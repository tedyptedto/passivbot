from passivbot_multi import Passivbot, logging
from uuid import uuid4
import ccxt.pro as ccxt_pro
import ccxt.async_support as ccxt_async
import pprint
import asyncio
import traceback
import numpy as np
from pure_funcs import multi_replace, floatify, ts_to_date_utc, calc_hash, determine_pos_side_ccxt
from procedures import print_async_exception, utc_ms


class BitgetBot(Passivbot):
    def __init__(self, config: dict):
        super().__init__(config)
        self.ccp = getattr(ccxt_pro, self.exchange)(
            {
                "apiKey": self.user_info["key"],
                "secret": self.user_info["secret"],
                "password": self.user_info["passphrase"],
            }
        )
        self.ccp.options["defaultType"] = "swap"
        self.cca = getattr(ccxt_async, self.exchange)(
            {
                "apiKey": self.user_info["key"],
                "secret": self.user_info["secret"],
                "password": self.user_info["passphrase"],
            }
        )
        self.cca.options["defaultType"] = "swap"
        self.max_n_cancellations_per_batch = 10
        self.max_n_creations_per_batch = 5
        self.order_side_map = {
            "buy": {"long": "open_long", "short": "close_short"},
            "sell": {"long": "close_long", "short": "open_short"},
        }

    async def init_bot(self):
        # require symbols to be formatted to ccxt standard COIN/USDT:USDT
        self.markets_dict = await self.cca.load_markets()
        self.symbols = {}
        for symbol_ in sorted(set(self.config["symbols"])):
            symbol = symbol_
            if not symbol.endswith("/USDT:USDT"):
                coin_extracted = multi_replace(
                    symbol_, [("/", ""), (":", ""), ("USDT", ""), ("BUSD", ""), ("USDC", "")]
                )
                symbol_reformatted = coin_extracted + "/USDT:USDT"
                logging.info(
                    f"symbol {symbol_} is wrongly formatted. Trying to reformat to {symbol_reformatted}"
                )
                symbol = symbol_reformatted
            if symbol not in self.markets_dict:
                logging.info(f"{symbol} missing from {self.exchange}")
            else:
                elm = self.markets_dict[symbol]
                if elm["type"] != "swap":
                    logging.info(f"wrong market type for {symbol}: {elm['type']}")
                elif not elm["active"]:
                    logging.info(f"{symbol} not active")
                elif not elm["linear"]:
                    logging.info(f"{symbol} is not a linear market")
                else:
                    self.symbols[symbol] = self.config["symbols"][symbol_]
        self.quote = "USDT"
        self.inverse = False
        self.symbol_ids_inv = {
            self.markets_dict[symbol]["id"]: symbol for symbol in self.markets_dict
        }
        for symbol in self.symbols:
            elm = self.markets_dict[symbol]
            self.symbol_ids[symbol] = elm["id"]
            self.min_costs[symbol] = (
                0.1 if elm["limits"]["cost"]["min"] is None else elm["limits"]["cost"]["min"]
            )
            self.min_qtys[symbol] = elm["limits"]["amount"]["min"]
            self.qty_steps[symbol] = elm["precision"]["amount"]
            self.price_steps[symbol] = elm["precision"]["price"]
            self.c_mults[symbol] = elm["contractSize"]
            self.coins[symbol] = symbol.replace("/USDT:USDT", "")
            self.tickers[symbol] = {"bid": 0.0, "ask": 0.0, "last": 0.0}
            self.open_orders[symbol] = []
            self.positions[symbol] = {
                "long": {"size": 0.0, "price": 0.0},
                "short": {"size": 0.0, "price": 0.0},
            }
            self.upd_timestamps["open_orders"][symbol] = 0.0
            self.upd_timestamps["tickers"][symbol] = 0.0
            self.upd_timestamps["positions"][symbol] = 0.0
        await super().init_bot()

    async def start_websockets(self):
        await asyncio.gather(
            self.watch_balance(),
            self.watch_orders(),
            self.watch_tickers(),
        )

    async def watch_balance(self):
        while True:
            try:
                if self.stop_websocket:
                    break
                res = await self.ccp.watch_balance()
                res["USDT"]["total"] = res["USDT"]["free"]  # bitget balance is 'free'
                self.handle_balance_update(res)
            except Exception as e:
                print(f"exception watch_balance", e)
                traceback.print_exc()

    async def watch_orders(self):
        while True:
            try:
                if self.stop_websocket:
                    break
                res = await self.ccp.watch_orders()
                for i in range(len(res)):
                    res[i]["position_side"] = res[i]["info"]["posSide"]
                    res[i]["qty"] = res[i]["amount"]
                self.handle_order_update(res)
            except Exception as e:
                print(f"exception watch_orders", e)
                traceback.print_exc()

    async def watch_tickers(self, symbols=None):
        symbols = list(self.symbols if symbols is None else symbols)
        while True:
            try:
                if self.stop_websocket:
                    break
                res = await self.ccp.watch_tickers(symbols)
                if res["last"] is None:
                    res["last"] = np.random.choice([res["bid"], res["ask"]])
                self.handle_ticker_update(res)
            except Exception as e:
                print(f"exception watch_tickers {symbols}", e)
                traceback.print_exc()

    async def fetch_open_orders(self, symbol: str = None):
        fetched = None
        open_orders = []
        try:
            fetched = await self.cca.private_mix_get_mix_v1_order_margincoincurrent(
                params={"productType": "umcbl"}
            )
            for elm in fetched["data"]:
                elm["side"] = "buy" if elm["side"] in ["close_short", "open_long"] else "sell"
                elm["position_side"] = elm["posSide"]
                elm["price"] = float(elm["price"])
                elm["qty"] = elm["amount"] = float(elm["size"])
                elm["timestamp"] = float(elm["cTime"])
                elm["id"] = elm["orderId"]
                elm["custom_id"] = elm["clientOid"]
                elm["symbol"] = self.symbol_ids_inv[elm["symbol"]]
                open_orders.append(elm)
            return sorted(open_orders, key=lambda x: x["timestamp"])
        except Exception as e:
            logging.error(f"error fetching open orders {e}")
            print_async_exception(fetched)
            traceback.print_exc()
            return False

    async def fetch_positions(self) -> ([dict], float):
        # also fetches balance
        fetched_positions, fetched_balance = None, None
        try:
            fetched_positions, fetched_balance = await asyncio.gather(
                self.cca.private_mix_get_mix_v1_position_allposition_v2(
                    {"marginCoin": "USDT", "productType": "umcbl"}
                ),
                self.cca.private_mix_get_mix_v1_account_accounts({"productType": "umcbl"}),
            )
            balance = float(
                [x for x in fetched_balance["data"] if x["marginCoin"] == self.quote][0]["available"]
            )
            positions = []
            for elm in floatify(fetched_positions["data"]):
                if elm["total"] == 0.0:
                    continue
                positions.append(
                    {
                        "symbol": self.symbol_ids_inv[elm["symbol"]],
                        "position_side": elm["holdSide"],
                        "size": abs(elm["total"]) * (1.0 if elm["holdSide"] == "long" else -1.0),
                        "price": elm["averageOpenPrice"],
                    }
                )
            return positions, balance
        except Exception as e:
            logging.error(f"error fetching positions and balance {e}")
            print_async_exception(fetched_positions)
            print_async_exception(fetched_balance)
            traceback.print_exc()
            return False

    async def fetch_tickers(self):
        fetched = None
        try:
            fetched = await self.cca.public_mix_get_mix_v1_market_tickers(
                params={"productType": "UMCBL"}
            )
            tickers = self.cca.parse_tickers(fetched["data"])
            return tickers
        except Exception as e:
            logging.error(f"error fetching tickers {e}")
            print_async_exception(fetched)
            traceback.print_exc()
            if "bybit does not have market symbol" in str(e):
                # ccxt is raising bad symbol error
                # restart might help...
                raise Exception("ccxt gives bad symbol error... attempting bot restart")
            return False

    async def fetch_ohlcv(self, symbol: str, timeframe="1m"):
        # intervals: 1,3,5,15,30,60,120,240,360,720,D,M,W
        fetched = None
        try:
            fetched = await self.cca.fetch_ohlcv(symbol, timeframe=timeframe, limit=1000)
            return fetched
        except Exception as e:
            logging.error(f"error fetching ohlcv for {symbol} {e}")
            print_async_exception(fetched)
            traceback.print_exc()
            return False

    async def fetch_pnls(
        self,
        start_time: int = None,
        end_time: int = None,
    ):
        limit = 100
        if start_time is None and end_time is None:
            return await self.fetch_pnl()
        all_fetched = {}
        while True:
            fetched = await self.fetch_pnl(start_time=start_time, end_time=end_time)
            if fetched == []:
                break
            for elm in fetched:
                all_fetched[elm["id"]] = elm
            if len(fetched) < limit:
                break
            logging.info(f"debug fetching income {ts_to_date_utc(fetched[-1]['timestamp'])}")
            end_time = fetched[0]["timestamp"]
        return sorted(
            [x for x in all_fetched.values() if x["pnl"] != 0.0], key=lambda x: x["timestamp"]
        )

    async def fetch_pnl(
        self,
        start_time: int = None,
        end_time: int = None,
    ):
        fetched = None
        # if there are more fills in timeframe than 100, it will fetch latest
        try:
            if end_time is None:
                end_time = utc_ms() + 1000 * 60 * 60 * 24
            if start_time is None:
                start_time = 0
            params = {"productType": "umcbl", "startTime": int(start_time), "endTime": int(end_time)}
            fetched = await self.cca.private_mix_get_mix_v1_order_allfills(params=params)
            pnls = []
            for elm in fetched["data"]:
                pnls.append(elm)
                pnls[-1]["pnl"] = float(pnls[-1]["profit"])
                pnls[-1]["timestamp"] = float(pnls[-1]["cTime"])
                pnls[-1]["id"] = pnls[-1]["tradeId"]
            return sorted(pnls, key=lambda x: x["timestamp"])
        except Exception as e:
            logging.error(f"error fetching income {e}")
            print_async_exception(fetched)
            traceback.print_exc()
            return False

    async def execute_multiple(self, orders: [dict], type_: str, max_n_executions: int):
        if not orders:
            return []
        executions = []
        for order in orders[:max_n_executions]:  # sorted by PA dist
            execution = None
            try:
                execution = asyncio.create_task(getattr(self, type_)(order))
                executions.append((order, execution))
            except Exception as e:
                logging.error(f"error executing {type_} {order} {e}")
                print_async_exception(execution)
                traceback.print_exc()
        results = []
        for execution in executions:
            result = None
            try:
                result = await execution[1]
                results.append(result)
            except Exception as e:
                logging.error(f"error executing {type_} {execution} {e}")
                print_async_exception(result)
                traceback.print_exc()
        return results

    async def execute_cancellation(self, order: dict) -> dict:
        executed = None
        try:
            executed = await self.cca.cancel_order(order["id"], symbol=order["symbol"])
            return {
                "symbol": executed["symbol"],
                "side": order["side"],
                "id": executed["id"],
                "position_side": order["position_side"],
                "qty": order["qty"],
                "price": order["price"],
            }
        except Exception as e:
            logging.error(f"error cancelling order {order} {e}")
            print_async_exception(executed)
            traceback.print_exc()
            return {}

    async def execute_cancellations(self, orders: [dict]) -> [dict]:
        if len(orders) > self.max_n_cancellations_per_batch:
            # prioritize cancelling reduce-only orders
            try:
                reduce_only_orders = [x for x in orders if x["reduce_only"]]
                rest = [x for x in orders if not x["reduce_only"]]
                orders = (reduce_only_orders + rest)[: self.max_n_cancellations_per_batch]
            except Exception as e:
                logging.error(f"debug filter cancellations {e}")
        return await self.execute_multiple(
            orders, "execute_cancellation", self.max_n_cancellations_per_batch
        )

    async def execute_order(self, order: dict) -> dict:
        executed = None
        try:
            executed = await self.cca.create_limit_order(
                symbol=order["symbol"],
                side=order["side"],
                amount=abs(order["qty"]),
                price=order["price"],
                params={
                    "reduceOnly": order["reduce_only"],
                    "timeInForceValue": "post_only",
                    "side": self.order_side_map[order["side"]][order["position_side"]],
                    "clientOid": f"{self.broker_code}#{order['custom_id']}_{str(uuid4())}"[:64],
                },
            )
            if "symbol" not in executed or executed["symbol"] is None:
                executed["symbol"] = order["symbol"]
            for key in ["side", "position_side", "qty", "price"]:
                if key not in executed or executed[key] is None:
                    executed[key] = order[key]
            return executed
        except Exception as e:
            logging.error(f"error executing order {order} {e}")
            print_async_exception(executed)
            traceback.print_exc()
            return {}

    async def execute_orders(self, orders: [dict]) -> [dict]:
        return await self.execute_multiple(orders, "execute_order", self.max_n_creations_per_batch)

    async def update_exchange_config(self):
        pass
