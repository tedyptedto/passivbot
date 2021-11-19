import argparse
import asyncio
import glob
import logging
import os
import pprint
import shutil
import sys
import time
from collections import OrderedDict
from typing import Union

import nevergrad as ng
import numpy as np
import psutil
import ray
from ray import tune
from ray.tune.schedulers import AsyncHyperBandScheduler
from ray.tune.suggest import ConcurrencyLimiter
from ray.tune.suggest.nevergrad import NevergradSearch

from passivbot.backtest import backtest
from passivbot.backtest import plot_wrap
from passivbot.downloader import Downloader
from passivbot.utils.funcs.njit import round_dynamic
from passivbot.utils.funcs.pure import analyze_fills
from passivbot.utils.funcs.pure import get_template_live_config
from passivbot.utils.funcs.pure import pack_config
from passivbot.utils.funcs.pure import ts_to_date
from passivbot.utils.funcs.pure import unpack_config
from passivbot.utils.procedures import add_argparse_args
from passivbot.utils.procedures import load_live_config
from passivbot.utils.procedures import prepare_optimize_config
from passivbot.utils.reporter import LogReporter

log = logging.getLogger(__name__)

os.environ["TUNE_GLOBAL_CHECKPOINT_S"] = "240"


def get_expanded_ranges(config: dict) -> dict:
    updated_ranges = OrderedDict()
    unpacked = unpack_config(get_template_live_config())
    for k0 in unpacked:
        if "£" in k0 or k0 in config["ranges"]:
            for k1 in config["ranges"]:
                if k1 in k0:
                    updated_ranges[k0] = config["ranges"][k1]
                    if "wallet_exposure_limit" in k0:
                        updated_ranges[k0] = [
                            updated_ranges[k0][0],
                            min(updated_ranges[k0][1], config["max_leverage"]),
                        ]
    return updated_ranges


def create_config(config: dict) -> dict:
    updated_ranges = get_expanded_ranges(config)
    template = get_template_live_config()
    template["long"]["enabled"] = config["do_long"]
    template["short"]["enabled"] = config["do_short"]
    unpacked = unpack_config(template)
    for k in updated_ranges:
        side = "long" if "long" in k else ("short" if "short" in k else "")
        if updated_ranges[k][0] != updated_ranges[k][1] and (not side or config[f"do_{side}"]):
            unpacked[k] = tune.uniform(updated_ranges[k][0], updated_ranges[k][1])
        else:
            unpacked[k] = updated_ranges[k][0]
    return {**config, **unpacked, **{"ranges": updated_ranges}}


def clean_start_config(start_config: dict, config: dict) -> dict:
    clean_start = {}
    for k, v in unpack_config(start_config).items():
        if k in config:
            if isinstance(config[k], (ray.tune.sample.Float, ray.tune.sample.Integer)):
                clean_start[k] = min(max(v, config["ranges"][k][0]), config["ranges"][k][1])
    return clean_start


def clean_result_config(config: dict) -> dict:
    for k, v in config.items():
        if isinstance(v, np.float64):
            config[k] = float(v)
        if isinstance(v, (np.int64, np.int32, np.int16, np.int8)):
            config[k] = int(v)
    return config


def iter_slices_full_first(data, sliding_window_days, max_span):
    yield data
    yield from iter_slices(data, sliding_window_days, max_span)


def iter_slices(data, sliding_window_days: float, max_span: int):
    sliding_window_ms = sliding_window_days * 24 * 60 * 60 * 1000
    span_ms = data[-1][0] - data[0][0]
    max_span_ms = max_span * 60 * 1000
    if sliding_window_ms > span_ms * 0.999 - max_span_ms:
        yield data
        return
    sample_size_ms = data[1][0] - data[0][0]
    samples_per_window = sliding_window_ms / sample_size_ms
    max_span_ito_n_samples = max_span * 60 / (sample_size_ms / 1000)
    n_windows = int(np.round(span_ms / sliding_window_ms)) + 1
    for x in np.linspace(len(data) - samples_per_window, max_span_ito_n_samples, n_windows):
        start_i = max(0, int(x - max_span_ito_n_samples))
        end_i = min(len(data), int(round(start_i + samples_per_window + max_span_ito_n_samples)))
        yield data[start_i:end_i]
    yield from iter_slices(data, sliding_window_days * 2, max_span)


