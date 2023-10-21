import errno
import functools
import os
import shutil
import subprocess as sp
import sys
import time
from datetime import datetime, date, timezone
from famgz_utils import (
    run,
    print,
    input,
    json_,
    f_time,
    timeit,
    timestamp_to_full_date,
    get_running_processes,
    is_valid_uuid,
    func_name
)
from pathlib import Path
from time import sleep
from timeit import default_timer as timer
from types import SimpleNamespace


class Config:

    @staticmethod
    def parse_dev(dev):
        devs = _all_devs

        if dev in devs:
            return dev

        if not dev:
            return None

        if not isinstance(dev, (str, int)):
            return None

        if isinstance(dev, str):
            if not dev.isdigit():
                dev = ''.join( [x for x in dev if x.isdigit()] )
                if not dev.isdigit():
                    return None
            dev = str(int(dev))

        elif isinstance(dev, int):
            dev = str(dev)

        dev = dev.zfill(3)

        if dev not in devs:
            return None

        return dev


    @staticmethod
    def check_dev(func):
        ''' Decorator function to validate dev through `parse_dev` '''
        @functools.wraps(func)
        def inner(*args, **kwargs):
            # t1 = timer()
            if 'dev' in kwargs:
                kwargs['dev'] = Config.parse_dev(kwargs['dev'])
            else:
                args = list(args)
                check = dict(zip(func.__code__.co_varnames, args))
                if 'dev' in check:
                    dev = Config.parse_dev(check['dev'])
                    index = list(check).index('dev')
                    args[index] = dev
                elif 'dev' in kwargs:
                    kwargs['dev'] = Config.parse_dev(kwargs['dev'])

            # print(args)
            # print(kwargs)
            # print(f_time(None, timer()-t1, decimal=15))
            return func(*args, **kwargs)
        return inner


    def __init__(self) -> None:
        self.day_in_sec = 24 * 60 * 60  # 86400 seconds
        self.hour_in_sec = 60 * 60      # 3600 seconds
        self.minute_in_sec = 60         # 60 seconds

        self._core_paths()
        self._first_run_check()
        self._core_json()
        self._core_devs()
        self._check_duplicate_devs()


    @property
    def now(self):
        return time.time()  # in timestamp


    @property
    def now_utc(self):
        now_utc = datetime.now().utcnow()
        return now_utc.timestamp()  # in timestamp


    @property
    def today(self):
        return date.today()  # in full date YYYY/MM/DD


    def brave_version(self):
        path = Path('C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application')
        folder = [x.name for x in path.iterdir() if x.is_dir()][0]
        chromium_version = folder[:3]
        brave_version_str = folder[4:]
        brave_version_int = int("".join( [x for x in brave_version_str if x.isdigit()] ))
        return {
            'chromium_version': chromium_version,
            'brave_version_str': brave_version_str,
            'brave_version_int': brave_version_int,
        }


    def _core_paths(self):
        # folders
        self.source_dir = Path(__file__).resolve().parent
        self.config_dir = Path(self.source_dir, 'config')
        self.data_dir   = Path(self.source_dir, 'data'  )
        self.temp_dir   = Path(self.source_dir, 'temp'  )
        self.logs_dir   = Path(self.source_dir, 'logs'  )
        self._folders = [
            self.config_dir,
            self.data_dir,
            self.temp_dir,
            self.logs_dir,
        ]
        # json files
        self.fp_config_json   = Path(self.config_dir, 'config.json')
        self.fp_creators_json = Path(self.config_dir, 'creators.json')
        self.fp_excpt_json    = Path(self.config_dir, 'excpt.json')
        self.fp_farmer_json   = Path(self.config_dir, 'farmer.json')
        self.fp_urls_json     = Path(self.config_dir, 'urls.json')
        self.fp_wallets_json  = Path(self.config_dir, 'wallets.json')

        print(f'[bright_black]{self.source_dir}')


    def _core_devs(self):
        global _devs
        global _flagged_devs
        global _claim_devs
        global _frozen_devs
        global _all_devs

        self._devs_folder    = Path(self.config_json['devs_folders']['devs']).resolve()
        self._flagged_folder = Path(self.config_json['devs_folders']['flagged_devs']).resolve()
        self._claim_folder   = Path(self.config_json['devs_folders']['claim_devs']).resolve()
        self._frozen_folder  = Path(self.config_json['devs_folders']['frozen_devs']).resolve()

        self._devs_folder    = self._devs_folder    if self._devs_folder.is_dir()    else Path('C:\\brave-ads\\devs').resolve()
        self._flagged_folder = self._flagged_folder if self._flagged_folder.is_dir() else Path('C:\\brave-ads\\flagged').resolve()
        self._claim_folder   = self._claim_folder   if self._claim_folder.is_dir()   else Path('C:\\brave-ads\\claim').resolve()
        self._frozen_folder  = self._frozen_folder  if self._frozen_folder.is_dir()  else Path('C:\\brave-ads\\frozen').resolve()

        for path in (self._devs_folder, self._flagged_folder, self._claim_folder, self._frozen_folder):
            if not path.is_dir():
                os.makedirs(path)

        self._min_dev = '001'
        self._max_dev = '999'
        self._first_flagged = '901'

        # using redundant global instances to satisfy @check_dev only
        _devs         = [x.name for x in self._devs_folder.iterdir()    if x.is_dir() and x.name.isdigit()]
        _flagged_devs = [x.name for x in self._flagged_folder.iterdir() if x.is_dir() and x.name.isdigit()]
        _claim_devs   = [x.name for x in self._claim_folder.iterdir()   if x.is_dir() and x.name.isdigit()]
        _frozen_devs  = [x.name for x in self._frozen_folder.iterdir()  if x.is_dir() and x.name.isdigit()]
        _all_devs = _devs + _flagged_devs + _claim_devs + _frozen_devs
        _all_devs.sort()

        self.devs         = _devs
        self.flagged_devs = _flagged_devs
        self.claim_devs   = _claim_devs
        self.frozen_devs  = _frozen_devs
        self.all_devs     = _all_devs
        self.all_devs_groups = (self.devs, self.flagged_devs, self.claim_devs, self.frozen_devs)

        self._devs_groups = {
            'd': {
                'name': 'devs',
                'description': 'regular devs to farm',
                'color': '[bright_blue]',
                'folder': self._devs_folder,
                'devs': self.devs
            },
            'fl': {
                'name': 'flagged_devs',
                'description': 'flagged devs with some BAT stored',
                'color': '[bright_yellow]',
                'folder': self._flagged_folder,
                'devs': self.flagged_devs
            },
            'cl': {
                'name': 'claim_devs',
                'description': 'farmed devs ready to claim',
                'color': '[bright_magenta]',
                'folder': self._claim_folder,
                'devs': self.claim_devs
            },
            'fr': {
                'name': 'frozen_devs',
                'description': 'farmed and claimed devs ready to verify/tip',
                'color': '[bright_cyan]',
                'folder': self._frozen_folder,
                'devs': self.frozen_devs
            },
            'all': {
                'name': 'all_devs',
                'description': 'devs altogether',
                'color': '[bright_white]',
                'folder': None,
                'devs': self.all_devs
            },
        }

        self._devs_info = {}
        for devs_code, data in self._devs_groups.items():
            if devs_code == 'all':
                continue
            devs = data['devs']
            for dev in devs:
                self._devs_info[dev] = {
                    'devs_code': devs_code,
                    'devs_name': data['name'],
                    'index': devs.index(dev),
                    'color': data['color'],
                    'folder': Path(data['folder'], dev)
                }


    def _core_json(self):
        self.config_json   = json_(self.fp_config_json)
        self.creators_json = json_(self.fp_creators_json)
        self.excpt_json    = json_(self.fp_excpt_json)
        self.farmer_json   = json_(self.fp_farmer_json)
        self.urls_json     = json_(self.fp_urls_json)
        self.wallets_json  = json_(self.fp_wallets_json)


    def update_json(self, file):
        files = {
            'config':   {'path': self.fp_config_json,   'data': self.config_json},
            'creators': {'path': self.fp_creators_json, 'data': self.creators_json},
            'excpt':    {'path': self.fp_excpt_json,    'data': self.excpt_json},
            'farmer':   {'path': self.fp_farmer_json,   'data': self.farmer_json},
            'urls':     {'path': self.fp_urls_json,     'data': self.urls_json},
            'wallets':  {'path': self.fp_wallets_json,  'data': self.wallets_json},
        }
        path = files[file]['path']
        data = files[file]['data']
        json_(path, data, backup=True, indent='\t', ensure_ascii=False)


    def _first_run_check(self):
        self._check_folders()
        self._check_files()


    def _check_folders(self):
        for folder in self._folders:
            if not folder.exists():
                Path.mkdir(folder, parents=True)


    def _check_files(self):
        # config.json
        if not self.fp_config_json.exists():
            content = {
                "backups": {
                    "folder": "C:/brave/backups",
                    "routines": {}
                },
                "devs_folders": {
                    "devs": "C:/brave-ads/devs",
                    "flagged_devs": "C:/brave-ads/flagged",
                    "claim_devs": "C:/brave-ads/claim",
                    "frozen_devs": "C:/brave-ads/frozen"
                },
                "creators": [],
                "windows_display_scale": 100
            }
            json_(self.fp_config_json, content, indent='\t')

        # creators.json
        if not self.fp_creators_json.exists():
            content = {
                'channels': {},
                'ledger': {}
            }
            json_(self.fp_creators_json, content)

        # urls.json
        if not self.fp_urls_json.exists():
            content = {'crypto':{'crypto':['https://ethereum.org/en/']}}
            json_(self.fp_urls_json, content, indent='\t')

        # wallets.json
        if not self.fp_wallets_json.exists():
            content = {}
            json_(self.fp_wallets_json, content)

        # excpt.json
        if not self.fp_excpt_json.exists():
            # these values should be compared with >= or <
            content = {
                'min_values': {
                    'pn':  0.005,
                    'nt':  0,
                    'ic':  0,
                    'ptr': 0.1,
                },
                'bad_advtids': [],
                'bad_csids': [],
            }
            json_(self.fp_excpt_json, content, indent='\t')

        # farmer.json
        if not self.fp_farmer_json.exists():
            content = {
                "README": "Please preserve the exact data string structure while editing otherwise it breaks: `data | type: comment`",
                "EARN": "1 | bool: major farm switch; skip earning if outside PERIOD_FULLDAY",
                "DEVS_TYPE": "1 | int: choose devs group; d=devs fl=flagged_devs cl=claim_devs fr=frozen_devs all=all_devs; Can also concatenate groups with `+` eg.: <fl+cl>",
                "FIRST_DEV": " | dev: first dev to farm; if not exists fallback to first known dev",
                "LAST_DEV": " | dev: last dev to farm; if not exists fallback to last known dev",
                "PERIOD_FULLDAY": "21,22,23,00,01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20 | list: as reference",
                "PERIOD_CATALOG": "21,22,23,00,01,02,03,04,05,06,07,08,__,__,__,__,__,__,__,__,__,__,__,__ | list: hours full catalog",
                "PERIOD_LONG_PN": "__,__,__,__,__,__,__,__,__,__,__,__,09,10,11,12,13,14,15,16,17,18,19,20 | list: hours to insist pn",
                "PERIOD_ALLOWNT": "21,22,23,00,01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20 | list: hours to allow nt",
                "REFILL_UNB_TOK": "1 | bool: to refill unblinded tokens periodically",
                "SEGMENTS_DEBUG": "0 | bool: print all segment's urls and infos",
                "FILTER_URLS": "1 | bool: ignore low ptr segment's urls, if exists",
                "MAX_CLIENT_HISTORY_SIZE": "10 | int: max size of ad entries on dev's client.json > adsShownHistory",
                "N_DEVS_TO_ESCAPE_LOW_PTR": "15 | number of active devices to try escape from low ptr farmer cycle; doubled during not PERIOD_CATALOG ",
                "IDLE": "1 | bool: idle's status on program initialization",
                "IDLE_RECONCILE": "1 | bool: reconcile during idle; fallback to SHOULD_VISIT",
                "IDLE_N_VISIT": "0 | bool: visit during idle; fallback to STAND_BY_DURATION",
                "IDLE_STAND_BY_DURATION": "5 | minutes: just wait during idle",
                "IDLE_N_VISITS": "2 | int: number of url access on VISIT",
                "RECONCILE_N_MEAN_SLOTS": "12 | int: do not change! average number of devs to open; max out to 14 devices which is 8GB RAM safe limit",
                "RECONCILE_DUR_PER_ROUND": "2 | minutes: comment",
                "RECONCILE_DUR_PER_DEV": "0.5 | minutes: comment",
                "RECONCILE_DUR_PER_CONF": "0.25 | minutes: comment",
                "RECONCILE_MIN_DURATION": "2 | minutes: comment",
                "RECONCILE_OPEN_REWARDS": "0 | bool: open brave://rewards-internals on each reconciling dev to fasten debug",
                "PN_ONE_PAGE_PER_TRY": "1 | bool: only open 1 page per pn try; otherwise 1 page per pn trigger",
                "PN_TRIES_AFTER_IC": "1 | int: number of pn tries after ic",
                "PN_TRIES_LONG": "4 | int: number of pn tries on PERIOD_CATALOG",
                "PN_TRIGGERS_PER_TRY_LONG": "3 | int: number of pn triggers per tries on PERIOD_CATALOG",
                "PN_TRIES_SHORT": "1 | int: number of pn tries not on PERIOD_CATALOG",
                "PN_TRIGGERS_PER_TRY_SHORT": "3 | int: number of pn triggers per tries not on PERIOD_CATALOG",
                "PN_RETRY_BY_RELAUNCH": "1 | bool: relaunch browser and retry pn;  triggers priority?",
                "NT_BY_RELAUNCH": "0 | bool: deprecated! trigger nt by relauching the browser",
                "NT_BY_SWITCH_TAB": "1 | bool: trigger nt by alternating new tab with other tab; fallback to trigger by refresh tab (not effective)",
                "NT_MIN_N_TO_TRIGGER": "3 | int: minimum available nt ads to trigger",
                "NTP_ZOOM": "25 | int: new tab page zoom; 25=ic scroll mode >50=ic refresh mode",
                "IC_SCROLLS_PER_TRY": "3 | int: number of scroll triggers per ic try",
                "IC_TRIES_MULTIPLIER": "5 | int: multiply ic tries",
                "IC_MAX_TRIES_MULTIPLIER": "7 | int: multiply ic tries if found any",
                "IC_MIN_TRIES": "15 | int: minimum ic tries regardless the available",
                "IC_SCROLL_INTERVAL": "0.8 | seconds: interval between ic scroll inputs",
                "IC_MOUSE_AFTER_N_SCROLLS": "15 | int: load mouse movement after n ic scroll inputs",
                "MIN_UNBL_TOK_MSG_TO_FLAG": "2 | int: minimum 'You do not have enough unblinded tokens' messages to strike as flagged",
                "MIN_FLAGGED_STRIKES": "2 | int: minimum amount of strikes to consider fully flagged and not earn",
                "APPEND_PRE_FLAGGED": "1 | bool: include cfg.pre_flagged_devs on Manager.flagged",
                "FLAGGED_VISITS": "0 | int: amount of flagged devs visits; independent from SHOULD_VISIT/N_VISITS",
            }
            json_(self.fp_farmer_json, content, indent=0)

        # campaigns.json
        campaigns = Path(self.data_dir, 'campaigns.json')
        if not campaigns.exists():
            content = {'campaigns': []}
            json_(campaigns, content)

        # public_keys.json
        publickeys = Path(self.data_dir, 'public_keys.json')
        if publickeys.exists():
            content = []
            json_(publickeys, content)


    def _check_duplicate_devs(self):
        dupes = [dev for dev in self.all_devs if len( [1 for group in (self.devs, self.flagged_devs, self.claim_devs, self.frozen_devs) if dev in group] ) > 1]
        if not dupes:
            return
        print(
            f'[red]Found duplicate devs: [bright_cyan]{" ".join(dupes)}\n'
            '[red]Please check\nExiting...'
        )
        sys.exit(1)


    @check_dev
    def dirs(self, dev=None, folder='dev', *extras):
        dev_folder = self._devs_info.get(dev,{}).get('folder')

        lib = {
            'data':        self.data_dir,
            'temp':        self.temp_dir,
            'config':      self.config_dir,
            'dev':         dev_folder,
            'user_data':   Path(dev_folder, 'User Data'),
            'default':     Path(dev_folder, 'User Data', 'Default'),
            'ads_service': Path(dev_folder, 'User Data', 'Default', 'ads_service'),
        }

        path = Path(lib[folder], *extras).resolve()
        if not path.exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        return path


    @property
    def min_first_dev(self):
        return self._min_dev


    @property
    def max_last_dev(self):
        return self._max_dev


    @property
    def first_flagged(self):
        return self._first_flagged


    @property
    def number_of_devices(self):
        return len(self.devs)


    def is_possible_dev(self, dev):
        return self._min_dev <= int(dev) <= self._max_dev


    @check_dev
    def is_flagged(self, dev):
        return int(self.first_flagged) <= int(dev) <= int(self.max_last_dev)


    def parse_devs_code(self, devs_code: str):
        devs_code = "".join( [x.lower() for x in devs_code if x.isalpha() or x == '+'] )
        devs_code = [x.strip() for x in devs_code.split('+') if x.strip() in self._devs_groups]
        devs_code = list(set(devs_code))
        return devs_code


    def get_devs_group(self, devs_code, sort_devs=True):
        '''
        Returns devs groups by code: d, fl, cl, fr, all

        Can also concatenate groups with "+" eg.: <fl+cl>
        '''
        devs_code = self.parse_devs_code(devs_code)
        if 'all' in devs_code:
            return self._devs_groups['all']['devs']
        devs = [dev for code in devs_code for dev in self._devs_groups[code]['devs']]
        if sort_devs:
            devs.sort()
        return devs


    @check_dev
    def get_dev_group(self, dev):
        return self._devs_info.get(dev,{}).get('devs_code')


    def dev_color(self, dev):
        fallback_color = '[white]'

        dev = str(dev).strip()

        # by devs group code: d, fl, cl, fr, all
        if dev.isalpha():
            return self._devs_groups.get(dev, {}).get('color', fallback_color)

        # by actual dev number
        dev = Config.parse_dev(dev)
        return self._devs_info.get(dev,{}).get('color', fallback_color)


    @check_dev
    def fdev(self, dev):
        ''' Replace left zeroes by space '''
        return f'{int(dev):>3}'


    @check_dev
    def dev_index(self, dev):
        if dev is None:
            return None
        return self._devs_info.get(dev,{}).get('index') + 1


    @check_dev
    def format_dev(self, dev, fdev=True, pad=4, dev_index=True):
        dev_index = f'[bright_black]{self.dev_index(dev):2} ' if dev_index else ''
        color = self.dev_color(dev)
        dev = self.fdev(dev) if fdev else dev
        return f'{dev_index}{color}{dev:<{pad}}'


    @check_dev
    def print_dev(self, dev, fdev=True, pad=4, dev_index=True, end=''):
        ''' Formatted dev headers '''
        dev = self.format_dev(dev, fdev=fdev, pad=pad, dev_index=dev_index)
        print(dev, end=end)


    def _show_list_of_devs(self):
        for devs_code, data in self._devs_groups.items():
            if devs_code == 'all':
                continue
            name = data['name']
            color = data['color']
            devs = " ".join(data['devs'])
            print(f'\n{name} [bright_black]({len(data["devs"])}):\n{color}{devs}')


    def _show_devs_menu(self):
        print(
            '\n'
            'Inputs:\n'
            '-[bright_white]to select groups:\n'
            '    [white]<d>=devs\n'
            '    [white]<fl>=flagged_devs\n'
            '    [white]<cl>=claim_devs\n'
            '    [white]<fr>=frozen_devs\n'
            '    [white]<all>=all_devs\n'
            '    [white]or multiple using "+" eg.: <fl+cl>\n'
        )


    def _show_dev_menu(self):
        print(
            '-[bright_white]to select devs:\n'
            '-[bright_white]empty to open all available devs\n'
            '-[bright_white]for specific devs use comma or space:\n'
            '    [white]e.g.: <2,3,24> or <2 3 24> or <2,3 24>\n'
            '-[bright_white]for chunks of devs use dash:\n'
            '    [white]e.g.: <4-12> for 4 to 12>\n'
        )


    def parse_devs_input(self, string=None, validate=True):
        '''
        Convert a given string and output a list of dev numbers list from it
        If `validate`, works only with existing devs, otherwise use range 1-999 (why?)
        '''

        # no input -> display menu
        if string is None:
            self._show_list_of_devs()
            self._show_devs_menu()
            self._show_dev_menu()
            string = input()

        string = string.strip()
        letters = ''.join( [x for x in string if x.isalpha()] )
        numbers = ''.join( [x for x in string if x.isdigit()] )

        # choose devs group
        all_devs = self.get_devs_group(string) or self.all_devs

        # input has no numebrs
        if not numbers:
            return all_devs

        # input has numbers -> parse it
        all_devs.sort()
        if numbers:
            if '-' in string:
                string = ''.join( [x for x in string if x.isdigit() or x == '-'] )
                string = string.split('-')
                first, last = string[0], string[-1]
                first = first if first and first.isdigit() else (all_devs[0]  if validate else self.min_first_dev)
                last  = last  if last  and last.isdigit()  else (all_devs[-1] if validate else self.max_last_dev)
                first, last = int(first), int(last)
                if validate:
                    devs = [Config.parse_dev(x) for x in range(first, last+1) if Config.parse_dev(x)]
                else:
                    devs = [x for x in range(first, last+1)]
            else:
                string = string.replace(' ', ',')
                string = ''.join( [x for x in string if x.isdigit() or x == ','] )
                string = string.strip(',')
                string = string.split(',')
                string = [int(x.strip()) for x in string if x.strip() and x.strip().isdigit()]
                if validate:
                    devs = [Config.parse_dev(x) for x in string if Config.parse_dev(x)]
                else:
                    devs = [Config.parse_dev(x) for x in string if self.is_possible_dev(x)]

            devs = [x for x in devs if x in all_devs]
            devs = list(set(devs))
            devs.sort()
            return devs


    @check_dev
    def dev_all_info(self, dev, preferences=False, transactions=False, publisher_info_db=False):
        '''
        Parse several dev's information
        Informations are according to the required file to improve efficiency
        '''
        from .ads import ads

        a = SimpleNamespace()

        if preferences:
            from .json_preferences import Preferences
            pf = Preferences(dev, print_=False)
            timestamp = pf.get_next_time_redemption_at()
            a.wallet_id = pf.get_wallet_id()
            a.next_time_redemption_at = {
                'timestamp':  timestamp,
                'date':       str(timestamp_to_full_date(timestamp)),
                'eta':        max(timestamp - self.now, 0)
            }

        if transactions:
            from .json_transactions import Transactions
            tr = Transactions()
            confs_json = tr.confirmations_json(dev)
            a.failed_confirmations     = len(confs_json['confirmations']['failed_confirmations'])
            a.unblinded_payment_tokens = len(confs_json['unblinded_payment_tokens'])
            a.unblinded_tokens         = len(confs_json['unblinded_tokens'])

        if publisher_info_db:
            a.grants_ads = ads.parse_sql_publisher_info_db(dev)

        return a


    @check_dev
    def copy_secure_preferences(self, dev):
        '''
        DEPRECATED: high risk for a trivial task; rather use input commands
        WARNING: running this function for existing devs will result in crash and reset!
        For new devices only
        Copy Secure Preferences to configure "On startup" and "Show homepage button" on new devices
        '''
        # safe mechanism
        dev_folder = self.dirs(dev, 'default')
        creation_date = dev_folder.stat().st_ctime  # in timestamp
        folder_age = self.now - creation_date
        if folder_age > self.minute_in_sec:
            print(f"[bright_red]WARNING: device's folder is older than 1 minute: [/]{f_time(None, folder_age)}!"
                  "\n[bright_red]Skipping Secure Preference configuration")
            return
        secure_path = self.dirs(None, 'config', 'Secure Preferences')
        secure = json_(secure_path)
        dest_path = self.dirs(dev, 'default', 'Secure Preferences')
        json_(dest_path, secure, backup=True)


    @check_dev
    def configure_dev(self, dev, step):
        assert step in (1, 2, 'full')

        from .json_preferences import Preferences
        pf = Preferences(dev, print_=False)

        if step in (1, 'full'):
            self.copy_bookmarks(dev)
            pf.confirm_close_tabs(False)

        if step in (2, 'full'):
            pf.welcome_page(False)
            pf.ads_per_hour()
            pf.auto_contribute(False)
            pf.bookmarks_bar(True)
            pf.confirm_close_tabs(False)
            pf.cookies(True)
            pf.dismiss_wallpaper_notification(True)
            pf.exit_type_normal()
            pf.hangouts(False)
            pf.images(False)
            pf.javascript(False)
            pf.news(True)
            pf.shields_aggressive(True)
            pf.shields_stats_badge_visible(False)
            pf.social_media_blocking(False)
            pf.spellchecking(False)
            pf.translate(False)
            pf.wallet_icon(False)
            pf.webtorrent(False)
            pf.zoom_ntp_out(25)
            pf.ntp_background_color()

            from .json_local_state import LocalState
            ls = LocalState(dev, print_=False)
            ls.flags(True)
            ls.p3a(False)
            ls.done()

        pf.done()
        print(f'[bright_black]\[{func_name()}]step {step} done!')


    @timeit
    def create_dev(self, n_devs_to_create=None, auto=None):
        from .controls import ct

        def kill():
            ct.kill()
            sleep(0.5)

        def set_onstartup():
            from .controls import ct
            ct.open_page('brave://settings/getStarted')
            sleep(1)
            ct.click((927,515))
            ct.click((927,535))
            ct.click((927,545))
            ct.press('esc')

        def enable_rewards():
            ct.open_new_tab()
            sleep(1)
            ct.click('enable_rewards_100')
            sleep(2)
            ct.press('esc', n=2)
            sleep(1)
            sleep(1)
            ct.load_mouse_event(n=2)
            ct.click()
            ct.press(n=5)
            ct.open_page('brave://rewards')
            sleep(2)
            ct.press('f5', n=2)
            ct.close_tab()

        def trigger_unbl_tokens():
            from .json_transactions import Transactions
            tr = Transactions()
            ct.open_new_tab()
            for i in range(10):
                unbl_tokens = tr.len_unb_tokens(dev)
                if unbl_tokens:
                    break
                ct.press('pagedown', n=10)
                ct.click()
                ct.load_mouse_event(n=1)
                ct.press(n=5)
            print(f'[white]{unbl_tokens} unblinded tokens ({i+1})')
            ct.close_tab()

        # slots = [str(x).zfill(3) for x in range(int(self.min_first_dev), int(self.first_flagged)) if x not in self.devs]

        if auto is None:
            auto = bool(input('Input any key to auto mode\n>'))

        existing_devs = [int(dev) for dev in self.all_devs if int(dev) < 900]
        existing_devs.sort()
        last_existing_dev = existing_devs[-1] if existing_devs else 0
        slots = [str(x).zfill(3) for x in range(last_existing_dev+1, int(self.first_flagged)) if x not in self.devs]
        n_avail = len(slots)

        limit = 10 if self.number_of_devices > 60 else 60  # safety latch

        print(
            f'[white]\ndevs:{len(self.devs)} | flagged_devs:{len(self.flagged_devs)} | claim_devs:{len(self.claim_devs)} | frozen_devs:{len(self.frozen_devs)}\n'
            f'[bright_white]{n_avail} available slots:\n'
            f'[bright_white]slots: [bright_cyan ]{" ".join( [f"{str(x+1):^3}" for x in range(len(slots[:20])) ])} ...\n'
            f'[bright_white]devs:  [bright_black]{" ".join( [x for x in slots[:20]] )} ...'
        )

        n_devs_to_create = n_devs_to_create or int(input(f'\nInput how many slots to create (limit={limit})\n>').strip() or 1)
        n_devs_to_create = min(n_devs_to_create, n_avail, limit)
        devs = slots[:n_devs_to_create]

        self.close_brave()

        print(f'\nCreating {len(devs)} devs:\n[white]{" ".join(devs)}')
        for dev in devs:
            print(f'\n[bright_blue]{dev}')
            # register dev
            path = Path(self._devs_folder, dev, 'User Data')
            os.makedirs(path)
            self._core_devs()
            # create dev
            ct.run_brave(dev, maximized=True)
            sleep(2)
            ct.press('esc')
            sleep(2)
            # manual setup
            set_onstartup()
            sleep(1)
            if auto:
                enable_rewards()
                sleep(5)
            else:
                input('Enter to continue configuration...')
            kill()
            # auto setup step 1
            self.configure_dev(dev, step=1)
            sleep(0.5)
            ct.run_brave(dev, maximized=True)
            sleep(3)
            kill()
            # auto setup step 2
            self.configure_dev(dev, step=2)
            sleep(0.5)
            ct.run_brave(dev, maximized=True)
            sleep(3)
            # trigger unbl tokens to check if it's earning/not insta flagged
            # trigger_unbl_tokens()
            kill()
            # recheck auto setup step 2
            self.configure_dev(dev, step=2)

        self.all_update_wallet_ids()
        print('[bright_green]Done!')


    def sweep(self, func, header=None, print_=True):
        '''
        Access all devs and feed them as parameter to parsed function.
        '''
        if header:
            print(header) if print_ else ...
        for dev in self.all_devs:
            print(f'{dev}', end=' ') if print_ else ...
            x = func(dev=dev)
            if x is not None:
                print('[white]', x) if print_ else ...
            else:
                print() if print_ else ...


    def is_brave_running(self, wait=0):
        sleep(wait)
        return 'brave.exe' in get_running_processes()


    # @timeit
    def close_brave(self, print_=True):

        if not cfg.is_brave_running(0):
            return

        if print_:
            print('\n[bright_black]Closing all open Brave applications...\n')

        run('powershell -command "Get-Process brave | ForEach-Object { $_.CloseMainWindow() | Out-Null}"')

        if not cfg.is_brave_running(0.1):
            return

        run('taskkill /im brave.exe')  # gentle no child

        if not cfg.is_brave_running(0.1):
            return

        for _ in range(5):
            run('taskkill /im brave* /t')  # gentle with child
            if not cfg.is_brave_running(0.1):
                return

        run('taskkill /f /im brave* /t')  # forced full


    @timeit
    def backup(self, devs_code=None):
        from .controls import ct
        import subprocess

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'all'
            os.system('cls')
        devs = cfg.get_devs_group(devs_code) or cfg.all_devs


        self.get_backups_folder()

        assert self.backup_folder and self.backup_folder.is_dir()

        self.close_brave()

        folders_to_exclude = [
            "BrowserMetrics",
            "BraveWallet",
            "BrowserMetrics-spare.pma",
            "Cache",
            "Code Cache",
            "Crashpad",
            "CrashpadMetrics-active.pma",
            "Extension State",
            "Greaselion",
            "GrShaderCache",
            "GPUCache",
            "hyphen-data",
            "IndexedDB",
            "OnDeviceHeadSuggestModel",
            "Safe Browsing",
            "Service Worker",
            "ShaderCache",
            "Temp",
            "aoojcmojmmcbpfgoecoadbdpnagfchel",  # Brave NTP background images component
            "cffkpbalmllkdoenhmdmpbkajipdjfam",  # Brave Ad Block Updater extension
            "oemmndcbldboiebfnladdacbdfmadadm",  # pdfHandler.html
            "oofiananboodjbbmdelgdommihjbkfag",  # Brave HTTPS Everywhere Updater extension
            "afalakplffnnnlkncjhbmahjfjhmlkal",  # Brave Local Data Files Updater extension
            "ocilmpijebaopmdifcomolmpigakocmo",  # Brave Ads Resources Component
            "fimpfhgllgkaekhbpkakjchdogecjflf",  # Brave Ads Resources Component
        ]
        folders_to_exclude = ' '.join([f'-xr!"{item}"' for item in folders_to_exclude])

        # TODO perform a routine to check if 7z is installed and on PATH

        for dev in devs:

            self.close_brave()
            src_path = self.dirs(dev, folder='dev')

            if src_path.is_dir():
                self.print_dev(dev)

                zip_name = f'{dev}.zip'
                zip_path = Path(self.backup_folder, zip_name)

                previous_zip_name = f'{dev}.previous.zip'
                previous_zip_path = Path(self.backup_folder, previous_zip_name)

                print(f'[white]{src_path} -> {zip_path}')

                if zip_name in os.listdir(self.backup_folder):
                    if previous_zip_name in os.listdir(self.backup_folder):
                        os.remove(previous_zip_path)
                    os.rename(zip_path, previous_zip_path)

                # subprocess.run(f'7z a -tzip "{zip_path}" "{src_path}" {folders_to_exclude}')
                run(f'7z a -tzip "{zip_path}" "{src_path}" {folders_to_exclude}', silent=True)

        print('[bright_green]Done!')


    def get_backups_folder(self):
        backup_folder = self.config_json['backups']['folder']
        if not backup_folder:
            print('[yellow]No backup directory\nCheck config.json file.')
            return
        backup_folder = Path(backup_folder).resolve()
        if not backup_folder.is_dir:
            print(f'[yellow]Invalid backup directory: {backup_folder}\nCheck config.json file.')
            return
        self.backup_folder = backup_folder


    def check_backup(self):
        ''' UNFINISHED '''
        today = str(self.today)
        routines = self.config_json['backups']['routines']
        if not routines.get(today):
            # self.backup()
            ...


    def all_update_wallet_ids(self):
        '''
        Get wallet payment id for all devices
        and save them in wallet.json.
        '''
        from .json_preferences import Preferences
        path = Path(self.config_dir, 'wallets.json')
        wallets = json_(path)
        for dev in self.devs:
            pf = Preferences(dev)
            ids = pf.get_wallet_id()
            wallets.setdefault(dev,{})
            wallets[dev] = ids
        json_(path, wallets, backup=True, n_backups=20, indent='\t')


