import os

os.environ["NOJIT"] = "true"

import ccxt.async_support as ccxt
import json
import hjson
import pprint
import numpy as np
import asyncio
import time
import subprocess
import argparse
import traceback
from procedures import load_exchange_key_secret_passphrase, utc_ms
from njit_funcs import calc_emas
from pure_funcs import determine_pos_side_ccxt


def score_func_old(ohlcv):
    highs = np.array(ohlcv)[:, 2]
    lows = np.array(ohlcv)[:, 3]
    closes = np.array(ohlcv)[:, 4]
    range_mean = ((highs - lows) / closes).mean()
    std_over_mean = closes.std() / closes.mean()
    return range_mean ** 2 / std_over_mean


def score_func(ohlcv):
    highs = np.array(ohlcv)[:, 2]
    lows = np.array(ohlcv)[:, 3]
    closes = np.array(ohlcv)[:, 4]
    spans = [int(round(len(closes) * i)) for i in np.linspace(0.1, 0.9, 4)]
    emas = calc_emas(closes, np.array(spans))
    unilateralness = abs(sum([(1 - emas[:, i] / emas[:, i - 1]).mean() for i in range(1, len(emas[0]))]))
    range_mean = ((highs - lows) / closes).mean()
    return range_mean / unilateralness


def calc_unilateralness(ohlcv):
    # higher means more unilateral
    closes = np.array(ohlcv)[:, 4]
    spans = [int(round(len(closes) * i)) for i in np.linspace(0.1, 0.9, 4)]
    emas = calc_emas(closes, np.array(spans))
    return abs(sum([(1 - emas[:, i] / emas[:, i - 1]).mean() for i in range(1, len(emas[0]))]))


def calc_noisiness(ohlcv):
    # higher is more noisy
    highs = np.array(ohlcv)[:, 2]
    lows = np.array(ohlcv)[:, 3]
    closes = np.array(ohlcv)[:, 4]
    range_mean = ((highs - lows) / closes).mean()
    return range_mean


def calc_volume_sum(ohlcv):
    vols = np.array(ohlcv)[:, 5]
    closes = np.array(ohlcv)[:, 4]
    return (vols * closes).sum()


def sort_symbols(ohlcvs, config):
    min_n_syms = max(config["n_longs"], config["n_shorts"])
    print("min_n_syms", min_n_syms)
    filtered_syms = list(ohlcvs)
    by_func = [(0.0, sym) for sym in filtered_syms]
    for title, func, higher_is_better in [
        ("volume", calc_volume_sum, True),
        ("unilateralness", calc_unilateralness, False),
        ("noisiness", calc_noisiness, True),
    ]:
        if config[f"{title}_clip_threshold"] == 0.0:
            continue
        by_func = sorted([(func(ohlcvs[sym]), sym) for sym in filtered_syms], reverse=higher_is_better)
        print(f"sorted by {title} {'high to low' if higher_is_better else 'low to high'} n syms: {len(by_func)}")
        for elm in by_func:
            print(elm)
        by_func = by_func[: max(int(round(len(by_func) * config[f"{title}_clip_threshold"])), min_n_syms)]
        filtered_syms = [elm[1] for elm in by_func]
    return by_func