def objective_function(
    analysis: dict, config: dict, metric="adjusted_daily_gain"
) -> (float, bool, str):
    if analysis["n_fills"] == 0:
        return -1.0
    obj = analysis[metric]
    break_early = False
    line = ""
    for ckey, akey in [
        ("maximum_hrs_stuck", "hrs_stuck_max"),
        ("maximum_hrs_stuck_same_side", "hrs_stuck_max"),
        ("maximum_hrs_stuck_avg", "hrs_stuck_avg"),
    ]:
        # minimize these
        if config[ckey] != 0.0:
            new_obj = obj * min(1.0, config[ckey] / analysis[akey])
            obj = -abs(new_obj) if (obj < 0.0 or analysis[akey] < 0.0) else new_obj
            if config["break_early_factor"] != 0.0 and analysis[akey] > config[ckey] * (
                1 + config["break_early_factor"]
            ):
                break_early = True
                line += f" broke on {ckey} {round_dynamic(analysis[akey], 5)}"
    for ckey, akey in [
        ("minimum_bankruptcy_distance", "closest_bkr"),
        ("minimum_equity_balance_ratio", "eqbal_ratio_min"),
    ]:
        # maximize these
        if config[ckey] != 0.0:
            new_obj = obj * min(1.0, analysis[akey] / config[ckey])
            obj = -abs(new_obj) if (obj < 0.0 or analysis[akey] < 0.0) else new_obj
            if config["break_early_factor"] != 0.0 and analysis[akey] < config[ckey] * (
                1 - config["break_early_factor"]
            ):
                break_early = True
                line += f" broke on {ckey} {round_dynamic(analysis[akey], 5)}"
    for ckey, akey in [("minimum_slice_adg", "average_daily_gain")]:
        # absolute requirements
        if analysis[akey] < config[ckey]:
            break_early = True
            line += f" broke on {ckey} {round_dynamic(analysis[akey], 5)}"
    return obj, break_early, line


def single_sliding_window_run(config, data, do_print=True) -> (float, [dict]):
    analyses = []
    objective = 0.0
    n_days = config["n_days"]
    metric = config["metric"] if "metric" in config else "adjusted_daily_gain"
    if config["sliding_window_days"] == 0.0:
        sliding_window_days = n_days
    else:
        # sliding window n days should be greater than max hrs no fills
        sliding_window_days = min(
            n_days,
            max(
                [
                    config["maximum_hrs_stuck"] * 2.1 / 24,
                    config["maximum_hrs_stuck_same_side"] * 2.1 / 24,
                    config["sliding_window_days"],
                ]
            ),
        )
    max_span = config["max_span"] if "max_span" in config else 0
    for z, data_slice in enumerate(
        iter_slices(data, sliding_window_days, max_span=int(round(max_span)))
    ):
        if len(data_slice[0]) == 0:
            log.info("debug b no data")
            continue
        try:
            packed = pack_config(config)
            fills, stats = backtest(packed, data_slice)
        except Exception as e:
            log.error(e)
            break
        _, _, analysis = analyze_fills(fills, stats, config)
        analysis["score"], do_break, line = objective_function(analysis, config, metric=metric)
        analysis["score"] *= analysis["n_days"] / config["n_days"]
        analyses.append(analysis)
        objective = np.sum([e["score"] for e in analyses]) * max(
            1.01, config["reward_multiplier_base"]
        ) ** (z + 1)
        analyses[-1]["objective"] = objective
        line = (
            f'{str(z).rjust(3, " ")} adg {analysis["average_daily_gain"]:.4f}, '
            f'bkr {analysis["closest_bkr"]:.4f}, '
            f'eqbal {analysis["eqbal_ratio_min"]:.4f} n_days {analysis["n_days"]:.1f}, '
            f'score {analysis["score"]:.4f}, objective {objective:.4f}, '
            f'hrs stuck ss {str(round(analysis["hrs_stuck_max"], 1)).zfill(4)}, ' + line
        )
        if do_print:
            log.info(line)
        if do_break:
            break
    return objective, analyses