# BROWSER TWEAKS
    @check_dev
    def copy_bookmarks(self, dev, from_file=False):
        '''
        Copy default Bookmarks to dev
        Using bookmarks is the most practical way of visually identify a dev
        '''
        def item_dict(name, url):
            return {
                "date_added": "13303354175469314",
                "guid":       "712264ad-88b4-4363-9b5c-5935ce20aaaa",
                "id":         "204",
                "name":       name,
                "type":       "url",
                "url":        url
            }

        # deprecated
        if from_file:
            src_path = Path(self.config_dir, 'Bookmarks')
            if not src_path.is_file():
                sys.exit(f'Invalid default Bookmarks path: {src_path}')
            bookmarks = json_(src_path)

        else:
            bookmarks = {
                "checksum": "",
                "roots": {
                    "bookmark_bar": {
                        "children": [ {
                            "date_added": "13293992698000000",
                            "guid": "6d55ca39-1977-4b38-bdcf-19fc3c63a7a9",
                            "id": "1",
                            "name": "Internals",
                            "type": "url",
                            "url": "chrome://rewards-internals/"
                        }, {
                            "date_added": "13303073329670381",
                            "guid": "e1cfe8f6-f875-4de4-b46f-f9c3565cab47",
                            "id": "2",
                            "name": "Version",
                            "type": "url",
                            "url": "chrome://version/"
                        }, {
                            "date_added": "13293992704000000",
                            "guid": "39cf910f-9731-430f-b72c-ff14dbb2d877",
                            "id": "3",
                            "name": "Catalog",
                            "type": "url",
                            "url": "https://sampson.codes/brave/ads/my_region/"
                        }, {
                            "date_added": "13294101741000000",
                            "guid": "1c094d8f-5345-4365-9690-f91e042326be",
                            "id": "4",
                            "name": "",
                            "type": "url",
                            "url": "https://ethereum.org/en/"
                        }, {
                            "date_added": "13292510736000000",
                            "guid": "de90a268-b996-4434-856c-dffe07ebd983",
                            "id": "5",
                            "name": "",
                            "type": "url",
                            "url": "https://1inch.io/"
                        }, {
                            "date_added": "13292526569000000",
                            "guid": "417683d3-dd62-4390-8551-2babc7a5fe62",
                            "id": "6",
                            "name": "",
                            "type": "url",
                            "url": "https://nft.bigtime.gg/"
                        }, {
                            "date_added": "13292994229000000",
                            "guid": "31422a4a-cd32-402c-a567-c5d13df2100f",
                            "id": "7",
                            "name": "",
                            "type": "url",
                            "url": "https://www.aax.com/en-US/"
                        } ],
                        "date_added": "13290626935595997",
                        "date_modified": "13303354177857605",
                        "guid": "0bc5d13f-2cba-5d74-951f-3f233fe6c908",
                        "id": "1",
                        "name": "Bookmarks",
                        "type": "folder"
                    },
                    "other": {
                        "children": [  ],
                        "date_added": "13290626935595999",
                        "date_modified": "0",
                        "guid": "82b081ec-3dd3-529c-8475-ab6c344590dd",
                        "id": "2",
                        "name": "Other bookmarks",
                        "type": "folder"
                    },
                    "synced": {
                        "children": [  ],
                        "date_added": "13290626935596000",
                        "date_modified": "0",
                        "guid": "4cf2e351-0e85-532b-bb37-df045d8f8d0f",
                        "id": "3",
                        "name": "Mobile bookmarks",
                        "type": "folder"
                    }
                },
                "version": 1
            }

        dst_path = self.dirs(dev, 'default')
        dst_path = Path(dst_path, 'Bookmarks')
        children = bookmarks['roots']['bookmark_bar']['children']

        # add creators links
        for url in self.config_json['creators']:
            item = item_dict("", url)
            children.insert(2, item)

        # add dev id
        dev_id = item_dict(dev, 'about:blank')
        children.insert(0, dev_id)

        saved = json_(dst_path, bookmarks, backup=True, indent='\t')
        if saved:
            print(f'[bright_black]\[{func_name()}]Added bookmarks on {dev}')


    def all_copy_bookmarks(self):
        '''
        Copy default Bookmarks to all devs
        '''
        self.sweep(self.copy_bookmarks)


    @check_dev
    def replace_ntp_images(self, dev=None):
        '''
        Replace each "Brave NTP background images"
        for very light files to lighten new tab refreshs
        '''
        devs = [dev] if dev else self.devs
        black_img_path = Path(self.config_dir, 'black.webp')
        black_img_size = black_img_path.stat().st_size
        if not black_img_path.is_file():
            sys.exit(f'Invalid base image path: {black_img_path}')
        count = 0
        for dev in devs:
            ntp_root_folder = self.dirs(dev, 'user_data', 'aoojcmojmmcbpfgoecoadbdpnagfchel')
            for ntp_folder in [x for x in ntp_root_folder.iterdir() if x.is_dir()]:
                webps = [x for x in ntp_folder.iterdir() if x.is_file() and x.name.endswith('.webp') and x.stat().st_size != black_img_size]
                for file in webps:
                    file_path = Path(ntp_folder, file)
                    shutil.copy(black_img_path, file_path)
                    count += 1
        print(f'[bright_black]\[{func_name()}]{count} images replaced')


    def write_id_in_excpt(self, mode, ids):
        assert mode in ('advtids', 'csids'), f'Invalid mode: {mode}'
        assert isinstance(ids, list), f'Invalid ids format: {type(ids)} {ids}'
        target = f'bad_{mode}'
        ids = list(set(ids))
        ids = [x for x in ids if x and is_valid_uuid(x)]
        excpt_path = self.dirs(folder='excpt')
        excpt = json_(excpt_path)
        excpt[target] = ids
        edited = json_(excpt_path, excpt, backup=True)
        return edited


    @check_dev
    def _ban_advertiser(self, dev, advt_to_ban):
        '''
        DEPRECATED: overkill since an advertiser may have multiple campaigns, using csid instead
        Write advertiser id to `client.json > adPreferences > filtered_advertisers`.
        Not to be used directly unless you can fully validate `bad_advtids`.
        '''
        path_client = self.dirs(dev, 'ads_service', 'client.json')
        data = json_(path_client)
        filtered_advertisers = sorted(data['adPreferences']['filtered_advertisers'], key=lambda x: x['id'])
        advt_to_ban.sort(key=lambda x: x['id'])
        if filtered_advertisers == advt_to_ban:
            return False
        data['adPreferences']['filtered_advertisers'] = advt_to_ban
        edited = json_(path_client, data, backup=True)
        return edited


    @timeit
    def all_ban_advertiser(self, mode):
        '''
        DEPRECATED: overkill since an advertiser may have multiple campaigns, using csid instead
        Get advertiser ids to ignore found on `excpt.json`
        and write/remove it on all `client.json` files.
        Initially built to avoid low ptr Ads.
        '''
        assert mode in ('add', 'clean')

        self.close_brave()

        if mode == 'add':
            excpt = json_(self.fp_excpt_json)
            advt_to_ban = excpt['bad_advtids']
            advt_to_ban = list(set(advt_to_ban))
            advt_to_ban.sort()
            advt_to_ban = [{'id': x} for x in advt_to_ban if x and is_valid_uuid(x)]
            print(f'[white]Adding advertiser filters: {advt_to_ban}')

        elif mode == 'clean':
            advt_to_ban = []
            print('[white]Cleaning advertiser filters')

        all_edited = 0
        for dev in self.devs:
            edited = self._ban_advertiser(dev, advt_to_ban)
            if edited is True:
                all_edited += 1

        print(f'[bright_black]\[{func_name()}]{all_edited} client.json edited')


    @check_dev
    def _ban_csid(self, dev, csid_to_ban):
        '''
        Write low ptr campaign's creative set ids to `client.json > adPreferences > flagged_ads`.
        Not to be used directly unless you can fully uuid validate `csid_to_ignore`.
        '''
        path_client = self.dirs(dev, 'ads_service', 'client.json')
        data = json_(path_client)
        flagged_ads = sorted(data['adPreferences']['flagged_ads'], key=lambda x: x['creative_set_id'])
        csid_to_ban.sort(key=lambda x: x['creative_set_id'])
        if flagged_ads == csid_to_ban:
            return False
        data['adPreferences']['flagged_ads'] = csid_to_ban
        edited = json_(path_client, data, backup=True)
        return edited


    @timeit
    def all_ban_csid(self, devs, mode):
        '''
        Get creative set ids to ignore found on `excpt.json`
        and write/remove it on all devs `client.json` files.
        Initially built to avoid low ptr Ads.
        Accurate, no overkill, better than ban_advertiser
        '''
        assert mode in ('add', 'clean')

        self.close_brave()

        if mode == 'add':
            excpt = json_(self.fp_excpt_json)
            csids = excpt['bad_csids']
            csids = list(set(csids))
            csids.sort()
            csids = [x for x in csids if x and is_valid_uuid(x)]
            print(f'[bright_black]\[all_ban_csid]Banning {len(csids)} csids: {" ".join( [x[:8] for x in csids] )}')
            csids = [{'creative_set_id': x} for x in csids]

        elif mode == 'clean':
            csids = []
            print('[bright_black]\[all_ban_csid]Cleaning csid filters')

        all_edited = 0
        for dev in devs:
            edited = self._ban_csid(dev, csids)
            if edited is True:
                all_edited += 1

        print(f'[bright_black]\[{func_name()}]{all_edited} client.json edited')


    @check_dev
    def _clean_client_ads_history(self, dev, max_size=10):
        '''
        Reduce client.json's adsShownHistory.
        Benefits:
          -prevent corruption between versions while downgrading: `n_items_to_remain` must be zero
          -speed up client.json reading process since we use it a lot: `n_items_to_remain` ideally 1
        no sign of flagging due to client.json manipulation so far
        '''
        path_client = self.dirs(dev, 'ads_service', 'client.json')
        client = json_(path_client)
        if len(client['adsShownHistory']) <= max_size:
            return False
        client['adsShownHistory'] = client['adsShownHistory'][:max_size]
        edited = json_(path_client, client, backup=True)
        return edited


    @timeit
    def all_clean_client_ads_history(self, devs, max_size=10):
        ''' Remove all dev's client.json adsShownHistory '''
        self.close_brave()

        all_edited = 0
        for dev in devs:
            edited = self._clean_client_ads_history(dev, max_size=max_size)
            if edited is True:
                all_edited += 1
        print(f'[bright_black]\[{func_name()}]{all_edited} client.json edited')


    def clean_cache(self):
        from .json_preferences import Preferences
        from .controls import ct

        # devs = self.frozen_devs + self.claim_devs + self.flagged_devs
        devs = self.all_devs

        for dev in devs:
            with Preferences(dev) as pf:
                pf.clear_cache_on_exit(True)

        for dev in devs:
            ct.run_brave(dev)
            sleep(3)
            ct.kill()


    @timeit
    def all_clean_cache(self):
        return


    def reset_redemption_time(self, devs_code:str = None):
        from .json_preferences import Preferences
        if devs_code is None:
            self._show_devs_menu()
            devs_code = input('>')

        devs = self.get_devs_group(devs_code)
        for dev in devs:
            with Preferences(dev) as pf:
                pf.check_next_time_redemption_at()


cfg = Config()
