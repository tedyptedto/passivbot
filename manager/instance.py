import logging
import os
import sys
from typing import Dict, List
from constants import CONFIGS_PATH, INSTANCE_SIGNATURE_BASE, PASSIVBOT_PATH
from pm import ProcessManager


class Instance:
    def __init__(self, config):
        self.user = str(config['user'])
        self.symbol = str(config['symbol'])

        live_config_path = config['live_config_path']
        if type(live_config_path) == str and len(live_config_path) > 0:
            self.live_config_path = live_config_path
        else:
            self.live_config_path = os.path.join(
                CONFIGS_PATH, config['live_config_name'])

        if not os.path.exists(self.live_config_path):
            self.say('Config file does not exist: {}'.format(
                self.live_config_path))
            sys.exit(1)

        self.market_type = str(config['market_type']) or 'futures'
        self.lw = float(config['long_wallet_exposure_limit']) or 0.0
        self.sw = float(config['short_wallet_exposure_limit']) or 0.0
        self.ab = float(config['assigned_balance']) or 0
        self.lm = str(config['long_mode']) or 'n'
        self.sm = str(config['short_mode']) or 'm'

    def say(self, message) -> None:
        logging.info('[{}] {}'.format(self.get_id(), message))

    def get_args(self) -> List[str]:
        return [self.user, self.symbol, self.live_config_path]

    def get_flags(self) -> List[str]:
        flags = {
            '-m': {
                'value': self.market_type,
                'valid': self.market_type != 'futures'
            },
            '-lw': {
                'value': self.lw,
                'valid': self.lw > 0.0
            },
            '-sw': {
                'value': self.sw,
                'valid': self.sw > 0.0
            },
            '-ab': {
                'value': self.ab,
                'valid': self.ab > 0.0
            },
            '-lm': {
                'value': self.lm,
                'valid': self.lm != 'n'
            },
            '-sm': {
                'value': self.sm,
                'valid': self.sm != 'm'
            }
        }

        valid_flags = []
        for k, v in flags.items():
            if v['valid'] is True:
                valid_flags.append(k)
                valid_flags.append(str(v['value']))

        return valid_flags

    def get_id(self) -> str:
        return '{}-{}'.format(self.user, self.symbol)

    def get_symbol(self) -> str:
        return self.symbol

    def get_user(self) -> str:
        return self.user

    def get_pid_signature(self) -> str:
        signature = INSTANCE_SIGNATURE_BASE.copy()
        signature.extend([self.user, self.symbol])
        return '^{}'.format(' '.join(signature))

    def get_pid(self) -> int:
        pm = ProcessManager()
        return pm.get_pid(self.get_pid_signature())

    def get_pid_str(self) -> str:
        pid = self.get_pid()
        return str(pid) if pid is not None else '-'

    def get_cmd(self) -> List[str]:
        cmd = INSTANCE_SIGNATURE_BASE.copy()
        cmd.extend(self.get_args())
        cmd.extend(self.get_flags())
        return cmd

    def get_status(self) -> str:
        return 'running' if self.is_running() else 'stopped'

    def is_running(self) -> bool:
        pm = ProcessManager()
        return pm.is_running(self.get_pid_signature())

    def match(self, query: List[str], exact: bool = False) -> bool:
        parameters = {
            'id': self.get_id(),
            'pid': self.get_pid_str(),
            'symbol': self.get_symbol(),
            'user': self.get_user(),
            'status': self.get_status(),
        }

        if not exact:
            parameters = {k: v.lower() for k, v in parameters.items()}
            query = [q.lower() for q in query]

        matches = 0
        for condition in query:
            if '=' in condition:
                k, v = condition.split('=')
                if k in parameters and parameters[k].startswith(v):
                    matches += 1
                    continue

            if any(condition in v for v in parameters.values()):
                matches += 1

        return matches == len(query)

    # ---------------------------------------------------------------------------- #
    #                                 state methods                                #
    # ---------------------------------------------------------------------------- #

    def start(self, silent=False) -> bool:
        log_file = os.path.join(
            PASSIVBOT_PATH, 'logs/{}/{}.log'.format(self.user, self.symbol))
        if not os.path.exists(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file))

        cmd = self.get_cmd()

        if silent is True:
            log_file = '/dev/null'

        pm = ProcessManager()
        pm.add_nohup_process(cmd, log_file)
        self.proc_id = pm.get_pid(self.get_pid_signature(), retries=10)
        if self.proc_id is None:
            self.say('Failed to get process id. See {} for more info.'
                     .format(log_file))
            return False

        return True

    def stop(self, force=False) -> bool:
        if not self.is_running():
            return False

        pm = ProcessManager()
        pid = pm.get_pid(self.get_pid_signature())
        if pid is None:
            return False

        pm.kill(pid, force)
        return True

    def restart(self, force=False, silent=False) -> bool:
        if self.is_running():
            stopped = self.stop(force)
            if not stopped:
                return False

        return self.start(silent)


def instances_from_config(config: Dict, defaults: Dict) -> List[Instance]:
    instances = []
    for symbol in config['symbols']:
        cfg = defaults.copy()
        cfg['symbol'] = symbol
        cfg['user'] = config['user']
        for k, v in config.items():
            if k in cfg:
                cfg[k] = v
        instances.append(Instance(cfg))

    return instances
