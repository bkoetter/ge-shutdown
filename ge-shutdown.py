#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
from typing import Dict, List, Union


# check if user is in group and return True or False
# example: is_user_in_group('sapadm', 'sapsys') -> True
def is_user_in_group(user, group) -> bool:
    from grp import getgrnam
    try:
        return user in getgrnam(group).gr_mem
    except KeyError:
        print(f'Group {group} not found')
        exit(1)


# build command to list all instances
def build_command(command: str, user='sapadm') -> str:
    from getpass import getuser
    if user != 'sapadm' or not is_user_in_group(getuser(), 'sapsys'):
        command = f'sudo -n -u {user} {command}'
    return command


# execute OS command and return output
def execute_command(command: str, user=None) -> Dict[str, Union[str, int]]:
    from subprocess import CalledProcessError, run, PIPE, STDOUT
    if user:
        command = build_command(command, user)
    else:
        command = build_command(command)

    try:
        output = run(command.split(), stdout=PIPE, stderr=STDOUT, timeout=30, check=True)
        return {'output': output.stdout.decode('utf-8'), 'returncode': output.returncode}
    except CalledProcessError as e:
        if e.returncode == 1:
            print(f'Command {command} failed due to invalid parameters')
        elif e.returncode == 2:
            print(f'Command {command} failed due to timeout')
        elif e.returncode == 3 or e.returncode == 4:
            return {'output': e.output.decode('utf-8'), 'returncode': e.returncode}
        else:
            print(f'Command {command} failed due to internal error')
        sys.exit(e.returncode)
    except TimeoutError:
        print(f'Command {command} timed out')
        sys.exit(1)


# parse command output to get the instnance sid and instance number
def parse_command_output(command_output: str) -> dict:
    from re import search
    sap_instances: dict = {}
    for line in command_output.splitlines():
        if not line.startswith(' Inst Info : '):
            continue
        instance_sid, instance_number = search(r'Inst Info : ([A-Z][A-Z\d][A-Z\d]) - (\d\d)', line).groups()
        sap_instances.setdefault(instance_sid, {'nr': [], 'user': instance_sid.lower() + 'adm'})
        sap_instances[instance_sid]['nr'].append(instance_number)
    return sap_instances


# parse SAP process list
def parse_sap_process_list(command_output: str):
    # 0 starttime: 2022 07 05 19:20:14
    # 0 elapsedtime: 283:52:39
    # 0 pid: 875626
    from re import search
    # sap_process_list: List[Dict[str, str]] = []
    sap_process_list: list = []
    for line in command_output.splitlines():
        fields = search(r'\s*(\d+)\s+([a-z]+):\s+(.+)$', line)
        if fields is None:
            continue
        idx, key, value = fields.groups()
        if int(idx) not in range(-len(sap_process_list), len(sap_process_list)):
            sap_process_list.append({})
        else:
            sap_process_list[int(idx)][key] = value
    return sap_process_list


# get process list for all instances
def get_process_list_all(sap_instances) -> Dict[str, List[Dict[str, str]]]:
    sap_instances_process_list = {}
    for instance_sid in sap_instances:
        for instance_number in [sap_instances[instance_sid]['nr'] for instance_sid in sap_instances]:
            command = f'/usr/sap/hostctrl/exe/sapcontrol -format script -nr {instance_number} -function GetProcessList'
            sap_process_list = parse_sap_process_list(
                execute_command(command, sap_instances[instance_sid]['user'])['output'])
            sap_instances_process_list[instance_sid] = sap_process_list
    return sap_instances_process_list


# stop SAP system
def stop_sap_system() -> None:
    pass


def main():
    # execute command
    command_output = execute_command('/usr/sap/hostctrl/exe/saphostctrl -softtimeout 10,10,10 -function ListInstances')
    # parse command output
    sap_instances = parse_command_output(command_output['output'])
    process_list_all = get_process_list_all(sap_instances)
    for sid in process_list_all:
        for idx, list_of_instances in enumerate(process_list_all[sid]):
            print(f'{sid} -> {idx} -> {list_of_instances}')


if __name__ == '__main__':
    main()