def simple_sliding_window_wrap(config, data, do_print=False):
    objective, analyses = single_sliding_window_run(config, data, do_print=do_print)
    if not analyses:
        tune.report(
            obj=0.0,
            min_adg=0.0,
            avg_adg=0.0,
            min_bkr=0.0,
            eqbal_ratio_min=0.0,
            hrs_stuck_max=1000.0,
            hrs_stuck_max_ss=1000.0,
            hrs_stuck_max_avg=1000.0,
            hrs_stuck_avg_avg=1000.0,
            n_slc=0,
        )
    else:
        tune.report(
            obj=objective,
            min_adg=np.min([r["average_daily_gain"] for r in analyses]),
            avg_adg=np.mean([r["average_daily_gain"] for r in analyses]),
            min_bkr=np.min([r["closest_bkr"] for r in analyses]),
            eqbal_ratio_min=np.min([r["eqbal_ratio_min"] for r in analyses]),
            hrs_stuck_max=np.max([r["hrs_stuck_max"] for r in analyses]),
            hrs_stuck_max_ss=np.max([r["hrs_stuck_max"] for r in analyses]),
            hrs_stuck_max_avg=np.max([r["hrs_stuck_avg"] for r in analyses]),
            hrs_stuck_avg_avg=np.mean([r["hrs_stuck_avg"] for r in analyses]),
            n_slc=len(analyses),
        )


def backtest_tune(data: np.ndarray, config: dict, current_best: Union[dict, list] = None):
    memory = int(sys.getsizeof(data) * 1.2)
    virtual_memory = psutil.virtual_memory()
    log.info(f"data size in mb {memory / (1000 * 1000):.4f}")
    if (virtual_memory.available - memory) / virtual_memory.total < 0.1:
        log.info("Available memory would drop below 10%. Please reduce the time span.")
        return None
    config = create_config(config)
    log.info("tuning:")
    for k, v in config.items():
        if isinstance(v, (ray.tune.sample.Float, ray.tune.sample.Integer)):
            log.info("%s %s", k, (v.lower, v.upper))
    phi1 = 1.4962
    phi2 = 1.4962
    omega = 0.7298
    if "options" in config:
        phi1 = config["options"]["c1"]
        phi2 = config["options"]["c2"]
        omega = config["options"]["w"]
    current_best_params = []
    if current_best is not None:
        if isinstance(current_best, list):
            for c in current_best:
                c = clean_start_config(c, config)
                if c not in current_best_params:
                    current_best_params.append(c)
        else:
            current_best = clean_start_config(current_best, config)
            current_best_params.append(current_best)

    ray.init(
        num_cpus=config["num_cpus"], object_store_memory=memory if memory > 4000000000 else None
    )  # , logging_level=logging.FATAL, log_to_driver=False)
    pso = ng.optimizers.ConfiguredPSO(
        transform="identity", popsize=config["n_particles"], omega=omega, phip=phi1, phig=phi2
    )
    algo = NevergradSearch(optimizer=pso, points_to_evaluate=current_best_params)
    algo = ConcurrencyLimiter(algo, max_concurrent=config["num_cpus"])
    scheduler = AsyncHyperBandScheduler()

    log.info("Simple sliding window optimization")

    parameter_columns = []
    for side in ["long", "short"]:
        if config[f"{side}£enabled"]:
            parameter_columns.append(f"{side}£grid_span")
            parameter_columns.append(f"{side}£eprice_pprice_diff")
            parameter_columns.append(f"{side}£eprice_exp_base")
            parameter_columns.append(f"{side}£secondary_pprice_diff")
            parameter_columns.append(f"{side}£min_markup")

    backtest_wrap = tune.with_parameters(
        simple_sliding_window_wrap,
        data=data,
        do_print=(config["print_slice_progress"] if "print_slice_progress" in config else True),
    )
    analysis = tune.run(
        backtest_wrap,
        metric="obj",
        mode="max",
        name="search",
        search_alg=algo,
        scheduler=scheduler,
        num_samples=config["iters"],
        config=config,
        verbose=1,
        reuse_actors=True,
        local_dir=config["optimize_dirpath"],
        progress_reporter=LogReporter(
            metric_columns=[
                "min_adg",
                "avg_adg",
                "min_bkr",
                "eqbal_ratio_min",
                "hrs_stuck_max",
                "hrs_stuck_max_ss",
                "hrs_stuck_max_avg",
                "hrs_stuck_avg_avg",
                "n_slc",
                "obj",
            ],
            parameter_columns=parameter_columns,
        ),
        raise_on_failed_trial=False,
    )
    ray.shutdown()
    log.info("Cleaning up temporary optimizer data...")
    try:
        shutil.rmtree(os.path.join(config["optimize_dirpath"], "search"))
    except Exception as e:
        log.info("Failed cleaning up: %s", e)
    return analysis


