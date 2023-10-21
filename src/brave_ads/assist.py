import os
import os.path as p
from famgz_utils import print, input, rule, json_, open_folder, countdown
from os.path import join as pj
from pathlib import Path
from random import choice
from time import sleep

from .config import cfg
from .controls import ct
from .json_preferences import Preferences


def read_farmer_log():
    logs = [{'name':x.stem.split('_')[1], 'path':x} for x in Path(cfg.logs_dir).iterdir() if x.is_file and x.name.endswith('.log')]
    if not logs:
        return
    logs.reverse()
    [print(f"[bright_cyan]{i+1:>2}[white] - {dct['name']}") for i, dct in enumerate(logs)]
    item = input("[white]Enter the log number to read\n>").strip() or 1
    item = int(item-1)
    item = item if item in range(len(logs)) else 0
    path = logs[item]['path']
    os.system('cls')
    print(f"[bright_white]\nReading: [bright_cyan]{str(path)}\n")
    rule(style='bright_white')
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
        for line in lines:
            print(line)


def open_random(random_=True):
    '''
    DEPRECATED: no reason to randomly open as there's no need to mimic human activity
    No device appears to get flagged by automation inputs
    Single run session.
    Opens an device from queue.
    '''
    def reset():
        dct = [dev for dev in devs]
        json_(open_random_path, dct, indent=2)

    def read():
        return json_(open_random_path)

    devs = cfg.devs

    # create default file if not exists
    open_random_path = pj(cfg.config_dir, 'open_random.json')
    if not p.isfile(open_random_path):
        reset()

    j = read()

    avail_devs = [dev for dev in j]
    # reached all devices, resetting
    if not avail_devs:
        reset()
        j = read()
        avail_devs = [dev for dev in j]
    dev = choice(avail_devs) if random_ else avail_devs[0]

    print(f'Opening:\n[red]Dev {dev}')
    ct.run_brave(dev, '', maximized=True)
    j.append(dev)

    json_(open_random_path, j, indent=2)


@cfg.check_dev
def open_profile_dir(dev):
    path = cfg.dirs(dev, 'default')
    open_folder(path)


@cfg.check_dev
def open_profile_ads_dir(dev):
    path = cfg.dirs(dev, 'ads_service')
    open_folder(path)


def open_specific(devs):
    url = 'blank'
    input_url = input(
        '\nInput:\n'
        '- some url\n'
        '- empty to `about:blank`\n'
        '- <d> to open Profile folder\n'
        '- <a> to open Profile/ads_service folder\n'
        '- <r> to open Rewards\n\n>'
    ).strip()
    url = input_url or url
    print(
        f'\nOpening url: [white]{url}\n'
        f'[bright_white]For devs:\n {" ".join( [f"{cfg.dev_color(dev)}{dev}" for dev in devs] )}\n'
    )
    if url == 'r':
        url = 'brave://rewards/'
    for dev in devs:
        cfg.print_dev(dev, end='\n' if auto else '')
        with Preferences(dev, print_=False) as pf:
            pf.restore_browser_window()
        # open user folder
        if url == 'd':
            open_profile_dir(dev)
        elif url == 'a':
            open_profile_ads_dir(dev)
        # open brave url
        elif url.startswith('brave:'):
            ct.run_brave(dev, maximized=False, perf=False)
            sleep(1)
            ct.open_page(url)
        # open regular url
        else:
            ct.run_brave(dev, url, maximized=False, perf=False)

        if auto:
            sleep(3)
            ct.kill(print_=False, check_process=False)
        else:
            input('...')
        # cfg.close_brave(print_=False)


def main():
    global auto
    auto = input('[bright_white]Press any key to auto run mode\n>')
    while True:
        os.system('cls')
        devs = cfg.parse_devs_input()
        open_specific(devs)
