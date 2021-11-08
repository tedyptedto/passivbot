import argparse
import asyncio
import json
import multiprocessing
import os
import time

import numpy as np
import pyswarms as ps

from passivbot.downloader import Downloader
from passivbot.downloader import prep_config
from passivbot.optimize import get_expanded_ranges
from passivbot.optimize import single_sliding_window_run
from passivbot.utils.funcs.pure import candidate_to_live_config
from passivbot.utils.funcs.pure import denanify
from passivbot.utils.funcs.pure import get_template_live_config
from passivbot.utils.funcs.pure import numpyize
from passivbot.utils.funcs.pure import pack_config
from passivbot.utils.funcs.pure import ts_to_date
from passivbot.utils.funcs.pure import unpack_config
from passivbot.utils.procedures import add_argparse_args
from passivbot.utils.procedures import dump_live_config
from passivbot.utils.procedures import make_get_filepath

lock = multiprocessing.Lock()
BEST_OBJECTIVE = 0.0


def get_bounds(ranges: dict) -> tuple:
    return (
        np.array([float(v[0]) for k, v in ranges.items()]),
        np.array([float(v[1]) for k, v in ranges.items()]),
    )


class BacktestPSO:
    def __init__(self, data, config):
        self.data = data
        self.config = config
        self.expanded_ranges = get_expanded_ranges(config)
        for k in list(self.expanded_ranges):
            if self.expanded_ranges[k][0] == self.expanded_ranges[k][1]:
                del self.expanded_ranges[k]
        self.bounds = get_bounds(self.expanded_ranges)

    def config_to_xs(self, config):
        xs = np.zeros(len(self.bounds[0]))
        unpacked = unpack_config(config)
        for i, k in enumerate(self.expanded_ranges):
            xs[i] = unpacked[k]
        return xs

    def xs_to_config(self, xs):
        config = self.config.copy()
        for i, k in enumerate(self.expanded_ranges):
            config[k] = xs[i]
        return numpyize(denanify(pack_config(config)))

    def rf(self, xss):
        return np.array([self.single_rf(xs) for xs in xss])

    def single_rf(self, xs):
        config = self.xs_to_config(xs)
        objective, analyses = single_sliding_window_run(config, self.data)
        global lock, BEST_OBJECTIVE
        if analyses:
            try:
                lock.acquire()
                to_dump = {}
                for k in ["average_daily_gain", "score"]:
                    to_dump[k] = np.mean([e[k] for e in analyses])
                for k in ["lowest_eqbal_ratio", "closest_bkr"]:
                    to_dump[k] = np.min([e[k] for e in analyses])
                for k in ["max_hrs_no_fills", "max_hrs_no_fills_same_side"]:
                    to_dump[k] = np.max([e[k] for e in analyses])
                to_dump["objective"] = objective
                to_dump.update(candidate_to_live_config(config))
                with open(self.config["optimize_dirpath"] + "intermediate_results.txt", "a") as f:
                    f.write(json.dumps(to_dump) + "\n")
                if objective > BEST_OBJECTIVE:
                    if analyses:
                        config["average_daily_gain"] = np.mean(
                            [e["average_daily_gain"] for e in analyses]
                        )
                    dump_live_config(
                        {**config, **{"objective": objective}},
                        self.config["optimize_dirpath"] + "intermediate_best_results.json",
                    )
                    BEST_OBJECTIVE = objective
            finally:
                lock.release()
        return -objective


async def _main(args: argparse.Namespace) -> None:
    for config in await prep_config(args):
        try:

            template_live_config = get_template_live_config(config["n_spans"])
            config = {**template_live_config, **config}
            dl = Downloader(config)
            data = await dl.get_data()
            shms = [
                multiprocessing.shared_memory.SharedMemory(create=True, size=d.nbytes) for d in data
            ]
            shdata = [
                np.ndarray(d.shape, dtype=d.dtype, buffer=shms[i].buf) for i, d in enumerate(data)
            ]
            for i in range(len(data)):
                shdata[i][:] = data[i][:]
            del data
            config["n_days"] = (shdata[2][-1] - shdata[2][0]) / (1000 * 60 * 60 * 24)
            config["optimize_dirpath"] = make_get_filepath(
                os.path.join(
                    config["optimize_dirpath"], ts_to_date(time.time())[:19].replace(":", ""), ""
                )
            )

            print()
            for k in (
                keys := [
                    "exchange",
                    "symbol",
                    "starting_balance",
                    "start_date",
                    "end_date",
                    "latency_simulation_ms",
                    "do_long",
                    "do_shrt",
                    "minimum_bankruptcy_distance",
                    "maximum_hrs_no_fills",
                    "maximum_hrs_no_fills_same_side",
                    "iters",
                    "n_particles",
                    "sliding_window_size",
                    "n_spans",
                ]
            ):
                if k in config:
                    print(f"{k: <{max(map(len, keys)) + 2}} {config[k]}")
            print()

            bpso = BacktestPSO(tuple(shdata), config)

            optimizer = ps.single.GlobalBestPSO(
                n_particles=24,
                dimensions=len(bpso.bounds[0]),
                options=config["options"],
                bounds=bpso.bounds,
                init_pos=None,
            )
            # todo: implement starting configs
            cost, pos = optimizer.optimize(
                bpso.rf, iters=config["iters"], n_processes=config["num_cpus"]
            )
            print(cost, pos)
            best_candidate = bpso.xs_to_config(pos)
            print("best candidate", best_candidate)
            """
            conf = bpso.xs_to_config(xs)
            print('starting...')
            objective = bpso.rf(xs)
            print(objective)
            """
        finally:
            del shdata
            for shm in shms:
                shm.close()
                shm.unlink()


def main(args: argparse.Namespace) -> None:
    asyncio.run(_main(args))


def setup_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("pso-optimize", help="Optimize passivbot config.")
    parser.add_argument(
        "-t",
        "--start",
        type=str,
        required=False,
        dest="starting_configs",
        default=None,
        help="start with given live configs.  single json file or dir with multiple json files",
    )
    add_argparse_args(parser)
    parser.set_defaults(func=main)
