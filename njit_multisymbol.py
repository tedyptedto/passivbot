from __future__ import annotations

import os

import numpy as np

if "NOJIT" in os.environ and os.environ["NOJIT"] == "true":
    print("not using numba")

    def njit(pyfunc=None, **kwargs):
        def wrap(func):
            return func

        if pyfunc is not None:
            return wrap(pyfunc)
        else:
            return wrap

else:
    print("using numba")
    from numba import njit

from njit_funcs import (
    calc_ema,
    calc_new_psize_pprice,
    qty_to_cost,
    cost_to_qty,
    calc_close_grid_long,
    calc_close_grid_short,
    calc_pnl_long,
    calc_pnl_short,
    round_,
    calc_min_entry_qty,
)
from njit_funcs_recursive_grid import calc_recursive_entry_long, calc_recursive_entry_short


@njit
def calc_pnl_sum(poss_long, poss_short, market_prices, c_mults):
    pnl_sum = 0.0
    for i in range(len(poss_long)):
        pnl_sum += calc_pnl_long(
            poss_long[i][1], market_prices[i], poss_long[i][0], False, c_mults[i]
        )
    for i in range(len(poss_short)):
        pnl_sum += calc_pnl_short(
            poss_short[i][1], market_prices[i], poss_short[i][0], False, c_mults[i]
        )
    return pnl_sum


@njit
def get_open_orders_long(
    close_price,
    balance,
    pos_long,
    emas,
    unstucking_close,
    inverse,
    qty_step,
    price_step,
    min_qty,
    min_cost,
    c_mult,
    cfgl,
):
    # returns entries and closes
    entries = calc_recursive_entry_long(
        balance,
        pos_long[0],
        pos_long[1],
        close_price,
        min(emas),
        inverse,
        qty_step,
        price_step,
        min_qty,
        min_cost,
        c_mult,
        cfgl[10],
        cfgl[9],
        cfgl[5],
        cfgl[14],
        cfgl[15],
        cfgl[16],
        cfgl[1],
        cfgl[3],
        cfgl[0] or cfgl[2],
    )
    closes = calc_close_grid_long(
        cfgl[4],  # backwards_tp
        balance,
        max(0.0, abs(pos_long[0]) - abs(unstucking_close[0])) if unstucking_close[0] else pos_long[0],
        pos_long[1],
        close_price,  # close price
        max(emas),
        0,  # utc_now_ms: timed AU is disabled
        0,  # prev_AU_fill_ts_close: timed AU is disabled
        inverse,
        qty_step,
        price_step,
        min_qty,
        min_cost,
        c_mult,
        cfgl[16],  # wallet_exposure_limit
        cfgl[12],  # min_markup,
        cfgl[11],  # markup_range,
        cfgl[13],  # n_close_orders,
        cfgl[3],  # auto_unstuck_wallet_exposure_threshold,
        cfgl[1],  # auto_unstuck_ema_dist,
        cfgl[0],  # auto_unstuck_delay_minutes,
        cfgl[2],  # auto_unstuck_qty_pct,
    )
    if unstucking_close[0]:
        closes = [unstucking_close] + closes
    return entries, closes


