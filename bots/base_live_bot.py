import asyncio
import datetime
import json
from typing import Tuple, List, Union

import aiohttp
import pandas as pd
import websockets
from numba import types
from numba.experimental import jitclass

from bots.base_bot import Bot, ORDER_UPDATE, ACCOUNT_UPDATE
from definitions.candle import Candle, empty_candle_list
from definitions.fill import Fill, empty_fill_list
from definitions.order import Order, empty_order_list
from definitions.position import Position
from definitions.position_list import PositionList
from definitions.tick import Tick, empty_tick_list
from helpers.loaders import load_key_secret
from helpers.misc import get_utc_now_timestamp
from helpers.optimized import merge_ticks, calculate_base_candle_time
from helpers.print_functions import print_, print_tick


@jitclass([
    ('symbol', types.string),
    ('user', types.string),
    ('exchange', types.string),
    ('leverage', types.int64),
    ('call_interval', types.float64),
    ('historic_tick_range', types.float64),
    ('historic_fill_range', types.float64)
])
class LiveConfig:
    """
    A class representing a live config.
    """

    def __init__(self, symbol: str, user: str, exchange: str, leverage: int, call_interval: float,
                 historic_tick_range: float, historic_fill_range: float):
        """
        Creates a live config.
        :param symbol: The symbol to use.
        :param user: The user for the API keys.
        :param exchange: The exchange to use.
        :param leverage: The leverage to use.
        :param call_interval: Call interval for strategy to use in live.
        :param historic_tick_range: Range for which to fetch historic ticks in seconds. 0 if nothing to fetch.
        :param historic_tick_range: Range for which to fetch historic fills in seconds. 0 if nothing to fetch.
        """
        self.symbol = symbol
        self.user = user
        self.exchange = exchange
        self.leverage = leverage
        self.call_interval = call_interval
        self.historic_tick_range = historic_tick_range
        self.historic_fill_range = historic_fill_range


