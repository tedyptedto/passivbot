import sys
import json
import numpy as np
import pandas as pd
import asyncio
import os
from time import time
from passivbot import init_ccxt, make_get_filepath, ts_to_date, print_, load_settings, \
    sort_dict_keys, round_up, round_dn, round_, calc_long_closes, calc_shrt_closes, \
    calc_long_reentry_price, calc_shrt_reentry_price, calc_default_qty
from binance import fetch_trades as binance_fetch_trades
from bybit import fetch_trades as bybit_fetch_trades
from bybit import calc_cross_long_liq_price as bybit_calc_cross_long_liq_price
from bybit import calc_cross_shrt_liq_price as bybit_calc_cross_shrt_liq_price

from typing import Iterator
from bisect import insort_left


def backtest(df: pd.DataFrame, settings: dict):

    grid_spacing = settings['grid_spacing']
    grid_coefficient = settings['grid_coefficient']
    price_step = settings['price_step']
    qty_step = settings['qty_step']
    inverse = settings['inverse']
    break_on_loss = settings['break_on_loss']
    liq_dist_threshold = settings['liq_dist_threshold']
    stop_loss_pos_reduction = settings['stop_loss_pos_reduction']
    qty_equity_pct = settings['qty_equity_pct']
    min_qty = settings['min_qty']

    leverage = settings['leverage']
    margin_limit = settings['margin_limit']
    compounding = settings['compounding']

    if inverse:
        calc_cost = lambda qty_, price_: qty_ / price_
        calc_liq_price = lambda equity_, pos_size_, pos_price_: \
            bybit_calc_cross_shrt_liq_price(equity_, pos_size_, pos_price_) \
                if pos_size_ < 0.0 else \
                bybit_calc_cross_long_liq_price(equity_, pos_size_, pos_price_)
    else:
        calc_cost = lambda qty_, price_: qty_ * price_

    equity = margin_limit
    default_qty = calc_default_qty(qty_step, min_qty, qty_equity_pct, equity)

    maker_fee = settings['maker_fee']

    min_markup = settings['min_markup'] \
        if 'min_markup' in settings else sorted(settings['markups'])[0]
    max_markup = sorted(settings['markups'])[-1]
    print('min max markups', min_markup, max_markup)
    n_close_orders = settings['n_close_orders']


    trades = []

    ob = [df.iloc[:2].price.min(), df.iloc[:2].price.max()]

    pos_size = 0.0
    pos_price = 0.0

    bid_price = ob[0]
    ask_price = ob[1]

    liq_price = 0.0

    pnl_sum = 0.0

    for row in df.itertuples():
        if row.buyer_maker:
            if pos_size == 0.0:                                     # no pos
                bid_qty = default_qty
                bid_price = ob[0]
            elif pos_size > 0.0:                                    # long pos
                if abs(liq_price - row.price) / row.price < liq_dist_threshold:
                    # limit reached; enter no more
                    bid_qty = 0.0
                    bid_price = 0.0
                else:                                               # long reentry
                    bid_qty = default_qty
                    pos_margin = calc_cost(pos_size, pos_price) / leverage
                    bid_price = min(ob[0], calc_long_reentry_price(price_step,
                                                                   grid_spacing,
                                                                   grid_coefficient,
                                                                   equity,
                                                                   pos_margin,
                                                                   pos_price))
            else:                                                   # shrt pos
                if row.price <= pos_price:                          # shrt close
                    qtys, prices = calc_shrt_closes(price_step, qty_step, min_qty, min_markup,
                                                    max_markup, pos_size, pos_price, ob[0],
                                                    n_close_orders)
                    bid_qty = qtys[0]
                    bid_price = prices[0]
                elif abs(liq_price - row.price) / row.price < liq_dist_threshold:
                    if break_on_loss:
                        print('shrt break on loss')
                        return []
                    # controlled shrt loss
                    bid_qty = round_up(-pos_size * stop_loss_pos_reduction, qty_step)
                    bid_price = ob[0]
                else:                                               # no shrt close
                    bid_qty = 0.0
                    bid_price = 0.0
            ob[0] = row.price
            if pos_size > 0.0 and liq_price and row.price < liq_price:
                print('long liquidation', liq_price)
                return []
            if row.price < bid_price:
                if pos_size >= 0.0:
                    # create or add to long pos
                    cost = calc_cost(bid_qty, bid_price)
                    margin_cost = cost / leverage
                    pnl = -cost * maker_fee
                    new_pos_size = pos_size + bid_qty
                    pos_price = pos_price * (pos_size / new_pos_size) + \
                        bid_price * (bid_qty / new_pos_size)
                    pos_size = new_pos_size
                    liq_price = calc_liq_price(equity, pos_size, pos_price)
                    trades.append({'trade_id': row.Index, 'side': 'long', 'type': 'entry',
                                   'price': bid_price, 'qty': bid_qty, 'pnl': pnl,
                                   'pos_size': pos_size, 'pos_price': pos_price, 'roe': np.nan,
                                   'margin_cost': margin_cost, 'liq_price': liq_price})
                    pnl_sum += pnl
                    if compounding:
                        equity += pnl
                        default_qty = calc_default_qty(qty_step, min_qty, qty_equity_pct, equity)
                    line = f'\r{row.Index / len(df):.2f} pnl sum {pnl_sum:.6f} '
                    liq_dist = abs(liq_price - row.price) / row.price
                    line += f'default qty {equity * qty_equity_pct:.6f} equity {equity:.6f} '
                    line += f'liq distance {liq_dist:.2f} '
                    line += f'pos_size {pos_size:.3f} '
                    print(line, end='    ')
                else:
                    # close shrt pos
                    cost = calc_cost(bid_qty, bid_price)
                    margin_cost = cost / leverage
                    gain = (pos_price / bid_price - 1)
                    pnl = cost * gain - cost * maker_fee
                    pos_size += bid_qty
                    roe = gain * leverage
                    liq_price = calc_liq_price(equity, pos_size, pos_price)
                    trades.append({'trade_id': row.Index, 'side': 'shrt', 'type': 'close',
                                   'price': bid_price, 'qty': bid_qty, 'pnl': pnl,
                                   'pos_size': pos_size, 'pos_price': pos_price, 'roe': roe,
                                   'margin_cost': margin_cost, 'liq_price': liq_price})
                    pnl_sum += pnl
                    if compounding:
                        equity += pnl
                        default_qty = calc_default_qty(qty_step, min_qty, qty_equity_pct, equity)
                    line = f'\r{row.Index / len(df):.2f} pnl sum {pnl_sum:.6f} '
                    liq_dist = abs(liq_price - row.price) / row.price

                    line += f'default qty {equity * qty_equity_pct:.6f} equity {equity:.6f} '
                    line += f'liq distance {liq_dist:.2f} '
                    line += f'pos_size {pos_size:.3f} '
                    print(line, end='    ')
        else:
            if pos_size == 0.0:                                      # no pos
                ask_qty = -default_qty
                ask_price = ob[1]
            elif pos_size < 0.0:                                     # shrt pos
                if abs(liq_price - row.price) / row.price < liq_dist_threshold:
                    # limit reached; enter no more
                    ask_qty = 0.0
                    ask_price = 9.9e9
                else:                                                # shrt reentry
                    ask_qty = -default_qty
                    pos_margin = calc_cost(-pos_size, pos_price) / leverage
                    ask_price = max(ob[1], calc_shrt_reentry_price(price_step,
                                                                   grid_spacing,
                                                                   grid_coefficient,
                                                                   equity,
                                                                   pos_margin,
                                                                   pos_price))
            else:                                                    # long pos
                if row.price >= pos_price:                           # close long pos
                    qtys, prices = calc_long_closes(price_step, qty_step, min_qty, min_markup,
                                                    max_markup, pos_size, pos_price, ob[1],
                                                    n_close_orders)
                    ask_qty = qtys[0]
                    ask_price = prices[0]
                elif abs(liq_price - row.price) / row.price < liq_dist_threshold:
                    if break_on_loss:
                        print('break on loss')
                        return []
                    # controlled long loss
                    ask_qty = -round_up(pos_size * stop_loss_pos_reduction, qty_step)
                    ask_price = ob[1]
                else:                                                # no close
                    ask_qty = 0.0
                    ask_price = 9.9e9
            ob[1] = row.price
            if pos_size < 0.0 and liq_price and row.price > liq_price:
                print('shrt liquidation', row.price, liq_price, pos_size, pos_price)
                return []
            if row.price > ask_price:
                if pos_size <= 0.0:
                    # add to or create short pos
                    cost = -calc_cost(ask_qty, ask_price)
                    margin_cost = cost / leverage
                    pnl = -cost * maker_fee
                    new_pos_size = pos_size + ask_qty
                    pos_price = pos_price * (pos_size / new_pos_size) + \
                        ask_price * (ask_qty / new_pos_size)
                    pos_size = new_pos_size
                    liq_price = calc_liq_price(equity, pos_size, pos_price)
                    trades.append({'trade_id': row.Index, 'side': 'shrt', 'type': 'entry',
                                   'price': ask_price, 'qty': ask_qty, 'pnl': pnl,
                                   'pos_size': pos_size, 'pos_price': pos_price, 'roe': np.nan,
                                   'margin_cost': margin_cost, 'liq_price': liq_price})
                    pnl_sum += pnl
                    if compounding:
                        equity += pnl
                        default_qty = calc_default_qty(qty_step, min_qty, qty_equity_pct, equity)
                    line = f'\r{row.Index / len(df):.2f} pnl sum {pnl_sum:.6f} '
                    liq_dist = abs(liq_price - row.price) / row.price
                    line += f'default qty {equity * qty_equity_pct:.6f} equity {equity:.6f} '
                    line += f'liq distance {liq_dist:.2f} '
                    line += f'pos_size {pos_size:.3f} '
                    print(line, end='    ')
                else:
                    # close long pos
                    cost = -calc_cost(ask_qty, ask_price)
                    margin_cost = cost / leverage
                    gain = (ask_price / pos_price - 1)
                    pnl = cost * gain - cost * maker_fee
                    pos_size += ask_qty
                    roe = gain * leverage
                    liq_price = calc_liq_price(equity, pos_size, pos_price)
                    trades.append({'trade_id': row.Index, 'side': 'long', 'type': 'close',
                                   'price': ask_price, 'qty': ask_qty, 'pnl': pnl,
                                   'pos_size': pos_size, 'pos_price': pos_price, 'roe': roe,
                                   'margin_cost': margin_cost, 'liq_price': liq_price})
                    pnl_sum += pnl
                    if compounding:
                        equity += pnl
                        default_qty = calc_default_qty(qty_step, min_qty, qty_equity_pct, equity)
                    line = f'\r{row.Index / len(df):.2f} pnl sum {pnl_sum:.6f} '
                    liq_dist = abs(liq_price - row.price) / row.price
                    line += f'default qty {equity * qty_equity_pct:.6f} equity {equity:.6f} '
                    line += f'liq distance {liq_dist:.2f} '
                    line += f'pos_size {pos_size:.3f} '
                    print(line, end='    ')
    return trades


