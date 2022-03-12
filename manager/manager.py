import logging
import os
import sys
import yaml
from constants import INSTANCE_SIGNATURE_BASE, MANAGER_CONFIG_PATH
from instance import Instance, instances_from_config
from pm import ProcessManager
from typing import List


class Manager:
    def __init__(self):
        self.defaults = {}
        self.instances = []
        self.sync_config()

    def sync_config(self):
        '''Sync manger with config file'''
        self.instances = []

        if not os.path.exists(MANAGER_CONFIG_PATH):
            logging.error('No such file: {}'.format(MANAGER_CONFIG_PATH))
            sys.exit(1)

        with open(MANAGER_CONFIG_PATH, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        self.defaults = config['defaults']

        if 'instances' not in config or not isinstance(config['instances'], list):
            return

        for instance in config['instances']:
            self.instances.extend(instances_from_config(
                instance, self.defaults))

    def get_instances(self) -> List[Instance]:
        return self.instances

    def get_instances_length(self) -> int:
        return len(self.instances)

    def get_instance_by_id(self, instance_id) -> Instance:
        for instance in self.instances:
            if instance.get_id() == instance_id:
                return instance

        return None

    def get_running_instances(self) -> List[Instance]:
        running_instances = []
        for instance in self.instances:
            if instance.is_running():
                running_instances.append(instance)

        return running_instances

    def query_instances(self, query: List[str]) -> List[Instance]:
        '''Query instances by query string'''
        instances = []
        for instance in self.instances:
            if instance.match(query):
                instances.append(instance)

        return instances

    def get_all_passivbot_instances(self) -> List[Instance]:
        '''Get all passivbot instances running on this machine'''
        pm = ProcessManager()
        signature = '^{}'.format(' '.join(INSTANCE_SIGNATURE_BASE))
        pids = pm.get_pid(signature, all_matches=True)
        if len(pids) == 0:
            return []

        instances_cmds = [pm.info(pid) for pid in pids]
        instanaces = []
        for cmd in instances_cmds:
            args = cmd.split(' ')
            if len(args) > 3:
                args = args[3:]
            else:
                continue

            user = args[0]
            symbol = args[1]
            live_config_path = args[2]
            cfg = self.defaults.copy()
            cfg['user'] = user
            cfg['symbol'] = symbol
            cfg['live_config_path'] = live_config_path
            instance = Instance(cfg)
            if instance.is_running():
                instanaces.append(instance)

        return instanaces