class LiveBot(Bot):
    """
    Live implementation of the base bot class using async functions and websockets.
    """

    def __init__(self, config: LiveConfig, strategy):
        """
        Creates an instance of the live bot with configuration and strategy.
        :param config: A live configuration class.
        :param strategy: A strategy implementing the logic.
        """
        super(LiveBot, self).__init__()
        self.config = config
        self.strategy = strategy

        self.symbol = config.symbol
        self.leverage = config.leverage

        self.user = config.user

        self.session = aiohttp.ClientSession()

        self.key, self.secret = load_key_secret(config.exchange, self.user)

        self.call_interval = config.call_interval
        self.historic_tick_range = config.historic_tick_range
        self.historic_fill_range = config.historic_fill_range

        self.historic_ticks = empty_tick_list()
        self.historic_fills = empty_fill_list()

        self.execute_strategy_logic = False
        self.fetched_historic_ticks = False
        self.fetched_historic_fills = False

        self.base_endpoint = ''
        self.endpoints = {
            'listenkey': '',
            'position': '',
            'balance': '',
            'exchange_info': '',
            'leverage_bracket': '',
            'open_orders': '',
            'ticker': '',
            'fills': '',
            'income': '',
            'create_order': '',
            'cancel_order': '',
            'ticks': '',
            'margin_type': '',
            'leverage': '',
            'position_side': '',
            'websocket': '',
            'websocket_user': '',
            'websocket_data': ''
        }

    async def exchange_init(self):
        """
        Exchange specific initialization. Gets values from the exchange and sets parameters.
        :return:
        """
        raise NotImplementedError

    async def async_init(self):
        """
        Calls the base init and exchange specific init function and provides async support.
        :return:
        """
        self.init()
        await self.exchange_init()
        self.strategy.update_steps(self.quantity_step, self.price_step, self.minimal_quantity, self.minimal_cost,
                                   self.call_interval)
        self.strategy.update_symbol(self.symbol)
        self.strategy.update_leverage(self.leverage)

    async def fetch_exchange_info(self):
        """
        Exchange specific information fetching. Gets values from the exchange.
        :return:
        """
        raise NotImplementedError

    async def fetch_orders(self) -> List[Order]:
        """
        Function to fetch current open orders. To be implemented by the exchange implementation.
        :return: A list of current open orders.
        """
        raise NotImplementedError

    async def fetch_position(self) -> Tuple[Position, Position]:
        """
        Function to fetch current position. To be implemented by the exchange implementation.
        :return: The current long and short position.
        """
        raise NotImplementedError

    async def fetch_balance(self) -> float:
        """
        Function to fetch current balance. To be implemented by the exchange implementation.
        :return: The current balance.
        """
        raise NotImplementedError

    async def fetch_ticks(self, from_id: int = None, start_time: int = None, end_time: int = None,
                          do_print: bool = True) -> List[Tick]:
        """
        Function to fetch ticks, either based on ID or based on time. If the exchange does not support fetching by time,
        the function needs to implement logic that searches for the appropriate time and then fetches based on ID. To be
        implemented by the exchange implementation.
        :param from_id: The ID from which to fetch.
        :param start_time: The start time from which to fetch.
        :param end_time: The end time to which to fetch.
        :param do_print: Whether to print output or not.
        :return: A list of Ticks.
        """
        raise NotImplementedError

    async def fetch_fills(self, from_id: int = None, start_time: int = None, end_time: int = None, limit: int = 1000) -> \
            List[Fill]:
        """
        Function to fetch fills, either based on ID or based on time. If the exchange does not support fetching by time,
        the function needs to implement logic that searches for the appropriate time and then fetches based on ID. To be
        implemented by the exchange implementation.
        :param from_id: The ID from which to fetch.
        :param start_time: The start time from which to fetch.
        :param end_time: The end time to which to fetch.
        :param limit: Maximum fills to fetch.
        :return: A list of Fills.
        """
        raise NotImplementedError

    def fetch_from_repo(self, date: Union[Tuple[str, str], Tuple[str, str, str]]) -> pd.DataFrame:
        """
        Function to allow fetching trade data from a repository. Needs to be implemented by the exchange implementation
        or return an empty dataframe if this functionality is not available for the exchange.
        :param date: The date, a tuple representing either a year and a month, or a year, a month, and a day. The order
        is year, month, day.
        :return: A dataframe with following columns: trade_id (int64), price (float64), qty (float64),
        timestamp (int64), is_buyer_maker (int8)
        """
        raise NotImplementedError

    async def public_get(self, url: str, params: dict = {}) -> dict:
        """
        Function for public API endpoints. To be implemented by the exchange implementation.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer decoded into json.
        """
        raise NotImplementedError

    async def private_(self, type_: str, url: str, params: dict = {}) -> dict:
        """
        Base function for private API endpoints. Needs to calculate signature, encoding, and headers.
        To be implemented by the exchange implementation.
        :param type_: The type of call to call specific function.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer decoded into json.
        """
        raise NotImplementedError

    async def private_get(self, url: str, params: dict = {}) -> dict:
        """
        Function for private GET API endpoints. To be implemented by the exchange implementation.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer string.
        """
        raise NotImplementedError

    async def private_post(self, url: str, params: dict = {}) -> dict:
        """
        Function for private POST API endpoints. To be implemented by the exchange implementation.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer string.
        """
        raise NotImplementedError

    async def private_put(self, url: str, params: dict = {}) -> dict:
        """
        Function for private PUT API endpoints. To be implemented by the exchange implementation.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer string.
        """
        raise NotImplementedError

    async def private_delete(self, url: str, params: dict = {}) -> dict:
        """
        Function for private DELETE API endpoints. To be implemented by the exchange implementation.
        :param url: The URL to use in accordance with the base URL.
        :param params: The parameters to pass to the call.
        :return: The answer string.
        """
        raise NotImplementedError

    async def update_heartbeat(self):
        """
        Function that triggers an update of the websocket or initializes it, if needed.
        :return:
        """
        pass

    async def async_reset(self):
        """
        Resets the bot to an empty state and fetches data from the exchange again. Also updates the strategy with
        values.
        :return:
        """
        self.reset()
        await self.async_init_orders()
        await self.async_init_position()
        await self.async_init_balance()
        self.strategy.update_values(self.get_balance(), self.get_position(), self.get_orders())

    async def async_init_orders(self):
        """
        Initializes open orders by fetching them from the exchange.
        :return:
        """
        self.init_orders()
        a = await self.fetch_orders()
        add_orders = empty_order_list()
        delete_orders = empty_order_list()
        for order in a:
            add_orders.append(order)
        self.update_orders(add_orders, delete_orders)

    async def async_init_position(self):
        """
        Initializes positions by fetching them from the exchange.
        :return:
        """
        self.init_orders()
        long, short = await self.fetch_position()
        self.update_position(long, short)

    async def async_init_balance(self):
        """
        Initializes balance by fetching it from the exchange.
        :return:
        """
        self.init_balance()
        bal = await self.fetch_balance()
        self.update_balance(bal)

    async def async_handle_order_update(self, msg: dict):
        """
        Async wrapper for the order updates. Translates the exchange specific msg into an Order.
        Handles an orders update by either deleting, adding, or changing the open orders.
        :param msg: The order message to process.
        :return:
        """
        last_filled_order = self.handle_order_update(self.prepare_order(msg))
        if not last_filled_order.empty():
            asyncio.create_task(self.async_execute_strategy_order_update(last_filled_order))

    async def async_handle_account_update(self, msg: dict):
        """
        Async wrapper for the position and balance updates. Translates the exchange specific msg into Positions.
        Handles an account update which includes balance and position changes.
        :param msg: The account message to process.
        :return:
        """
        old_balance, new_balance, old_position, new_position = self.handle_account_update(*self.prepare_account(msg))
        asyncio.create_task(
            self.async_execute_strategy_account_update(old_balance, new_balance, old_position, new_position))

    async def start_heartbeat(self) -> None:
        """
        Heartbeat function to keep the websocket alive if needed.
        :return:
        """
        while True:
            await asyncio.sleep(60)
            await self.update_heartbeat()

    async def start_user_data(self) -> None:
        """
        Function to start the user data stream. Triggers order and account updates and keeps the state of the bot in
        sync with the exchange.
        :return:
        """
        while True:
            try:
                await self.async_reset()
                await self.update_heartbeat()
                async with websockets.connect(self.endpoints['websocket_user']) as ws:
                    async for msg in ws:
                        if msg is None:
                            continue
                        try:
                            msg = json.loads(msg)
                            type = self.determine_update_type(msg)
                            if type:
                                # print(msg)
                                if type == ORDER_UPDATE:
                                    asyncio.create_task(self.async_handle_order_update(msg))
                                elif type == ACCOUNT_UPDATE:
                                    asyncio.create_task(self.async_handle_account_update(msg))
                        except Exception as e:
                            print_(['User stream error inner', e], n=True)
            except Exception as e_out:
                print_(['User stream error outer', e_out], n=True)
                print_(['Retrying to connect in 5 seconds...'], n=True)
                await asyncio.sleep(5)

    async def start_websocket(self) -> None:
        """
        Function to start the price stream. Accumulates ticks and aggregates them to a candle based on the specified
        tick interval filling gaps if necessary. Also triggers the strategy decision making function after the specified
        interval. It is not guaranteed that the strategy is called exactly after each interval but it depends if a new
        message came in.
        :return:
        """
        while True:
            price_list = empty_candle_list()
            tick_list = empty_tick_list()
            last_tick_update = 0
            last_update = datetime.datetime.now()
            last_candle = Candle(0, 0.0, 0.0, 0.0, 0.0, 0.0)
            async with websockets.connect(self.endpoints['websocket_data']) as ws:
                async for msg in ws:
                    if msg is None:
                        continue
                    try:
                        msg = json.loads(msg)
                        # print_([msg], n=True)
                        tick = self.prepare_tick(msg)
                        if last_tick_update == 0:
                            # Make sure it starts at a base unit
                            # If tick interval is 250ms the base unit is either 0.0, 0.25, 0.5, or 0.75 seconds
                            last_tick_update = calculate_base_candle_time(tick, self.tick_interval)
                        # print_tick(tick)
                        if tick.timestamp - last_tick_update < self.tick_interval * 1000:
                            tick_list.append(tick)
                        else:
                            tick_list.append(tick)
                            # Calculate the time when the candle of the current tick ends
                            next_update = calculate_base_candle_time(tick, self.tick_interval) + int(
                                self.tick_interval * 1000)
                            # Calculate a list of candles based on the given ticks, gaps are filled
                            # The tick list and last update are already updated
                            candles, tick_list, last_tick_update = self.prepare_candles(tick_list, last_tick_update,
                                                                                        next_update, last_candle)
                            if candles:
                                # Update last candle
                                last_candle = candles[-1]
                            # print_candle(last_candle)
                            # Extend candle list with new candles
                            price_list.extend(candles)
                        current = datetime.datetime.now()
                        if current - last_update >= datetime.timedelta(seconds=self.strategy.call_interval):
                            last_update = current
                            print_(['Do something'], n=True)
                            # asyncio.create_task(self.async_execute_strategy_decision_making(price_list))
                            price_list = empty_candle_list()
                    except Exception as e:
                        if 'success' not in msg:
                            print_(['Error in price stream', e, msg], n=True)

    async def execute_leverage_change(self):
        """
        Function to execute the leverage change and ensure that the leverage is set correctly on the exchange. To be
        implemented by the exchange implementation.
        :return:
        """
        raise NotImplementedError

    async def async_create_orders(self, orders_to_create: List[Order]):
        """
        Async base function for the order creation function. To be implemented by the exchange implementation.
        :param orders_to_create: Orders to create/send to the exchange.
        :return:
        """
        raise NotImplementedError

    async def async_cancel_orders(self, orders_to_cancel: List[Order]):
        """
        Async base function for the order cancellation function. To be implemented by the exchange implementation.
        :param orders_to_cancel: Orders to cancel/send to the exchange.
        :return:
        """
        raise NotImplementedError

    async def async_execute_strategy_order_update(self, last_filled_order: Order):
        """
        Async wrapper for the base strategy order execution function. Calls the base function and creates creation and
        cancellation tasks.
        :return:
        """
        add_orders, delete_orders = self.execute_strategy_order_update(last_filled_order)

        asyncio.create_task(self.async_cancel_orders(delete_orders))
        asyncio.create_task(self.async_create_orders(add_orders))

    async def async_execute_strategy_account_update(self, old_balance: float, new_balance: float,
                                                    old_position: PositionList, new_position: PositionList):
        """
        Async wrapper for the base strategy account execution function. Calls the base function and creates creation and
        cancellation tasks.
        :return:
        """
        add_orders, delete_orders = self.execute_strategy_account_update(old_balance, new_balance, old_position,
                                                                         new_position)

        asyncio.create_task(self.async_cancel_orders(delete_orders))
        asyncio.create_task(self.async_create_orders(add_orders))

    async def async_execute_strategy_decision_making(self, prices: List[Candle]):
        """
        Async wrapper for the base strategy decision making function. Calls the base function and creates creation and
        cancellation tasks.
        :param prices: A list of candles since the last time this function was called.
        :return:
        """
        add_orders, delete_orders = self.execute_strategy_decision_making(prices)

        asyncio.create_task(self.async_cancel_orders(delete_orders))
        asyncio.create_task(self.async_create_orders(add_orders))