def jackrabbit(agg_trades: pd.DataFrame, exchange: str = 'bybit'):
    if exchange == 'bybit':
        settings = {
            'inverse': True,
            'maker_fee': -0.00025,
            'price_step': 0.5,
            'qty_step': 1.0,
            'symbol': 'BTCUSD',
            'n_entry_orders': 10,
            'leverage': 100,
            'min_qty': 1.0,
            
            'break_on_loss': False,
            'compounding': True,
            'min_markup': 0.0002, # will override min(markups) in backtest
            'stop_loss_pos_reduction': 0.02,
            'n_close_orders': 17,
            'margin_limit': 0.00154,
            'markups': (0.0002, 0.0159),
            'liq_dist_threshold': 0.02,

            'qty_equity_pct': 2000,
            'grid_coefficient': 160.0,
            'grid_spacing': 0.003,
        }
    elif exchange == 'binance':
        # settings for binance
        settings = {
            "default_qty": 0.001,
            "grid_coefficient": 80.0,
            "grid_spacing": 0.002,
            "leverage": 125,
            "liq_dist_threshold": 0.03,
            "maker_fee": 0.00018,
            "margin_limit": 50,
            "markups": (0.01,),
            "min_markup": 0.00075, # will override min(markups) in backtest
            "min_qty": 0.001,
            "n_close_orders": 14,
            "n_entry_orders": 7,
            "price_step": 0.01,
            "qty_step": 0.001,
            "symbol": "BTCUSDT",
            "inverse": False,
            "break_on_loss": True,
        }

    ranges = {
        'grid_spacing': (0.0005, 0.02, 0.0001),
        'grid_coefficient': (0.0, 800, 0.01),
        'qty_equity_pct': (0.0, 10000, 10),
    }

    tweakable = {
        'grid_spacing': 0.0,
        'grid_coefficient': 0.0,
        'qty_equity_pct': 0.0,
    }

    best = {}

    for key in tweakable:
        if type(tweakable[key]) == tuple:
            best[key] = tuple(sorted([
                calc_new_val((ranges[key][1] - ranges[key][0]) / 2, ranges[key], 1.0)
                for _ in tweakable[key]
            ]))
        else:
            best[key] = calc_new_val((ranges[key][1] - ranges[key][0]) / 2, ranges[key], 1.0)

    # optional: uncomment to use settings as start candidate.
    best = {k_: settings[k_] for k_ in sorted(ranges)}

    settings = sort_dict_keys(settings)
    best = sort_dict_keys(best)

    results = {}
    best_gain = -99999999
    candidate = best

    ks = 200
    k = 0
    ms = np.array([1/(i/2 + 16) for i in range(ks)])
    ms = ((ms - ms.min()) / (ms.max() - ms.min()))

    n_days = (agg_trades.timestamp.iloc[-1] - agg_trades.timestamp.iloc[0]) / 1000 / 60 / 60 / 24

    results_filename = make_get_filepath(
        f'jackrabbit_results_grid/{ts_to_date(time())[:19]}_{int(round(n_days))}'
    )
    if settings['inverse']:
        results_filename += '_inverse'

    settings['n_days'] = n_days
    print('n_days', n_days)

    # conditions for result approval
    conditions = [
        lambda r: True,
    ]

    df = prep_df(agg_trades)

    while k < ks - 1:
        try:
            k += 1
            key = tuple([candidate[k_] for k_ in sorted(candidate)])
            if key in results:
                print('skipping', key)
                candidate = get_new_candidate(ranges, best)
                continue
            line = f'\n{k} m={ms[k]:.4f} best {tuple(best.values())}, '
            line += f'candidate {tuple(candidate.values())}'
            print(line)
            settings_ = {k_: candidate[k_] if k_ in candidate else settings[k_]
                         for k_ in sorted(settings)}
            trades = backtest(df, settings_)
            if not trades:
                print('\nno trades')
                candidate = get_new_candidate(ranges, best)
                continue
            tdf = pd.DataFrame(trades).set_index('trade_id')
            closest_liq = ((tdf.price - tdf.liq_price).abs() / tdf.price).min()
            biggest_pos_size = tdf.pos_size.abs().max()
            n_closes = len(tdf[tdf.type == 'close'])
            pnl_sum = tdf.pnl.sum()
            loss_sum = tdf[tdf.pnl < 0.0].pnl.sum()
            abs_pos_sizes = tdf.pos_size.abs()
            if settings['inverse']:
                max_margin_cost = (abs_pos_sizes / tdf.pos_price / settings_['leverage']).max()
            else:
                max_margin_cost = (abs_pos_sizes * tdf.pos_price / settings_['leverage']).max()
            #gain = (pnl_sum + max_margin_cost) / max_margin_cost
            gain = (pnl_sum + settings_['margin_limit']) / settings_['margin_limit']
            average_daily_gain = gain ** (1 / n_days)
            n_trades = len(tdf)
            result = {'n_closes': n_closes, 'pnl_sum': pnl_sum, 'loss_sum': loss_sum,
                      'max_margin_cost': max_margin_cost, 'average_daily_gain': average_daily_gain,
                      'gain': gain, 'n_trades': n_trades, 'closest_liq': closest_liq,
                      'biggest_pos_size': biggest_pos_size}
            print('\n', result)
            results[key] = result

            if gain > best_gain and all([c(results[key]) for c in conditions]):
                best = candidate
                best_gain = gain
                print('\n\nnew best', best, '\n', gain, '\n')
                print(settings_)
                print(results[key], '\n\n')
            candidate = get_new_candidate(ranges, best, m=ms[k])
            pd.DataFrame(results).T.to_csv(results_filename + '.csv')
        except KeyboardInterrupt:
            return results
    return results