@njit
def get_open_orders_short(
    close_price,
    balance,
    pos_short,
    emas,
    unstucking_close,
    inverse,
    qty_step,
    price_step,
    min_qty,
    min_cost,
    c_mult,
    cfgs,
):
    # returns entries and closes
    entries = calc_recursive_entry_short(
        balance,
        pos_short[0],
        pos_short[1],
        close_price,
        max(emas),
        inverse,
        qty_step,
        price_step,
        min_qty,
        min_cost,
        c_mult,
        cfgs[10],
        cfgs[9],
        cfgs[5],
        cfgs[14],
        cfgs[15],
        cfgs[16],
        cfgs[1],
        cfgs[3],
        cfgs[0] or cfgs[2],
    )
    closes = calc_close_grid_short(
        cfgs[4],  # backwards_tp
        balance,
        min(0.0, -abs(pos_short[0]) + abs(unstucking_close[0]))
        if unstucking_close[0]
        else pos_short[0],
        pos_short[1],
        close_price,  # close price
        min(emas),
        0,  # utc_now_ms: timed AU is disabled
        0,  # prev_AU_fill_ts_close: timed AU is disabled
        inverse,
        qty_step,
        price_step,
        min_qty,
        min_cost,
        c_mult,
        cfgs[16],  # wallet_exposure_limit
        cfgs[12],  # min_markup,
        cfgs[11],  # markup_range,
        cfgs[13],  # n_close_orders,
        cfgs[3],  # auto_unstuck_wallet_exposure_threshold,
        cfgs[1],  # auto_unstuck_ema_dist,
        cfgs[0],  # auto_unstuck_delay_minutes,
        cfgs[2],  # auto_unstuck_qty_pct,
    )
    if unstucking_close[0]:
        closes = [unstucking_close] + closes
    return entries, closes


@njit
def calc_fills(
    pside_idx,  # 0: long, 1: short
    k,
    poss_long,
    poss_short,
    idx,
    symbol,
    balance,
    entry,
    closes,
    hlc,
    inverse,
    qty_step,
    price_step,
    min_qty,
    min_cost,
    c_mults: np.ndarray,
    cfg: np.ndarray,
    maker_fee,
):
    """
    returns fills: [tuple], new_pos: (float, float), new_balance: float
    """
    fills = []
    pos = poss_long[idx] if pside_idx == 0 else poss_short[idx]
    new_pos = (pos[0], pos[1])
    new_balance = balance
    while entry[0] != 0.0 and (
        (pside_idx == 0 and hlc[idx][1] < entry[1]) or (pside_idx == 1 and hlc[idx][0] > entry[1])
    ):
        new_pos = calc_new_psize_pprice(
            new_pos[0],
            new_pos[1],
            entry[0],
            entry[1],
            qty_step,
        )
        fee_paid = -qty_to_cost(entry[0], entry[1], inverse, c_mults[idx]) * maker_fee
        new_balance = max(new_balance * 1e-6, new_balance + fee_paid)
        new_equity = new_balance + calc_pnl_sum(
            poss_long, poss_short, hlc[:, 2], c_mults
        )  # compute total equity
        wallet_exposure = qty_to_cost(new_pos[0], new_pos[1], inverse, c_mults[idx]) / new_balance
        fills.append(
            (
                k,  # index
                symbol,
                0.0,  # realized pnl
                fee_paid,
                new_balance,
                new_equity,  # equity
                entry[0],  # fill qty
                entry[1],  # fill price
                new_pos[0],  # psize after fill
                new_pos[1],  # pprice after fill
                entry[2],  # fill type
                wallet_exposure / cfg[16],  # stuckness
            )
        )
        if "ientry" in entry[2]:
            break
        prev_eprice = entry[1]
        args = (
            new_balance,
            new_pos[0],
            new_pos[1],
            entry[1],
            entry[1],
            inverse,
            qty_step,
            price_step,
            min_qty,
            min_cost,
            c_mults[idx],
            cfg[10],
            cfg[9],
            cfg[5],
            cfg[14],
            cfg[15],
            cfg[16],
            cfg[1],
            cfg[3],
            cfg[0] or cfg[2],
        )
        if pside_idx == 0:
            entry = calc_recursive_entry_long(*args)
        else:
            entry = calc_recursive_entry_short(*args)
        if entry[1] == prev_eprice:
            break
    for close in closes:
        if (
            close[0] == 0.0
            or (pside_idx == 0 and close[1] >= hlc[idx][0])
            or (pside_idx == 1 and close[1] <= hlc[idx][1])
        ):
            break
        # close fill
        new_pos_ = (round_(new_pos[0] + close[0], qty_step), new_pos[1])
        if (pside_idx == 0 and new_pos_[0] < 0.0) or (pside_idx == 1 and new_pos_[0] > 0.0):
            print("warning: close qty greater than psize", "short" if pside_idx else "short")
            print("symbol", symbol)
            print("new_pos", new_pos)
            print("new_pos_", new_pos_)
            print("closes order", close)
            close = (-new_pos[0], close[1], close[2])
            new_pos_ = (0.0, 0.0)
        elif new_pos_[0] == 0.0:
            new_pos_ = (0.0, 0.0)
        fee_paid = -qty_to_cost(close[0], close[1], inverse, c_mults[idx]) * maker_fee
        pnl = (
            calc_pnl_long(new_pos[1], close[1], close[0], inverse, c_mults[idx])
            if pside_idx == 0
            else calc_pnl_short(new_pos[1], close[1], close[0], inverse, c_mults[idx])
        )
        new_pos = new_pos_
        new_balance = max(new_balance * 1e-6, new_balance + fee_paid + pnl)
        new_equity = new_balance + calc_pnl_sum(
            poss_long, poss_short, hlc[:, 2], c_mults
        )  # compute total equity
        wallet_exposure = qty_to_cost(new_pos[0], new_pos[1], inverse, c_mults[idx]) / new_balance
        fills.append(
            (
                k,  # index
                symbol,
                pnl,  # realized pnl
                fee_paid,
                new_balance,  # post fill
                new_equity,  # post fill
                close[0],  # fill qty
                close[1],  # fill price
                new_pos[0],  # psize after fill
                new_pos[1],  # pprice after fill
                close[2],  # fill type
                wallet_exposure / cfg[16],  # stuckness
            )
        )

    return fills, new_pos, new_balance, new_equity