def save_results(analysis, config):
    df = analysis.results_df
    df.reset_index(inplace=True)
    df.rename(
        columns={column: column.replace("config.", "") for column in df.columns}, inplace=True
    )
    df = df.sort_values("obj", ascending=False)
    df.to_csv(os.path.join(config["optimize_dirpath"], "results.csv"), index=False)
    log.info("Best candidate found:\n%s", pprint.pformat(analysis.best_config))


async def execute_optimize(config):
    if not (config["do_long"] and config["do_short"]):
        if not (config["do_long"] or config["do_short"]):
            raise Exception("both long and short disabled")
        log.info(
            f"{'long' if config['do_long'] else 'short'} only, setting maximum_hrs_stuck ="
            " maximum_hrs_stuck_same_side"
        )
        config["maximum_hrs_stuck"] = config["maximum_hrs_stuck_same_side"]
    downloader = Downloader(config)
    for k in (
        keys := [
            "exchange",
            "symbol",
            "market_type",
            "starting_balance",
            "start_date",
            "end_date",
            "latency_simulation_ms",
            "do_long",
            "do_short",
            "minimum_bankruptcy_distance",
            "maximum_hrs_stuck",
            "maximum_hrs_stuck_same_side",
            "maximum_hrs_stuck_avg",
            "iters",
            "n_particles",
            "sliding_window_days",
            "metric",
            "min_span",
            "max_span",
            "n_spans",
        ]
    ):
        if k in config:
            log.info(f"{k: <{max(map(len, keys)) + 2}} {config[k]}")
    data = await downloader.get_sampled_ticks()
    config["n_days"] = (data[-1][0] - data[0][0]) / (1000 * 60 * 60 * 24)
    config["optimize_dirpath"] = os.path.join(
        config["optimize_dirpath"], ts_to_date(time.time())[:19].replace(":", ""), ""
    )

    start_candidate = None
    if config["starting_configs"] is not None:
        try:
            if os.path.isdir(config["starting_configs"]):
                start_candidate = [
                    load_live_config(f)
                    for f in glob.glob(os.path.join(config["starting_configs"], "*.json"))
                ]
                log.info("Starting with all configurations in directory.")
            else:
                start_candidate = load_live_config(config["starting_configs"])
                log.info("Starting with specified configuration.")
        except Exception as e:
            log.error("Could not find specified configuration: %s", e)
    analysis = backtest_tune(data, config, start_candidate)
    if analysis:
        save_results(analysis, config)
        config.update(clean_result_config(analysis.best_config))
        plot_wrap(pack_config(config), data)


async def _main(args: argparse.Namespace) -> None:
    config = await prepare_optimize_config(args)
    await execute_optimize(config)


def main(args: argparse.Namespace) -> None:
    asyncio.run(_main(args))


def setup_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o",
        "--optimize_config",
        type=str,
        required=False,
        dest="optimize_config_path",
        default="configs/optimize/default.hjson",
        help="optimize config hjson file",
    )
    parser.add_argument(
        "-t",
        "--start",
        type=str,
        required=False,
        dest="starting_configs",
        default=None,
        help="start with given live configs.  single json file or dir with multiple json files",
    )
    parser.add_argument(
        "-i",
        "--iters",
        type=int,
        required=False,
        dest="iters",
        default=None,
        help="n optimize iters",
    )
    add_argparse_args(parser)
    parser.set_defaults(func=main)