def prep_df(adf: pd.DataFrame):
    dfc = adf[adf.price != adf.price.shift(1)]
    if 'side' in dfc.columns:
        # bybit
        buyer_maker = dfc.side == 'Sell'
        buyer_maker.name = 'buyer_maker'
    elif 'is_buyer_maker' in dfc.columns:
        # binance
        buyer_maker = dfc.is_buyer_maker
        buyer_maker.name = 'buyer_maker'
    else:
        raise Exception('trades of unknown format')
    df = pd.concat([dfc.price, buyer_maker], axis=1)
    df.index = np.arange(len(df))
    return df


def calc_new_val(val, range_, m):
    new_val = val + (np.random.random() - 0.5) * (range_[1] - range_[0]) * max(0.0001, m)
    return round(round(max(min(new_val, range_[1]), range_[0]) / range_[2]) * range_[2], 10)


def get_new_candidate(ranges: dict, best: dict, m=0.2):
    new_candidate = {}
    for key in best:
        if key not in ranges:
            continue
        if type(best[key]) == tuple:
            new_candidate[key] = tuple(sorted([calc_new_val(e, ranges[key], m) for e in best[key]]))
        else:
            new_candidate[key] = calc_new_val(best[key], ranges[key], m)
    return {k_: new_candidate[k_] for k_ in sorted(new_candidate)}