@njit
def calc_AU_allowance(
    pnls: np.ndarray, balance: float, loss_allowance_pct=0.01, drop_since_peak_abs=-1.0
):
    """
    allow up to 1% drop from balance peak for auto unstuck
    """
    if drop_since_peak_abs == -1.0:
        pnl_cumsum = pnls.cumsum()
        drop_since_peak_abs = pnl_cumsum.max() - pnl_cumsum[-1]
    balance_peak = balance + drop_since_peak_abs
    drop_since_peak_pct = balance / balance_peak - 1
    AU_allowance = max(0.0, balance_peak * (loss_allowance_pct + drop_since_peak_pct))
    return AU_allowance


@njit
def backtest_multisymbol_recursive_grid(
    hlcs,
    starting_balance,
    maker_fee,
    do_longs,
    do_shorts,
    c_mults,
    symbols,
    qty_steps,
    price_steps,
    min_costs,
    min_qtys,
    live_configs,
    loss_allowance_pct,
    stuck_threshold,
    unstuck_close_pct,
):
    """
    multi symbol backtest
    all symbols share same wallet

    interval is 1m
    hlcs: [[[sym1_high_0, sym1_low_0, sym1_close_0],
            [sym1_high_1, sym1_low_1, sym1_close_1],
            ...],
           [[sym1_high_0, sym1_low_0, sym1_close_0],
            [sym1_high_1, sym1_low_1, sym1_close_1],
            ...],
           ...
           ]
    # static values
    do_longs: (True, True, ...)
    do_shorts: (True, True, ...)
    c_mults: (float, float, ...)
    symbols: (str, str, ...)
    qty_steps: (float, float, ...)
    price_steps: (float, float, ...)
    min_costs: (float, float, ...)
    min_qtys: (float, float, ...)

    # each symbol has its own config
    # no dicts, structs, classes or named tubles allowed with numba...
    # a config is a list of float values
    # indices:

    0  auto_unstuck_delay_minutes
    1  auto_unstuck_ema_dist
    2  auto_unstuck_qty_pct
    3  auto_unstuck_wallet_exposure_threshold
    4  backwards_tp
    5  ddown_factor
    6  ema_span_0
    7  ema_span_1
    8  enabled
    9  initial_eprice_ema_dist
    10 initial_qty_pct
    11 markup_range
    12 min_markup
    13 n_close_orders
    14 rentry_pprice_dist
    15 rentry_pprice_dist_wallet_exposure_weighting
    16 wallet_exposure_limit

    live_configs: [((float, float, ...), (float, float, ...)), ((float, float, ...), (float, float, ...))]
    [(long, short), (long, short), ...]

    stuck_threshold: if WE / WE_limit > stuck_threshold: consider position stuck
    """

    inverse = False

    idxs = np.arange(len(symbols))

    ll = [[z[0] for z in x] for x in live_configs]  # live configs long
    ls = [[z[1] for z in x] for x in live_configs]  # live configs short
    # disable auto unstuck
    ll = [[0.0] * 4 + x[4:] for x in ll]
    ls = [[0.0] * 4 + x[4:] for x in ls]

    balance = starting_balance
    poss_long = [(0.0, 0.0) for _ in range(len(symbols))]  # [psize: float, pprice: float]
    poss_short = [(0.0, 0.0) for _ in range(len(symbols))]  # [psize: float, pprice: float]
    fills = []
    stats = [
        (
            0,
            poss_long.copy(),
            poss_short.copy(),
            hlcs[:, 0, 2],
            balance,
            balance,
        )
    ]
    entries_long = [(0.0, 0.0, "") for _ in idxs]  # (qty: float, price: float, type: str)
    entries_short = [(0.0, 0.0, "") for _ in idxs]
    closes_long = [[(0.0, 0.0, "")] for _ in idxs]  # [(qty: float, price: float, type: str), (), ...]
    closes_short = [
        [(0.0, 0.0, "")] for _ in idxs
    ]  # [(qty: float, price: float, type: str), (), ...]

    ema_spans_long = [np.array(sorted((x[6], (x[6] * x[7]) ** 0.5, x[7]))) for x in ll]
    ema_spans_short = [np.array(sorted((x[6], (x[6] * x[7]) ** 0.5, x[7]))) for x in ll]
    ema_spans_long = [np.where(x < 1.0, 1.0, x) for x in ema_spans_long]
    ema_spans_short = [np.where(x < 1.0, 1.0, x) for x in ema_spans_short]

    # find first non zero hlcs
    first_non_zero_idxs = [0 for _ in idxs]
    for i in idxs:
        for k in range(len(hlcs[i])):
            if hlcs[i][k][2] != 0.0:
                first_non_zero_idxs[i] = k
                break
    emas_long = [np.repeat(hlcs[i][k][2], 3) for i, k in enumerate(first_non_zero_idxs)]
    emas_short = [np.repeat(hlcs[i][k][2], 3) for i, k in enumerate(first_non_zero_idxs)]

    alphas_long = [2.0 / (x + 1.0) for x in ema_spans_long]
    alphas__long = [1.0 - x for x in alphas_long]
    alphas_short = [2.0 / (x + 1.0) for x in ema_spans_short]
    alphas__short = [1.0 - x for x in alphas_short]
    any_do_long, any_do_short = False, False
    idxs_long, idxs_short = [], []
    for i in range(len(do_longs)):
        if do_longs[i]:
            idxs_long.append(i)
            any_do_long = True
    for i in range(len(do_shorts)):
        if do_shorts[i]:
            idxs_short.append(i)
            any_do_short = True

    stuck_positions_long = np.zeros(len(symbols))  # 0 is unstuck; 1 is stuck
    stuck_positions_short = np.zeros(len(symbols))  # 0 is unstuck; 1 is stuck

    unstucking_close = (0.0, 0.0, "")
    s_i, s_pside = -1, -1

    bankrupt = False
    any_stuck = False
    pnl_cumsum_running = 0.0
    pnl_cumsum_max = 0.0

    if len(symbols) == 1:
        pass
        # TODO
        """
        return backtest_single_symbol_recursive_grid(
            hlcs[0],
            starting_balance,
            maker_fee,
            do_longs[0],
            do_shorts[0],
            c_mults[0],
            symbols[0],
            qty_steps[0],
            price_steps[0],
            min_costs[0],
            min_qtys[0],
            live_configs[0],
        )
        """

    for k in range(1, len(hlcs[0])):
        any_fill = False

        # check for fills long
        for i in idxs_long:
            if hlcs[i][k][0] == 0.0:
                continue
            emas_long[i] = calc_ema(alphas_long[i], alphas__long[i], emas_long[i], hlcs[i][k][2])
            if (entries_long[i][0] > 0.0 and hlcs[i][k][1] < entries_long[i][1]) or (
                poss_long[i][0] > 0.0
                and closes_long[i][0][0] != 0.0
                and hlcs[i][k][0] > closes_long[i][0][1]
            ):
                # there were fills
                new_fills, new_pos_long, new_balance, new_equity = calc_fills(
                    0,
                    k,
                    poss_long,
                    poss_short,
                    i,
                    symbols[i],
                    balance,
                    entries_long[i],
                    closes_long[i],
                    hlcs[:, k],
                    inverse,
                    qty_steps[i],
                    price_steps[i],
                    min_qtys[i],
                    min_costs[i],
                    c_mults,
                    ll[i],
                    maker_fee,
                )
                if len(new_fills) > 0:
                    any_fill = True
                if new_equity <= 0.0:
                    bankrupt = True
                for fill in new_fills:
                    pnl_cumsum_running += fill[2]
                    pnl_cumsum_max = max(pnl_cumsum_max, pnl_cumsum_running)
                fills.extend(new_fills)
                poss_long[i] = new_pos_long
                balance = new_balance

                wallet_exposure = (
                    qty_to_cost(poss_long[i][0], poss_long[i][1], inverse, c_mults[i]) / balance
                )
                if wallet_exposure / ll[i][16] > stuck_threshold and hlcs[i][k][2] < poss_long[i][1]:
                    # is stuck and not in profit
                    any_stuck = True
                    stuck_positions_long[i] = 1.0
                else:
                    # is unstuck
                    stuck_positions_long[i] = 0.0

        # check for fills short
        for i in idxs_short:
            if hlcs[i][k][0] == 0.0:
                continue
            emas_short[i] = calc_ema(alphas_short[i], alphas__short[i], emas_short[i], hlcs[i][k][2])
            if (entries_short[i][0] != 0.0 and hlcs[i][k][0] > entries_short[i][1]) or (
                poss_short[i][0] != 0.0
                and closes_short[i][0][0] != 0.0
                and hlcs[i][k][1] < closes_short[i][0][1]
            ):
                # there were fills
                new_fills, new_pos_short, new_balance, new_equity = calc_fills(
                    1,
                    k,
                    poss_long,
                    poss_short,
                    i,
                    symbols[i],
                    balance,
                    entries_short[i],
                    closes_short[i],
                    hlcs[:, k],
                    inverse,
                    qty_steps[i],
                    price_steps[i],
                    min_qtys[i],
                    min_costs[i],
                    c_mults,
                    ls[i],
                    maker_fee,
                )
                if len(new_fills) > 0:
                    any_fill = True
                if new_equity <= 0.0:
                    bankrupt = True
                for fill in new_fills:
                    pnl_cumsum_running += fill[2]
                    pnl_cumsum_max = max(pnl_cumsum_max, pnl_cumsum_running)
                fills.extend(new_fills)
                poss_short[i] = new_pos_short
                balance = new_balance

                wallet_exposure = (
                    qty_to_cost(poss_short[i][0], poss_short[i][1], inverse, c_mults[i]) / balance
                )
                if wallet_exposure / ls[i][16] > stuck_threshold and hlcs[i][k][2] > poss_short[i][1]:
                    # is stuck and not in profit
                    any_stuck = True
                    stuck_positions_short[i] = 1.0
                else:
                    # is unstuck
                    stuck_positions_short[i] = 0.0

        s_i, s_pside = -1, -1
        unstucking_close = (0.0, 0.0, "")
        if any_stuck:
            # check if all are unstuck
            any_stuck = False
            for idx in idxs_long:
                if stuck_positions_long[idx]:
                    any_stuck = True
                    break
            for idx in idxs_short:
                if stuck_positions_short[idx]:
                    any_stuck = True
                    break

            if any_stuck:
                # find which position to unstuck
                # lowest pprice diff is chosen
                s_pside = 0  # 0==long, 1==short
                s_i = 0  # index
                lowest_pprice_diff = 100.0
                for i in idxs_long:
                    if stuck_positions_long[i]:
                        # long is stuck
                        pprice_diff = 1.0 - hlcs[i][k][2] / poss_long[i][1]
                        if pprice_diff < lowest_pprice_diff:
                            lowest_pprice_diff = pprice_diff
                            s_i = i
                            s_pside = 0
                for i in idxs_short:
                    if stuck_positions_short[i]:
                        # short is stuck
                        pprice_diff = hlcs[i][k][2] / poss_short[i][1] - 1.0
                        if pprice_diff < lowest_pprice_diff:
                            lowest_pprice_diff = pprice_diff
                            s_i = i
                            s_pside = 1
                AU_allowance = calc_AU_allowance(
                    np.array([0.0]),
                    balance,
                    loss_allowance_pct=loss_allowance_pct,
                    drop_since_peak_abs=(pnl_cumsum_max - pnl_cumsum_running),
                )
                if AU_allowance > 0.0:
                    if s_pside:  # short
                        close_price = min(hlcs[s_i][k][2], emas_short[s_i].min())  # lower ema band
                        upnl = calc_pnl_short(
                            poss_short[s_i][1],
                            hlcs[s_i][k][2],
                            poss_short[s_i][0],
                            inverse,
                            c_mults[s_i],
                        )
                        AU_allowance_pct = 1.0 if upnl >= 0.0 else min(1.0, AU_allowance / abs(upnl))
                        AU_allowance_qty = round_(
                            abs(poss_short[s_i][0]) * AU_allowance_pct, qty_steps[s_i]
                        )
                        close_qty = max(
                            calc_min_entry_qty(
                                close_price, inverse, qty_steps[s_i], min_qtys[s_i], min_costs[s_i]
                            ),
                            min(
                                abs(AU_allowance_qty),
                                round_(
                                    cost_to_qty(
                                        balance * ls[s_i][16] * unstuck_close_pct,
                                        close_price,
                                        inverse,
                                        c_mults[s_i],
                                    ),
                                    qty_steps[s_i],
                                ),
                            ),
                        )
                        unstucking_close = (abs(close_qty), close_price, "unstuck_close_short")
                    else:  # long
                        close_price = max(hlcs[s_i][k][2], emas_long[s_i].max())  # upper ema band
                        upnl = calc_pnl_long(
                            poss_long[s_i][1],
                            hlcs[s_i][k][2],
                            poss_long[s_i][0],
                            inverse,
                            c_mults[s_i],
                        )
                        AU_allowance_pct = 1.0 if upnl >= 0.0 else min(1.0, AU_allowance / abs(upnl))
                        AU_allowance_qty = round_(
                            abs(poss_long[s_i][0]) * AU_allowance_pct, qty_steps[s_i]
                        )
                        close_qty = max(
                            calc_min_entry_qty(
                                close_price, inverse, qty_steps[s_i], min_qtys[s_i], min_costs[s_i]
                            ),
                            min(
                                abs(AU_allowance_qty),
                                round_(
                                    cost_to_qty(
                                        balance * ll[s_i][16] * unstuck_close_pct,
                                        close_price,
                                        inverse,
                                        c_mults[s_i],
                                    ),
                                    qty_steps[s_i],
                                ),
                            ),
                        )
                        unstucking_close = (-abs(close_qty), close_price, "unstuck_close_long")

        # check if open orders long need to be updated
        for i in idxs_long:
            if hlcs[i][k][0] == 0.0:
                continue
            if (
                any_fill
                or poss_long[i][0] == 0.0
                or (s_pside == 0 and s_i == i and unstucking_close[0])
            ):
                # calc orders if any fill or if psize is zero or if stuck
                entries_long[i], closes_long[i] = get_open_orders_long(
                    hlcs[i][k][2],
                    balance,
                    poss_long[i],
                    emas_long[i],
                    unstucking_close if s_pside == 0 and s_i == i else (0.0, 0.0, ""),
                    inverse,
                    qty_steps[i],
                    price_steps[i],
                    min_qtys[i],
                    min_costs[i],
                    c_mults[i],
                    ll[i],
                )

        # check if open orders short need to be updated
        for i in idxs_short:
            if hlcs[i][k][0] == 0.0:
                continue
            if (
                any_fill
                or poss_short[i][0] == 0.0
                or (unstucking_close[0] and s_pside == 1 and s_i == i)
            ):
                # calc orders if any fill or if psize is zero or if stuck
                entries_short[i], closes_short[i] = get_open_orders_short(
                    hlcs[i][k][2],
                    balance,
                    poss_short[i],
                    emas_short[i],
                    unstucking_close if s_pside == 1 and s_i == i else (0.0, 0.0, ""),
                    inverse,
                    qty_steps[i],
                    price_steps[i],
                    min_qtys[i],
                    min_costs[i],
                    c_mults[i],
                    ls[i],
                )

        if k % 60 == 0:
            # update stats hourly
            equity = balance + calc_pnl_sum(poss_long, poss_short, hlcs[:, k, 2], c_mults)
            stats.append(
                (
                    k,
                    poss_long.copy(),
                    poss_short.copy(),
                    hlcs[:, k, 2],
                    balance,
                    equity,
                )
            )
            if equity <= 0.0 or bankrupt:
                # bankrupt
                break
    if stats[-1][0] != k:
        stats.append(
            (
                stats[-1][0] + 60,
                poss_long.copy(),
                poss_short.copy(),
                hlcs[:, k, 2],
                balance,
                balance + calc_pnl_sum(poss_long, poss_short, hlcs[:, k, 2], c_mults),
            )
        )
    return fills, stats