def generate_yaml(
    sorted_syms,
    config,
    current_positions_long,
    current_positions_short,
    current_open_orders_long,
    current_open_orders_short,
):
    yaml = f"session_name: {config['user']}\nwindows:\n"
    user = config["user"]
    twe_long = config["twe_long"]
    twe_short = config["twe_short"]

    n_longs = config["n_longs"]
    n_shorts = config["n_shorts"]
    lw = round(twe_long / n_longs, 4) if n_longs > 0 else 0.1
    sw = round(twe_short / n_shorts, 4) if n_shorts > 0 else 0.1
    lm, sm = "gs", "gs"
    sorted_syms = [x[1] for x in sorted_syms]
    current_positions_long = sorted(set(current_positions_long + current_open_orders_long))
    current_positions_short = sorted(set(current_positions_short + current_open_orders_short))
    if config["approved_symbols_only"]:
        approved_longs = set(config["live_configs_map_long"]) | set(config["live_configs_map"])
        approved_shorts = set(config["live_configs_map_short"]) | set(config["live_configs_map"])
    else:
        approved_longs = set(sorted_syms)
        approved_shorts = set(sorted_syms)
    ideal_longs = [x for x in sorted_syms if x in approved_longs][:n_longs]
    ideal_shorts = [x for x in sorted_syms if x in approved_shorts][:n_shorts]

    free_slots_long = max(0, n_longs - len(current_positions_long))
    active_longs = [sym for sym in ideal_longs if sym in current_positions_long]
    active_longs += [sym for sym in ideal_longs if sym not in active_longs][:free_slots_long]
    longs_on_gs = [sym for sym in current_positions_long if sym not in active_longs]

    free_slots_short = max(0, n_shorts - len(current_positions_short))
    active_shorts = [sym for sym in ideal_shorts if sym in current_positions_short]
    active_shorts += [sym for sym in ideal_shorts if sym not in active_shorts][:free_slots_short]
    shorts_on_gs = [sym for sym in current_positions_short if sym not in active_shorts]

    print("ideal_longs", sorted(ideal_longs))
    print("ideal_shorts", sorted(ideal_shorts))
    print("longs_on_gs", sorted(longs_on_gs))
    print("shorts_on_gs", sorted(shorts_on_gs))
    print("active_longs", sorted(active_longs))
    print("active_shorts", sorted(active_shorts))

    active_bots, bots_on_gs = [], []
    for sym in sorted(set(active_longs + active_shorts + longs_on_gs + shorts_on_gs)):
        elm = (sym, sym in active_longs, sym in active_shorts)
        if elm[1] or elm[2]:
            active_bots.append(elm)
        else:
            bots_on_gs.append(elm)

    bot_instances = []
    for sym, long_enabled, short_enabled in active_bots + bots_on_gs:
        lm = "n" if long_enabled and lw > 0.0 else "gs"
        sm = "n" if short_enabled and sw > 0.0 else "gs"
        if sym in config["live_configs_map_long"]:
            conf_path_long = config["live_configs_map_long"][sym]
        elif sym in config["live_configs_map"]:
            conf_path_long = config["live_configs_map"][sym]
        else:
            conf_path_long = config["default_config_path"]

        if sym not in (shorts_on_gs + active_shorts):
            conf_path_short = conf_path_long
        elif sym in config["live_configs_map_short"]:
            conf_path_short = config["live_configs_map_short"][sym]
        elif sym in config["live_configs_map"]:
            conf_path_short = config["live_configs_map"][sym]
        else:
            conf_path_short = config["default_config_path"]

        if sym not in (longs_on_gs + active_longs):
            conf_path_long = conf_path_short

        if conf_path_long == conf_path_short:
            pane = f"    - shell_command:\n      - python3 passivbot.py {user} {sym} {conf_path_long} "
            pane += f"-lw {lw} -sw {sw} -lm {lm} -sm {sm} -lev {config['leverage']} -cd -pt {config['price_distance_threshold']}"
            bot_instances.append((sym, pane))
        else:
            # long and short use different configs
            long_active = sym in active_longs or sym in current_positions_long
            short_active = sym in active_shorts or sym in current_positions_short
            if long_active and short_active:
                # two separate bot instances for long & short
                pane = f"    - shell_command:\n      - python3 passivbot.py {user} {sym} {conf_path_long} "
                pane += f"-lw {lw} -sw {sw} -lm {lm} -sm m -lev {config['leverage']} -cd -pt {config['price_distance_threshold']}"
                bot_instances.append((sym, pane))
                pane = f"    - shell_command:\n      - python3 passivbot.py {user} {sym} {conf_path_short} "
                pane += f"-lw {lw} -sw {sw} -lm m -sm {sm} -lev {config['leverage']} -cd -pt {config['price_distance_threshold']}"
                bot_instances.append((sym, pane))
            elif long_active:
                pane = f"    - shell_command:\n      - python3 passivbot.py {user} {sym} {conf_path_long} "
                pane += f"-lw {lw} -sw {sw} -lm {lm} -sm {sm} -lev {config['leverage']} -cd -pt {config['price_distance_threshold']}"
                bot_instances.append((sym, pane))
            elif short_active:
                pane = f"    - shell_command:\n      - python3 passivbot.py {user} {sym} {conf_path_short} "
                pane += f"-lw {lw} -sw {sw} -lm {lm} -sm {sm} -lev {config['leverage']} -cd -pt {config['price_distance_threshold']}"
                bot_instances.append((sym, pane))

    both_on_gs = False
    z = 0
    for sym, pane in bot_instances:
        if not both_on_gs and sym not in active_longs and sym not in active_shorts:
            z = 0
            both_on_gs = True
        if z % config["max_n_panes"] == 0:
            yaml += f"- window_name: {config['user']}_{'gs' if both_on_gs else 'normal'}_{z}\n  layout: "
            yaml += f"even-vertical\n  shell_command_before:\n    - cd ~/passivbot\n  panes:\n"
        yaml += pane + "\n"
        z += 1
    return yaml