def iter_chunks(exchange: str, symbol: str) -> Iterator[pd.DataFrame]:
    chunk_size = 100000
    filepath = f'historical_data/{exchange}/agg_trades_futures/{symbol}/'
    if os.path.isdir(filepath):
        filenames = sorted([f for f in os.listdir(filepath) if f.endswith('.csv')])
        for f in filenames[::-1]:
            chunk = pd.read_csv(filepath + f).set_index('trade_id')
            if chunk is not None:
                print('loaded chunk of trades', f, ts_to_date(chunk.timestamp.iloc[0] / 1000))
                yield chunk
            else:
                yield None
        yield None
    else:
        yield None


async def load_trades(exchange: str, user: str, symbol: str, n_days: float) -> pd.DataFrame:

    def skip_ids(id_, ids_):
        if id_ in ids_:
            print('skipping from', id_)
            while id_ in ids_:
                id_ -= 1
            print('           to', from_id)
        return id_

    cc = init_ccxt(exchange, user)
    try:
        if exchange == 'binance':
            fetch_trades_func = binance_fetch_trades
        elif exchange == 'bybit':
            fetch_trades_func = bybit_fetch_trades
        else:
            print(exchange, 'not found')
            return
        filepath = make_get_filepath(f'historical_data/{exchange}/agg_trades_futures/{symbol}/')
        cache_filepath = make_get_filepath(
            f'historical_data/{exchange}/agg_trades_futures/{symbol}_cache/'
        )
        cache_filenames = [f for f in os.listdir(cache_filepath) if f.endswith('.csv')]
        ids = set()
        if cache_filenames:
            print('loading cached trades...')
            cached_trades = pd.concat([pd.read_csv(cache_filepath + f) for f in cache_filenames],
                                      axis=0)
            cached_trades = cached_trades.set_index('trade_id').sort_index()
            cached_trades = cached_trades[~cached_trades.index.duplicated()]
            ids.update(cached_trades.index)
        else:
            cached_trades = None
        age_limit = time() - 60 * 60 * 24 * n_days
        age_limit_millis = age_limit * 1000
        print('age_limit', ts_to_date(age_limit))
        chunk_iterator = iter_chunks(exchange, symbol)
        chunk = next(chunk_iterator)
        chunks = {} if chunk is None else {int(chunk.index[0]): chunk}
        if chunk is not None:
            ids.update(chunk.index)
        min_id = min(ids) if ids else 0
        new_trades = await fetch_trades_func(cc, symbol)
        cached_ids = set()
        k = 0
        while True:
            if new_trades[0]['timestamp'] <= age_limit_millis:
                break
            from_id = new_trades[0]['trade_id'] - 1
            while True:
                if chunk is None:
                    min_id = 0
                    break
                from_id = skip_ids(from_id, ids)
                if from_id < min_id:
                    chunk = next(chunk_iterator)
                    if chunk is None:
                        min_id = 0
                        break
                    else:
                        chunks[int(chunk.index[0])] = chunk
                        ids.update(chunk.index)
                        min_id = min(ids)
                        if chunk.timestamp.max() < age_limit_millis:
                            break
                else:
                    break
            from_id = skip_ids(from_id, ids)
            from_id -= 999
            new_trades = await fetch_trades_func(cc, symbol, from_id=from_id) + new_trades
            k += 1
            if k % 20 == 0:
                print('dumping cache')
                cache_df = pd.DataFrame([t for t in new_trades
                                         if t['trade_id'] not in cached_ids]).set_index('trade_id')
                cache_df.to_csv(cache_filepath + str(int(time() * 1000)) + '.csv')
                cached_ids.update(cache_df.index)
        new_trades_df = pd.DataFrame(new_trades).set_index('trade_id')
        trades_updated = pd.concat(list(chunks.values()) + [new_trades_df, cached_trades], axis=0)
        no_dup = trades_updated[~trades_updated.index.duplicated()]
        no_dup_sorted = no_dup.sort_index()
        chunk_size = 100000
        chunk_ids = no_dup_sorted.index // chunk_size * chunk_size
        for g in no_dup_sorted.groupby(chunk_ids):
            if g[0] not in chunks or len(chunks[g[0]]) != chunk_size:
                print('dumping chunk', g[0])
                g[1].to_csv(f'{filepath}{str(g[0])}.csv')
        for f in [f_ for f_ in os.listdir(cache_filepath) if f_.endswith('.csv')]:
            os.remove(cache_filepath + f)
        await cc.close()
        return no_dup_sorted[no_dup_sorted.timestamp >= age_limit_millis]
    except KeyboardInterrupt:
        await cc.close()


async def main():
    exchange = sys.argv[1]
    user = sys.argv[2]
    n_days = round(float(sys.argv[3]), 2)
    if exchange == 'bybit':
        symbol = 'BTCUSD'
    elif exchange == 'binance':
        symbol = 'BTCUSDT'
    else:
        raise Exception(f'exchange {exchange} not found')
    filename = f'{symbol}_agg_trades_{exchange}_{n_days}_days_{ts_to_date(time())[:10]}.csv'
    if os.path.isfile(filename):
        print('loading trades...')
        adf = pd.read_csv(filename).set_index('trade_id')
    else:
        print('fetching trades')
        agg_trades = await load_trades(exchange, user, symbol, n_days)
        adf = agg_trades.loc[agg_trades.price != agg_trades.price.shift(1)]
        adf.to_csv(filename)
    jackrabbit(adf, exchange)


if __name__ == '__main__':
    asyncio.run(main())