@njit
def backtest_single_symbol_recursive_grid(
    hlc,
    starting_balance,
    maker_fee,
    do_long,
    do_short,
    c_mult,
    symbol,
    qty_step,
    price_step,
    min_cost,
    min_qty,
    live_config,
):

    """
    live config tuple:
    0  auto_unstuck_delay_minutes
    1  auto_unstuck_ema_dist
    2  auto_unstuck_qty_pct
    3  auto_unstuck_wallet_exposure_threshold
    4  backwards_tp
    5  ddown_factor
    6  ema_span_0
    7  ema_span_1
    8  enabled
    9  initial_eprice_ema_dist
    10 initial_qty_pct
    11 markup_range
    12 min_markup
    13 n_close_orders
    14 rentry_pprice_dist
    15 rentry_pprice_dist_wallet_exposure_weighting
    16 wallet_exposure_limit
    """

    inverse = False

    ll = [x[0] for x in live_configs]  # live configs long
    ls = [x[1] for x in live_configs]  # live configs short

    # disable auto unstuck
    ll = [0.0] * 4 + ll[4:]
    ls = [0.0] * 4 + ls[4:]

    balance = starting_balance
    pos_long = (0.0, 0.0)  # (psize: float, pprice: float)
    pos_short = (0.0, 0.0)  # (psize: float, pprice: float)
    fills = []
    stats = [
        (
            0,
            (pos_long.copy(),),
            (pos_short.copy(),),
            hlc[0, 2],
            balance,
            balance,
        )
    ]
    entry_long = (0.0, 0.0, "")  # (qty: float, price: float, type: str)
    entry_short = (0.0, 0.0, "")
    closes_long = [(0.0, 0.0, "")]  # [(qty: float, price: float, type: str), (), ...]
    closes_short = [(0.0, 0.0, "")]  # [(qty: float, price: float, type: str), (), ...]

    ema_spans_long = np.array(sorted((ll[6], (ll[6] * ll[7]) ** 0.5, ll[7])))
    ema_spans_short = np.array(sorted((ls[6], (ls[6] * ls[7]) ** 0.5, ls[7])))
    ema_spans_long = np.where(x < 1.0, 1.0, x)
    ema_spans_short = np.where(x < 1.0, 1.0, x)

    emas_long = np.repeat(hlc[0, 2], 3)
    emas_short = np.repeat(hlc[0, 2], 3)

    alphas_long = 2.0 / (ema_spans_long + 1.0)
    alphas__long = 1.0 - alphas_long
    alphas_short = 2.0 / (ema_spans_short + 1.0)
    alphas__short = 1.0 - alphas_short

    bankrupt = False

    for k in range(1, len(hlcs[0])):
        any_fill = False

        # check for fills long
        emas_long = calc_ema(alphas_long, alphas__long, emas_long, hlc[k][2])
        if (entry_long[0] > 0.0 and hlc[k][1] < entry_long[1]) or (
            pos_long[0] > 0.0 and closes_long[0][0] != 0.0 and hlc[k][0] > closes_long[0][1]
        ):
            # there were fills
            new_fills, new_pos_long, new_balance, new_equity = calc_fills(
                0,
                k,
                (pos_long,),
                (pos_short,),
                0,
                symbol,
                balance,
                entry_long,
                closes_long,
                hlc[k],
                inverse,
                qty_step,
                price_step,
                min_qty,
                min_cost,
                (c_mult,),
                ll,
                maker_fee,
            )
            if len(new_fills) > 0:
                any_fill = True
            if new_equity <= 0.0:
                bankrupt = True
            fills.extend(new_fills)
            pos_long = new_pos_long
            balance = new_balance

        # check for fills short
        emas_short = calc_ema(alphas_short, alphas__short, emas_short, hlc[k][2])
        if (entry_short[0] != 0.0 and hlc[k][0] > entry_short[1]) or (
            pos_short[0] != 0.0 and closes_short[0][0] != 0.0 and hlc[k][1] < closes_short[0][1]
        ):
            # there were fills
            new_fills, new_pos_short, new_balance, new_equity = calc_fills(
                1,
                k,
                (pos_long,),
                (pos_short,),
                0,
                symbol,
                balance,
                entry_short,
                closes_short,
                hlc[k],
                inverse,
                qty_step,
                price_step,
                min_qty,
                min_cost,
                (c_mult,),
                ls,
                maker_fee,
            )
            if len(new_fills) > 0:
                any_fill = True
            if new_equity <= 0.0:
                bankrupt = True
            fills.extend(new_fills)
            pos_short = new_pos_short
            balance = new_balance

        # check if open orders long need to be updated
        if any_fill or pos_long[0] == 0.0:
            # calc orders if any fill or if psize is zero or if stuck
            entry_long, closes_long = get_open_orders_long(
                hlc[k][2],
                balance,
                pos_long,
                emas_long,
                (0.0, 0.0, ""),
                inverse,
                qty_step,
                price_step,
                min_qty,
                min_cost,
                c_mult,
                ll,
            )

        # check if open orders short need to be updated
        if any_fill or pos_short[0] == 0.0:
            # calc orders if any fill or if psize is zero or if stuck
            entry_short, closes_short = get_open_orders_short(
                hlc[k][2],
                balance,
                pos_short,
                emas_short,
                (0.0, 0.0, ""),
                inverse,
                qty_step,
                price_step,
                min_qty,
                min_cost,
                c_mult,
                ls,
            )

        if k % 60 == 0:
            # update stats hourly
            equity = balance + calc_pnl_sum((pos_long,), (pos_short,), hlc[k, 2], (c_mult,))
            stats.append(
                (
                    k,
                    (pos_long,),
                    (pos_short,),
                    hlc[k, 2],
                    balance,
                    equity,
                )
            )
            if equity <= 0.0 or bankrupt:
                # bankrupt
                break
    if stats[-1][0] != k:
        stats.append(
            (
                stats[-1][0] + 60,
                (pos_long,),
                (pos_short,),
                hlc[k, 2],
                balance,
                balance + calc_pnl_sum((pos_long,), (pos_short,), hlc[k, 2], (c_mult,)),
            )
        )
    return fills, stats
