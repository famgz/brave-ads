import os
import os.path as p
import subprocess as sp
from bs4 import BeautifulSoup
from famgz_utils import print, json_, LogPrint, get_local_date_time, open_selenium
from os.path import join as pj
from pathlib import Path
from time import sleep

from .config import cfg

log_path = pj(cfg.data_dir, 'cross_earnings')
lprint = LogPrint(log_path).print


def payout_screenshots(devs_code=None, chromedriver=False):
    ''' Take earnings screenshot from the Rewards page '''
    from PIL import ImageGrab
    from .controls import ct
    from .json_preferences import Preferences

    date = str(cfg.today)
    folder_path = Path(cfg.source_dir, 'payout', date)
    if not folder_path.is_dir():
        os.makedirs(folder_path)

    url = 'brave://rewards'

    if devs_code is None:
        cfg._show_devs_menu()
        devs_code = input('>')
        devs_code = devs_code or 'cl'
        os.system('cls')

    devs = cfg.get_devs_group(devs_code)

    for dev in devs:
        cfg.print_dev(dev)
        # configure new tab zoom
        with Preferences(dev, print_=False) as pf:
            pf.zoom_ntp_out(100)
            pf.restore_browser_window()
        sleep(0.5)

        if chromedriver:
            # run brave driver
            driver = dev_driver(dev)
            sleep(1)
            driver.get(url)
            sleep(2)
            driver.refresh()
            sleep(1)

            # get earnings amount
            html = driver.page_source
            page = BeautifulSoup(html, 'lxml')
            parsed = parse_values(page)
            pending = parsed['pending']

            print(pending)

        else:
            ct.run_brave(dev)
            sleep(2)
            ct.open_page(url)
            sleep(1)
            ct.press('f5', n=2)
            sleep(1)
            print()

        # take screenshot
        ct.press('alt', 'printscreen')
        path = Path(folder_path, f'{dev}.png')
        img = ImageGrab.grabclipboard()
        img.save(path, format='PNG')

        # close browser
        if chromedriver:
            driver.close()
            driver.quit()
        else:
            ct.close_tab()


def dev_driver(dev):
    user_data = str(cfg.dirs(dev, 'user_data'))
    driver = open_selenium(headless=False, user_data_dir=user_data)
    return driver


def parse_values(page:BeautifulSoup) -> dict:
    ''' To be executed any day before payout otherwise pending won't be found '''
    dct = {}
    # for item in ('balance', 'earnings'):  # TODO tags changed
    #     dct[item] = page.find('div', class_=lambda x: x and x.startswith(f'{item}Panel--'))\
    #                     .find('div', class_=lambda x: x and x.startswith('batAmount--'))\
    #                     .select_one('span.amount')\
    #                     .text.strip()
    #     dct[item] = '0' if dct[item] == '0.000' else dct[item]

    pending = page.select_one('span.rewards-payment-amount')
    if pending:
        pending = pending.select_one('span.amount').text.strip()
    dct['pending'] = pending or 0
    return dct


def run_(dev):
    return
    cfg.close_brave(print_=False)
    cfg.restore_browser_window(dev)
    command = r'"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=8888"'
    prog = sp.Popen(command, stdin=sp.PIPE, stdout=sp.DEVNULL)
    prog.stdin.write(b'')
    prog.communicate()
    page = dev_driver()
    val = parse_values(page)
    return val


def cross_earnings():
    data = json_(pj(cfg.data_dir, 'earnings.json'))
    lprint(get_local_date_time())
    lprint(f'\n{"":11}{"previous":>10}{"pending":>10}{"leavings":>10}{"pend+leav":>10}{"diff":>10}')
    for dev, data in data.items():
        lprint(f'[red]{dev}')
        v_color = 'white'
        dates = [date for date in data]
        if dates:
            dates.sort()
            last_date = dates[-1]
            old = data[last_date]['earnings']
            values = run_(dev)
            pending = values['pending']
            leavings = values['earnings']
            pend_leav = (float(pending) + float(leavings))
            diff = pend_leav - float(old)
            lprint(f' [{v_color}]{last_date:10}[bright_white]{old:>10}{pending:>10}[white]{leavings:>10}{pend_leav:>10.3f}{diff:>10.3f}')


def main():
    ''' To be execeuted on the last hour of the month '''
    path = pj(cfg.data_dir, 'earnings.json')
    if not p.isfile(path):
        dct = {dev:{} for dev in cfg.devs}
        json_(path, dct)

    results = json_(path)

    today = str(cfg.today)

    print(f'{"":24}{"balance":>11}  {"earnings":>11}')
    for dev in cfg.devs:
        print(f'[red]{dev}')
        v_color = 'white'

        val = run_(dev)

        results.setdefault(dev, {}).setdefault(today, {})
        results[dev][today] = val
        print(f' [{v_color}]{"":23} [white]{val["balance"]:>6}[bright_black] BAT   [white]{val["earnings"]:>6}[bright_black] BAT')

        json_(pj(cfg.data_dir, 'earnings.json'), results, backup=True, indent='\t', sort_keys=True)