async def get_ohlcvs(cc, symbols, config):
    ohs = {}
    n = 5
    if cc.id == "bybit":
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "12h": 43200,
            "1d": 86400,
            "1w": 604800,
        }
        max_n_ohlcvs = 200
        since = int(utc_ms() - interval_map[config["ohlcv_interval"]] * max_n_ohlcvs * 1000)
        extra_args = {"since": since}
    else:
        extra_args = {}
    print("n syms", len(symbols))
    for i in range(0, len(symbols), n):
        js = list(range(i, min(len(symbols), i + n)))
        fetched = await asyncio.gather(
            *[cc.fetch_ohlcv(symbols[j], timeframe=config["ohlcv_interval"], **extra_args) for j in js]
        )
        print("fetching ohlcvs", [symbols[j] for j in js], f"{i}/{len(symbols)}")
        for k, j in enumerate(js):
            ohs[symbols[j]] = fetched[k]
    return ohs


async def get_current_symbols(cc):
    current_positions_long, current_positions_short = [], []
    current_open_orders = []
    poss = await cc.fetch_positions()
    for elm in poss:
        if elm["contracts"] != 0.0:
            if elm["side"] == "long":
                current_positions_long.append(elm["symbol"])
            elif elm["side"] == "short":
                current_positions_short.append(elm["symbol"])
    if cc.id == "bybit":
        oos = []
        delay_s = 0.5
        for symbol in cc.markets:
            if symbol.endswith("USDT"):
                sts = time.time()
                oosf = await cc.fetch_open_orders(symbol=symbol)
                spent = time.time() - sts
                print(f"\r fetching open orders for {symbol}     ", end=" ")
                oos += oosf
                time.sleep(max(0.0, delay_s - spent))
        print()
    elif cc.id == "binanceusdm":
        cc.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
        oos = await cc.fetch_open_orders()
    else:
        oos = await cc.fetch_open_orders()
    current_open_orders_long, current_open_orders_short = [], []
    for elm in oos:
        pos_side = determine_pos_side_ccxt(elm)
        if pos_side == "short":
            current_open_orders_short.append(elm["symbol"])
        else:
            current_open_orders_long.append(elm["symbol"])
    current_positions_long = sorted(set(current_positions_long))
    current_positions_short = sorted(set(current_positions_short))
    current_open_orders_long = sorted(set(current_open_orders_long))
    current_open_orders_short = sorted(set(current_open_orders_short))
    return (
        current_positions_long,
        current_positions_short,
        current_open_orders_long,
        current_open_orders_short,
    )


async def get_min_costs(cc):
    exchange = cc.id
    info = await cc.fetch_markets()
    tickers = await cc.fetch_tickers()
    min_costs = {}
    c_mults = {}
    for x in info:
        symbol = x["symbol"]
        if symbol.endswith("USDT"):
            if x["type"] != "spot":
                if exchange in ["okx", "bitget", "kucoinfutures"]:
                    ticker_symbol = symbol.replace(":USDT", "")
                else:
                    ticker_symbol = symbol
                if ticker_symbol in tickers:
                    if exchange == "bitget":
                        min_cost = 5.0
                        c_mult = 1.0
                        min_qty = float(x["info"]["minTradeNum"])
                        last_price = tickers[ticker_symbol]["last"]
                    elif exchange == "kucoinfutures":
                        min_qty = 1.0
                        min_cost = 0.0
                        c_mult = float(x["info"]["multiplier"])
                        last_price = float(tickers[ticker_symbol]["info"]["last"])
                    else:
                        min_cost = 0.0 if x["limits"]["cost"]["min"] is None else x["limits"]["cost"]["min"]
                        c_mult = 1.0 if x["contractSize"] is None else x["contractSize"]
                        min_qty = 0.0 if x["limits"]["amount"]["min"] is None else x["limits"]["amount"]["min"]
                        last_price = tickers[ticker_symbol]["last"]
                    min_costs[symbol] = max(min_cost, min_qty * c_mult * last_price)
                    c_mults[symbol] = c_mult
    return min_costs, c_mults


async def dump_yaml(cc, config):
    max_min_cost = config["max_min_cost"]
    print("getting min costs...")
    min_costs, c_mults = await get_min_costs(cc)
    symbols_map = {sym: sym.replace(":USDT", "").replace("/", "") for sym in min_costs}
    symbols_map_inv = {v: k for k, v in symbols_map.items()}
    approved = [symbols_map[k] for k, v in min_costs.items() if v <= max_min_cost and k in symbols_map]
    approved = sorted(set(approved) - set(config["symbols_to_ignore"]))
    if config["approved_symbols_only"]:
        # only use approved symbols
        approved = sorted(
            set(approved)
            & (
                set(config["live_configs_map"])
                | set(config["live_configs_map_long"])
                | set(config["live_configs_map_short"])
            )
        )

    print("getting current bots...")
    (
        current_positions_long,
        current_positions_short,
        current_open_orders_long,
        current_open_orders_short,
    ) = await get_current_symbols(cc)

    current_positions_long = [symbols_map[s] if s in symbols_map else s for s in current_positions_long]
    current_positions_short = [symbols_map[s] if s in symbols_map else s for s in current_positions_short]
    current_open_orders_long = [symbols_map[s] if s in symbols_map else s for s in current_open_orders_long]
    current_open_orders_short = [symbols_map[s] if s in symbols_map else s for s in current_open_orders_short]

    current_positions_long = sorted(set(current_positions_long) - set(config["symbols_to_ignore"]))
    current_positions_short = sorted(set(current_positions_short) - set(config["symbols_to_ignore"]))
    current_open_orders_long = sorted(set(current_open_orders_long) - set(config["symbols_to_ignore"]))
    current_open_orders_short = sorted(set(current_open_orders_short) - set(config["symbols_to_ignore"]))

    print("ignoring symbols:", config["symbols_to_ignore"])
    print("current_positions_long", sorted(current_positions_long))
    print("current_positions_short", sorted(current_positions_short))
    print("current_open_orders long", sorted(current_open_orders_long))
    print("current_open_orders short", sorted(current_open_orders_short))
    print("getting ohlcvs...")
    ohs = await get_ohlcvs(cc, [symbols_map_inv[sym] for sym in approved], config)
    max_len_ohlcv = max([len(ohs[s]) for s in ohs])
    print("max_len_ohlcv", max_len_ohlcv)
    ohs = {symbols_map[k]: v for k, v in ohs.items() if len(v) == max_len_ohlcv}
    for sym in ohs:
        for i in range(len(ohs[sym])):
            ohs[sym][i][5] *= c_mults[symbols_map_inv[sym]]
    sorted_syms = sort_symbols(ohs, config)  # sorted best to worst
    print(f"generating yaml {config['yaml_filepath']}...")
    yaml = generate_yaml(
        sorted_syms,
        config,
        current_positions_long,
        current_positions_short,
        current_open_orders_long,
        current_open_orders_short,
    )
    with open(config["yaml_filepath"], "w") as f:
        f.write(yaml)


async def main():
    exchange_map = {
        "kucoin": "kucoinfutures",
        "okx": "okx",
        "bybit": "bybit",
        "binance": "binanceusdm",
    }
    parser = argparse.ArgumentParser(prog="forager", description="start forager")
    parser.add_argument("forager_config_path", type=str, help="path to forager config")
    args = parser.parse_args()
    config = hjson.load(open(args.forager_config_path))
    config["yaml_filepath"] = f"{config['user']}.yaml"
    user = config["user"]
    for key, value in [
        ("volume_clip_threshold", 0.5),
        ("unilateralness_clip_threshold", 0.5),
        ("noisiness_clip_threshold", 0.5),
        ("price_distance_threshold", 0.5),
        ("max_n_panes", 8),
        ("n_ohlcvs", 100),
        ("ohlcv_interval", "15m"),
        ("leverage", 10),
        ("symbols_to_ignore", []),
        ("live_configs_map_long", {}),
        ("live_configs_map_short", {}),
        ("update_interval_minutes", 60),
    ]:
        if key not in config:
            config[key] = value
    exchange, key, secret, passphrase = load_exchange_key_secret_passphrase(config["user"])
    max_n_tries_per_hour = 5
    error_timestamps = []
    while True:
        try:
            cc = getattr(ccxt, exchange_map[exchange])({"apiKey": key, "secret": secret, "password": passphrase})
            await dump_yaml(cc, config)
            print("waiting one minute to avoid API rate limiting...")
            for i in range(60, -1, -1):
                time.sleep(1)
                print(f"\rcountdown: {i}    ", end=" ")
            print()
            subprocess.run(["tmux", "kill-session", "-t", config["user"]])
            subprocess.run(["tmuxp", "load", "-d", config["yaml_filepath"]])
            for i in range(config["update_interval_minutes"] * 60, -1, -1):
                time.sleep(1)
                print(f"\rcountdown: {i}    ", end=" ")
            print()
        except Exception as e:
            traceback.print_exc()
            sleep_mins = 2
            print(f"error with forager {e} waiting {sleep_mins} minutes and trying again")
            for i in range(60 * sleep_mins, -1, -1):
                time.sleep(1)
                print(f"\rcountdown: {i}    ", end=" ")
            now = time.time()
            error_timestamps.append(now)
            error_timestamps = [x for x in error_timestamps if x > now - 60 * 60]
            if len(error_timestamps) > max_n_tries_per_hour:
                print(f"failed {max_n_tries_per_hour} times last hour; exiting")
                return
        finally:
            await cc.close()


if __name__ == "__main__":
    asyncio.run(main())
