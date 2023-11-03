import calendar
import datetime
import famgz_utils
import os
import sys
import traceback
from copy import deepcopy
from famgz_utils import (
    input,
    rule,
    disable_print,
    LogPrint,
    f_time,
    load_mouse_event,
    get_local_date_time,
    timeit,
    hour,
    min_duration,
    countdown,
    func_name,
    clear_last_console_line
)
from itertools import chain
from pathlib import Path
from os.path import join as pj
from random import choice
from time import sleep, time
from timeit import default_timer as timer

from .ads import ads
from .config import cfg
from .controls import ct
from .json_local_state import LocalState
from .json_preferences import Preferences
from .json_transactions import Transactions
from .rewards_log import ReLog
from .segments import Segments

# PRINT SETUP
# makes every print a logger
# TODO needs a better implementation
log_path = Path(cfg.logs_dir, 'farmer')
print = LogPrint(log_path, dated=True).print
import brave_ads
brave_ads.config.print = \
brave_ads.ads.print = \
brave_ads.json_preferences.print = \
brave_ads.json_local_state.print = \
brave_ads.segments.print = \
brave_ads.rewards_log.print = \
brave_ads.json_transactions.print = \
brave_ads.controls.print = \
famgz_utils.config.print = print


def _parse_farmer_json():
    farmer = cfg.farmer_json
    return {param:data.split('|')[0].strip() for param, data in farmer.items()}


def choose_devs():
    global DEVS_TYPE, DEVS_CODE, DEVS, FIRST_DEV, LAST_DEV

    DEVS_CODE = cfg.parse_devs_code(DEVS_TYPE)

    DEVS = cfg.get_devs_group(DEVS_TYPE)

    # in case proper input being mandatory...
    if DEVS is None:
        print(
            '\n\n'
            f'[yellow]Invalid devs_type input:[/] <{DEVS_TYPE}>\n\n'
            'Edit farmer.json > DEVS_TYPE\n\n'
            f'Available options: <{" ".join(cfg._devs_groups)}>\n\n'
            'Exiting...\n'
        )
        sys.exit(1)

    DEVS = DEVS or cfg.devs or cfg.all_devs

    if not DEVS:
        print(
            '\n\n'
            '[yellow]No devs found:\n'
            'Exiting...\n'
        )
        cfg.show_list_of_devs()
        sys.exit(1)

    FIRST_DEV = FIRST_DEV or DEVS[0]
    LAST_DEV  = LAST_DEV  or DEVS[-1]

    FROM_DEV, TO_DEV = DEVS.index(FIRST_DEV), DEVS.index(LAST_DEV)
    DEVS = DEVS[ FROM_DEV : TO_DEV+1 : ]


params = _parse_farmer_json()

EARN                       = bool(int(params["EARN"]))
DEVS_TYPE                  = str(params["DEVS_TYPE"])
FIRST_DEV                  = cfg.parse_dev(params["FIRST_DEV"])
LAST_DEV                   = cfg.parse_dev(params["LAST_DEV"])
PERIOD_FULLDAY             = [int(x) for x in params["PERIOD_FULLDAY"].split(',') if x.isdigit()]
PERIOD_CATALOG             = [int(x) for x in params["PERIOD_CATALOG"].split(',') if x.isdigit()]
PERIOD_LONG_PN             = [int(x) for x in params["PERIOD_LONG_PN"].split(',') if x.isdigit()]
PERIOD_ALLOWNT             = [int(x) for x in params["PERIOD_ALLOWNT"].split(',') if x.isdigit()]
REFILL_UNB_TOK             = bool(int(params["REFILL_UNB_TOK"]))
SEGMENTS_DEBUG             = bool(int(params["SEGMENTS_DEBUG"]))
FILTER_URLS                = bool(int(params["FILTER_URLS"]))
MAX_CLIENT_HISTORY_SIZE    = int(params["MAX_CLIENT_HISTORY_SIZE"])
N_DEVS_TO_ESCAPE_LOW_PTR   = int(params["N_DEVS_TO_ESCAPE_LOW_PTR"])
IDLE                       = bool(int(params["IDLE"]))
IDLE_VISIT                 = bool(int(params["IDLE_VISIT"]))
IDLE_RECONCILE             = bool(int(params["IDLE_RECONCILE"]))
IDLE_STAND_BY_DURATION     = float(params["IDLE_STAND_BY_DURATION"])  # minutes
IDLE_N_VISITS              = int(params["IDLE_N_VISITS"])
RECONCILE_N_MEAN_SLOTS     = 12
RECONCILE_DUR_PER_ROUND    = float(params["RECONCILE_DUR_PER_ROUND"])  # minutes
RECONCILE_DUR_PER_DEV      = float(params["RECONCILE_DUR_PER_DEV"])  # minutes
RECONCILE_DUR_PER_CONF     = float(params["RECONCILE_DUR_PER_CONF"])  # minutes
RECONCILE_MIN_DURATION     = float(params["RECONCILE_MIN_DURATION"])  # minutes
RECONCILE_OPEN_REWARDS     = bool(int(params["RECONCILE_OPEN_REWARDS"]))
PN_ONE_PAGE_PER_TRY        = bool(int(params["PN_ONE_PAGE_PER_TRY"]))
PN_TRIES_AFTER_IC          = int(params["PN_TRIES_AFTER_IC"])
PN_TRIES_LONG              = int(params["PN_TRIES_LONG"])
PN_TRIGGERS_PER_TRY_LONG   = int(params["PN_TRIGGERS_PER_TRY_LONG"])
PN_TRIES_SHORT             = int(params["PN_TRIES_SHORT"])
PN_TRIGGERS_PER_TRY_SHORT  = int(params["PN_TRIGGERS_PER_TRY_SHORT"])
PN_RETRY_BY_RELAUNCH       = bool(params["PN_RETRY_BY_RELAUNCH"])
NT_BY_RELAUNCH             = bool(int(params["NT_BY_RELAUNCH"]))
NT_BY_SWITCH_TAB           = bool(int(params["NT_BY_SWITCH_TAB"]))
NT_MIN_N_TO_TRIGGER        = int(params["NT_MIN_N_TO_TRIGGER"])
NTP_ZOOM                   = int(params["NTP_ZOOM"])
IC_SCROLLS_PER_TRY         = int(params["IC_SCROLLS_PER_TRY"])
IC_TRIES_MULTIPLIER        = int(params["IC_TRIES_MULTIPLIER"])
IC_MAX_TRIES_MULTIPLIER    = int(params["IC_MAX_TRIES_MULTIPLIER"])
IC_MIN_TRIES               = int(params["IC_MIN_TRIES"])
IC_SCROLL_INTERVAL         = float(params["IC_SCROLL_INTERVAL"])  # seconds
IC_MOUSE_AFTER_N_SCROLLS   = int(params["IC_MOUSE_AFTER_N_SCROLLS"])
MIN_UNBL_TOK_MSG_TO_FLAG   = int(params["MIN_UNBL_TOK_MSG_TO_FLAG"])
MIN_FLAGGED_STRIKES        = int(params["MIN_FLAGGED_STRIKES"])
APPEND_PRE_FLAGGED         = bool(int(params["APPEND_PRE_FLAGGED"]))
FLAGGED_VISITS             = int(params["FLAGGED_VISITS"])

choose_devs()


def refresh_pn_params():
    global PN_TRIES, PN_TRIGGERS_PER_TRY
    if not m.ptr_filter and hour() in PERIOD_CATALOG:
        PN_TRIES, PN_TRIGGERS_PER_TRY = (3, 3)
        return
    PN_TRIES, PN_TRIGGERS_PER_TRY = (PN_TRIES_LONG,PN_TRIGGERS_PER_TRY_LONG) if hour() in PERIOD_LONG_PN else (PN_TRIES_SHORT,PN_TRIGGERS_PER_TRY_SHORT)


def entry_conditions(ac):
    return (ac.pn > 0, ac.nt > 0, ac.ic > 0)


def manual_tweaks(dev, ac):
    '''
    Forced tests/adjustments
    '''
    # ac.pn = ac.pn_ini = 1
    # ac.nt = ac.nt_ini = 1
    # ac.ic = ac.ic_ini = 1
    # ac.pn = ac.pn_ini = ac.nt = ac.nt_ini = ac.ic = ac.ic_ini = 0
    # if dev in ['001']:
    #      ac.ic = ac.ic_ini = ac.nt = ac.nt_ini = 0
    return


def filters(dev, ac):
    if not m.earn:
        ac.pn = ac.pn_ini = ac.nt = ac.nt_ini = ac.ic = ac.ic_ini = 0
        return
    manual_tweaks(dev, ac)
    # allow nt
    if hour() not in PERIOD_ALLOWNT:
        ac.nt = ac.nt_ini = 0
        ...
    # isolate nt
    if ac.nt >= NT_MIN_N_TO_TRIGGER:
        ac.pn = ac.pn_ini = ac.ic = ac.ic_ini = 0
        ac.nt = ac.nt_ini = min(ac.nt, 100)
    else:
        ac.nt = ac.nt_ini = 0


class Manager:
    '''
    Global manager.
    Persist through whole run.
    '''
    def __init__(self):
        self.devs_type = self.format_devs_type()
        self.idle = bool(IDLE)
        self.earn = bool(EARN)
        self.t1_global = time()
        self.reconcile = bool(IDLE_RECONCILE)
        self.devs_to_reconcile = None
        self.reconcile_last = None
        self.is_failed_redeem_mode = None
        self.devs_to_visit = None
        self.cat_headers = {'all': None, 'net': None}
        self.first_dev_to_farm = DEVS[0]
        self.last_banned_csids = None
        self.ptr_filter = None
        self.tr = Transactions(devs=DEVS)
        self.last_checked_unb_tok = None
        self.total_cycles = 0
        self.active_cycles = 0
        self.earned_devices = 0
        self.min_earned_devices = 2
        self.active_devices = 0
        self.all_pn_count = 0
        self.all_nt_count = 0
        self.all_ic_count = 0
        self.no_ad_cycles = {'pn': 0, 'nt': 0, 'ic': 0}
        self.got_pn = False
        self.pn_from_ic = False
        self.flagged = []
        if APPEND_PRE_FLAGGED:
            self.flagged.extend(cfg.flagged_devs)
        self.blank_space = " "*100

    def format_devs_type(self):
        return " ".join( [f'{cfg.dev_color(code)}{cfg._devs_groups[code]["name"]}[white]({len(cfg._devs_groups[code]["devs"])})' for code in DEVS_CODE] )

    @timeit
    def config_devices(self):
        for dev in DEVS:
            with Preferences(dev, print_=False) as pf:
                pf.restore_browser_window()
                pf.ntp_background_color()
                pf.clear_cache_on_exit(True)
                pf.confirm_close_tabs(False)
                pf.images(False)
                pf.javascript(False)
                pf.cookies(True)
                pf.zoom_ntp_out(NTP_ZOOM)
                pf.exit_type_normal()
                pf.dismiss_wallpaper_notification(True)
            continue
            # single run enable flags
            with LocalState(dev, print_=False) as ls:
                ls.flags(True)

    def prevent_restore_box_after_crash(self):
        for dev in DEVS:
            with Preferences(dev, print_=False) as pf:
                pf.exit_type_normal()

    def check_earn(self):
        if self.earn:
            return
        if hour() in PERIOD_CATALOG:
            self.earn = True

    def check_idle(self):
        self.check_earn()
        if not self.earn:
            self.idle = True
            print()
            return
        self.check_idle_by_any_availability()

    def check_idle_by_any_availability(self):
        self.idle = not self.find_any_available_ads()

    def find_any_available_ads(self):
        self.first_dev_to_farm = DEVS[0]
        print('[white]checking ads:', end=' ')
        for dev in DEVS:
            if self.tr.len_unb_tokens(dev) < 10:
                continue
            ac = AdsCount(dev, only_first_references=True)
            self.apply_forced(ac)
            filters(dev, ac)
            if ac.pn or ac.ic or ac.nt:
                self.first_dev_to_farm = dev
                print(f'[white]{dev} > found ads, farm...')
                return True
        print(f'[white]{dev} > no ads found')
        return False

    def check_idle_by_all_availability(self):
        avail = self.find_all_available_ads()
        conditions = (
            avail['pn'] > 0,
            avail['nt'] > 0,
            avail['ic'] > 0,
        )
        self.idle = not any(conditions)

    def find_all_available_ads(self):
        avail = {'pn': 0, 'nt': 0, 'ic': 0}
        for dev in DEVS:
            if dev in self.flagged:
                continue
            ac = AdsCount(dev, only_first_references=True)
            self.apply_forced(ac)
            filters(dev, ac)
            avail['pn'] += ac.pn
            avail['nt'] += ac.nt
            avail['ic'] += ac.ic
        return avail

    def has_enough_unb_tok(self, dev):
        return m.tr.len_unb_tokens(dev) > 9

    def check_and_run_unb_tok(self):
        ''' Check and run low unblinded token devs once an hour '''
        if not REFILL_UNB_TOK:
            return
        if self.last_checked_unb_tok is None:
            # first check in 15 min
            # self.last_checked_unb_tok = cfg.now - cfg.minute_in_sec*45
            # return
            ...
        elif cfg.now - self.last_checked_unb_tok < cfg.hour_in_sec:
            return
        print(DEVS_TYPE)
        ads.run_low_unb_tokens_devs(devs_code=DEVS_TYPE, persists=False)
        self.last_checked_unb_tok = cfg.now

    def get_n_ideal_slots(self, total_n_devs, goal):
        '''
        Returns the ideal n_devs group size
        based on RECONCILE_N_SLOTS
        '''
        def split_eq(total, n_parts):
            d,r = divmod(total, n_parts)
            return [d+1]*r + [d]*(n_parts-r)
        floor = goal-2
        ceil  = goal+2
        if total_n_devs <= ceil:
            return total_n_devs
        if ceil+1 <= total_n_devs <= ceil+4:
            import math
            return math.ceil(total_n_devs/2)
        tolerance = range(floor, ceil+1)
        for i in range(1,50):
            groups = split_eq(total_n_devs, i)
            # print(f'[bright_black]{groups}')
            max_ = max(groups)
            if max_ in tolerance:
                return max_

    def get_devs_to_reconcile(self, force_redemption=False):
        # force_redemption=True
        devs_ini = self.tr.manage_failed_confs(print_=False, filter_click=False, filter_trash=False, sort_failed=False)
        if force_redemption:
            devs = []
        else:
            devs = [(dev, failed, unb_pay_tokens) for dev, failed, unb_pay_tokens in devs_ini if failed and dev in DEVS]

        # redeem failed confirmations mode
        if devs:
            self.is_failed_redeem_mode = True
            devs.sort(key=lambda x: x[1], reverse=True)  # sorting by `failed_confirmations`
        # redeem unblinded payment tokens mode
        else:
            self.is_failed_redeem_mode = False
            redeems = ads.show_next_redemption(devs=DEVS, sort_by_time=True, print_=False)
            devs = [(dev, failed, unb_pay_tokens, diff) for dev, failed, unb_pay_tokens, time_, diff, unbtok in redeems if unb_pay_tokens and diff < 60]
            if devs:
                print(f'{len(devs)} [white]devices ready to redeem payment tokens')
        # update scheduler
        if devs:
            if self.reconcile_last is not None:
                t2 = timer() - self.reconcile_last
                print(f'[bright_black]reconcile elapsed: {f_time(None, t2)}')
            self.reconcile_last = timer()

        print(f'[white]failed redeem mode: {self.is_failed_redeem_mode}')
        return devs

    def update_devs_to_reconcile(self, force_redemption=True):
        # if self.devs_to_reconcile is None:
            # self.tr.find_cancer(full=True)
        if not self.devs_to_reconcile:
            self.devs_to_reconcile = self.get_devs_to_reconcile(force_redemption=force_redemption)
            self.reconcile_n_slots = self.get_n_ideal_slots(len(self.devs_to_reconcile), RECONCILE_N_MEAN_SLOTS)

    def update_devs_to_visit(self):
        if self.devs_to_visit:
            return
        self.devs_to_visit = deepcopy(DEVS)

    def point_cat(self):
        ads.cat = ads.cat_net if self.ptr_filter else ads.cat_all

    def update_catalog(self, forced=False):
        was_updated = ads.update_catalog(from_file=False, file='campaigns', forced=forced)
        self.point_cat()  # whether to point ads.cat to all or net
        if not was_updated:
            return
        new_headers = self.get_catalog_headers()
        if forced and self.cat_headers == new_headers:
            return
        self.cat_headers = new_headers
        self.print_catalog()

    def get_catalog_headers(self):
        headers = {}
        for name, cat in (('all', ads.cat_all), ('net', ads.cat_net)):
            headers[name] = \
                f'[white]{ads.h_color(cat.pn_day)}pn={cat.pn_day:<2} {cat.pn_value:.2f} '\
                f'{ads.h_color(cat.nt_day)}nt={cat.nt_day:<2} {cat.nt_value:.2f} '\
                f'{ads.h_color(cat.ic_day)}ic={cat.ic_day:<2} {cat.ic_value:.2f}'\
                f'[white]|ptr pn={cat.pn_min_ptr} ic={cat.ic_min_ptr}'
        if headers['all'] == headers['net']:
            del headers['net']
        return headers

    def print_catalog(self):
        for name, cat in self.cat_headers.items():
            print(f"[white]{name}: {cat}")
        self.print_excpt()

    def print_excpt(self):
        print(
            f'[white]filter ptr: [{"bright_green" if self.ptr_filter else "bright_red"}]{self.ptr_filter}'
            f'[white] | excpt: min_ptr={cfg.excpt_json["min_values"]["ptr"]} csid={len(cfg.excpt_json["bad_csids"])} advtid={len( [x for x in cfg.excpt_json["bad_advtids"] if x] )}'
        )

    def print_clock(self, rule_=True):
        if not rule_:
            print(get_local_date_time())
            return
        print()
        rule(get_local_date_time(), characters='_', align='left', style='white')
        print()

    def print_bypass(self):
        if not (self.no_ad_cycles["pn"] or self.no_ad_cycles["nt"] or self.no_ad_cycles["ic"]):
            return
        print(f'[white]remaining_bypass_cycles: pn={self.no_ad_cycles["pn"]} nt={self.no_ad_cycles["nt"]} ic={self.no_ad_cycles["ic"]}')

    def print_pn_stats(self):
        print(f'{"":3}[white]pn: tries={PN_TRIES} triggers_per_try={PN_TRIGGERS_PER_TRY} tries_after_ic={PN_TRIES_AFTER_IC}')

    def print_ad_stats(self):
        print(
            f'[white]{" ":8}{"promises":^12}  {"earned":^12}\n'
            f'{" ":8}[white]{"pn":>4}{"nt":>4}{"ic":>4}   {"pn":>4}{"nt":>4}{"ic":>4}\n'
            f'{" ":23}{ads.h_color(self.all_pn_count, True)}{self.all_pn_count:>4}{ads.h_color(self.all_nt_count, True)}'
            f'{self.all_nt_count:>4}{ads.h_color(self.all_ic_count, True)}{self.all_ic_count:>4}'
        )

    def print_general_stats(self):
        print(f'[white]total_duration={f_time(self.t1_global)}  active_cycles={self.active_cycles}/{self.total_cycles}  idle={str(self.idle)}')

    def print_header(self):
        self.print_clock(rule_=False)
        print(f'[bright_white]farmer -> {self.devs_type}')
        self.print_excpt()
        self.print_general_stats()
        self.print_bypass()
        self.print_pn_stats()
        self.print_ad_stats()

    def input_forced(self):
        message = '[white]\nInput how many cycles ignoring ads\nin type order: `pn nt ic`\neg.:\n  <202> ignores `pn` and `ic` for 2 cycles\n  <3> ignores `pn` for 3 cycles\n  <009> ignores `ic` for 9 cycles\n  empty or zero to bypass\n>'
        answer = input(message).lower().strip()
        answer = [int(x) for x in answer if x.isdigit()]
        if not answer:
            return
        pn, nt, ic, *_ = chain(answer, [0,0,0])
        self.no_ad_cycles['pn'] = pn
        self.no_ad_cycles['nt'] = nt
        self.no_ad_cycles['ic'] = ic

    def apply_forced(self, ac):
        (ac.pn, ac.pn_ini) = (0,0) if m.no_ad_cycles['pn'] else (ac.pn, ac.pn_ini)
        (ac.nt, ac.nt_ini) = (0,0) if m.no_ad_cycles['nt'] else (ac.nt, ac.nt_ini)
        (ac.ic, ac.ic_ini) = (0,0) if m.no_ad_cycles['ic'] else (ac.ic, ac.ic_ini)

    def update_forced_count(self):
        for i in ('pn', 'nt', 'ic'):
            if self.no_ad_cycles[i]:
                self.no_ad_cycles[i] -= 1

    def update_active_cycles(self):
        if m.earned_devices >= 4:
            m.active_cycles += 1

    def end_cycle_routine(self):
        m.total_cycles += 1
        m.update_active_cycles()
        m.update_forced_count()
        self.first_dev_to_farm = DEVS[0]


class AdsCount:
    '''
    Single device Ads manager.
    Restart on each device cycle.
    '''
    def __init__(self, dev, only_first_references=False):
        self.dev = dev
        self.color = {}
        self.client_path = cfg.dirs(self.dev, 'ads_service', 'client.json')
        self.client_size = self.get_client_size()
        self.client_last_uuid = None
        self.client_parses = 0
        self.only_first_references = only_first_references  # faster parser for m.check_idle use
        self.set_first_references()

    def get_client_size(self):
        for _ in range(10):
            try:
                return os.path.getsize(self.client_path)
            except FileNotFoundError:
                sleep(0.1)

    def has_client_size_changed(self):
        size = self.get_client_size()
        if self.client_size != size:
            self.client_size = size
            return True
        return False

    def update_ads(self, sql):
        if sql:
            self.ads = ads.parse_ads(self.dev, sql=sql, sql_table='ad_events', sql_confirmation_type='served')
            return True
        client_data = ads.parse_client_json(self.dev)
        if not client_data:
            return False
        last_uuid = client_data[0]['uuid']
        if self.client_last_uuid == last_uuid:
            return False
        self.client_last_uuid = last_uuid
        self.ads = ads.parse_ads(self.dev, sql=False, sql_table='ad_events', sql_confirmation_type='served', client_data=client_data)
        self.client_parses += 1
        return True

    def all_ptr(self, ad_type):
        return [x['ptr'] for x in self.first_ads[ad_type]['bycamp']]

    def set_first_references(self):
        # immutable references from sql
        self.update_ads(sql=True)
        self.first_ads = self.ads
        self.pn_ini = self.pn = self.ads['pn']['available']
        self.nt_ini = self.nt = self.ads['nt']['available']
        self.ic_ini = self.ic = self.ads['ic']['available']

        self.pn_gross = sum( [min(x['avail_all'], x['avail_24h'], x['avail_1h']) for x in self.ads['pn']['bycamp']] )
        self.pn_repr = f'{self.pn}/{self.pn_gross}'
        self.nt_repr = self.nt_ini
        self.ic_repr = self.ic_ini

        if self.only_first_references:
            return

        # mutable references from client.json
        self.update_ads(sql=False)
        self.pn_today_ini = self.ads['pn']['today']
        self.nt_today_ini = self.ads['nt']['today']
        self.ic_today_ini = self.ads['ic']['today']

        self.pn_earned = 0
        self.nt_earned = 0
        self.ic_earned = 0

    def update_count(self, wait=0):
        if not self.has_client_size_changed():
            return

        sleep(wait)  # prevent wrong numbers and corruption
        # print(f'\nwaited {wait}')

        if not self.update_ads(sql=False):
            return

        self.pn_today = self.ads['pn']['today']
        self.nt_today = self.ads['nt']['today']
        self.ic_today = self.ads['ic']['today']

        # Note: using max() to avoid negative results since we're using `today` ads as reference
        # since on midnight turn, `ad_today` goes zero, resulting in negative subtraction
        self.pn_earned = max(self.pn_today - self.pn_today_ini, 0) if not self.pn_earned else self.pn_earned  # single earn guarantee
        self.nt_earned = max(self.nt_today - self.nt_today_ini, 0)
        self.ic_earned = max(self.ic_today - self.ic_today_ini, 0)

        # net available ads
        # self.pn = self.pn_earned if not self.pn else self.pn  # once it's been set to 1 no need to reassign
        self.pn = max(self.pn_ini - self.pn_earned, 0)
        self.nt = max(self.nt_ini - self.nt_earned, 0)
        self.ic = max(self.ic_ini - self.ic_earned, 0)

        return True

    def update_color(self):
        empty   = '[bright_black]'
        match   = '[bright_cyan]'
        unmatch = '[red]'

        # self.color['pn'] = match if self.pn_earned else empty

        for ad_type in ('pn', 'nt', 'ic'):
            ad = eval(f'self.{ad_type}_ini')
            ad_earned = eval(f'self.{ad_type}_earned')
            if ad:
                if ad_type == 'pn':
                    self.color[ad_type] = unmatch if not ad_earned else match
                else:
                    self.color[ad_type] = unmatch if ad_earned < ad else match
            else:
                self.color[ad_type] = match if ad_earned else empty


def farmer():

    def click_ad():
        if m.got_pn or m.pn_from_ic:
            return
        ac.update_count(0.25)
        if not ac.pn_earned:
            return
        m.got_pn = True
        last_pn = ac.ads['pn']['last']
        if last_pn['time'] > 300:  # overcautious 5 min window
            return
        value = last_pn['value'] or 10
        ptr   = last_pn['ptr']   or 10
        return
        if value < 0.005 or (value < 0.01 and ptr == 0.01):
            ct.click('close_ad')
            sleep(1)
        elif value > 0.005:
            ct.click('ad')
            sleep(1)

    def trigger_pn():
        '''
        These values are very close to the minimum required to trigger `pn`,
        so please be cautious when editing them or their inner functions.
        Also, idle mouse activity seems to block the initialization proccess,
        which was solved with `windll.user32.BlockInput`.
        '''
        load_mouse_event(max_dur=0.6)
        ct.press(n=6)
        ct.click()
        ct.silent(5.75)
        ct.click()
        ct.press(n=5)
        click_ad()
        if m.got_pn:
            return True

    def earn_pn(n=1):
        click_ad()
        if not ac.pn or m.got_pn:
            return
        for i in range(n):
            if not m.has_enough_unb_tok(dev):
                break
            if i == 0 or PN_ONE_PAGE_PER_TRY:
                ct.open_page(sg=sg)
            for _ in range(PN_TRIGGERS_PER_TRY):
                if trigger_pn():
                    return

    def earn_nt():

        def trigger_by_scroll():
            '''
            try and refill unblinded tokens
            new tab interaction might not refill unblinded tokens if there's none
            but triggering ic mechanism certainly will
            '''
            ct.press('pagedown')
            trigger_pn()
            ct.press('home')
            sleep(0.2)

        def refresh(n=1):
            ''' trigger by refreshing new tab '''
            for i in range(n):
                ct.press('f5')
                sleep(0.1)

        def relaunch():
            ''' trigger by relaunching brave '''
            ct.kill(print_=False)
            min_core_wait = 4
            final_wait = 1.19455

            t0 = timer()
            sleep(0.3)
            ct.run_brave(dev, 'blank')
            sleep(0.5)
            for i in range(2):
                ct.open_page()
                sleep(0.35)
            diff = min_core_wait - (timer() - t0)
            print(diff)
            sleep(diff)
            ct.open_new_tab()
            sleep(final_wait)  # very important parameter; if below 1s or too long won't trigger nt

        def switch_tab_and_refresh():
            ''' trigger by switching tabs to avoid `user was inactive` '''
            # for _ in range(4):
            ct.ctrl_tab()
            sleep(0.1)
            ct.ctrl_tab()
            sleep(0.1)
            ct.press('f5')
            sleep(0.15)

        # def trigger(first):
        #     avail = ac.nt
        #     if first:  # first nt was supposed earned on second tab refresh
        #         avail -= 1
        #     for i in range(avail + extra):
        #         if not m.has_enough_unb_tok(dev):
        #             break
        #         if i >= avail:
        #             ac.update_count(0)
        #             if not ac.nt:
        #                 break
        #         if NT_BY_RELAUNCH:
        #             relaunch()
        #             continue
        #         if NT_BY_SWITCH_TAB:
        #             switch_tab_and_refresh()
        #             continue
        #         for _ in range(4):
        #             ct.press('f5')
        #             ct.halt()
        #         load_mouse_event(max_dur=0.5)

        def trigger():
            avail = ac.nt
            for i in range(avail + extra):
                relaunch()
                if i == 0:
                    sleep(0)  # first attemp needs more time?
                if not m.has_enough_unb_tok(dev):
                    break
                previous = ac.nt
                for _ in range(1):
                    refresh()
                    sleep(1)
                    ac.update_count(0)
                    if not ac.nt:
                        return
                    if ac.nt > previous:
                        sleep(1)
                        break

        if not ac.nt:
            return

        extra = max(ac.nt//4, 1)

        trigger()

        if not ac.nt:
            return

        # if no unblinded tokens try refill and retry nt
        if not m.has_enough_unb_tok(dev):
            trigger_by_scroll()
            if m.has_enough_unb_tok(dev):
                trigger()

    def earn_ic():

        def scroll():
            ct.press('pagedown')
            sleep(1.1)
            for _ in range(4):
                ct.press('down')

        def first_wait():
            sleep(4.5)
            return
            if ac.pn and not m.got_pn:
                m.pn_from_ic = True
                trigger_pn()
                m.pn_from_ic = False
            else:
                sleep(4.5)

        def refresh_mode():
            # to work with at least 50% zoom
            for i in range(max_tries):
                if not m.has_enough_unb_tok(dev):
                    break
                # t1 = timer()
                ct.press('pagedown')
                first_wait() if i==0 else sleep(1.3)
                ac.update_count(0.6)
                if not ac.ic or (not ac.ic_earned and (i+1) >= tries) or i+1 == max_tries:
                    break
                if i>0 and (i+1) % IC_MOUSE_AFTER_N_SCROLLS == 0:
                    load_mouse_event(max_dur=0.5)
                    ct.click()
                ct.press('home')
                sleep(0.2)
                ct.press('f5')
                sleep(0.3)
                # print(timer()-t1)

        def scroll_mode():
            # to work with 25% zoom; preferable if possible
            scrolls = 0
            max_scrolls = 135


            sleep(1)
            ct.press('pagedown')
            first_wait()
            ac.update_count(0)
            rounds = max(tries, max_tries)
            for i in range(rounds):
                # print(ac.ic)
                if not m.has_enough_unb_tok(dev):
                    break
                for _ in range(IC_SCROLLS_PER_TRY):
                    scroll()
                    scrolls += 1
                    # print(f'{scrolls= } {ac.client_parses= }', end='\r')
                    sleep(IC_SCROLL_INTERVAL)
                    ac.update_count(0.1)
                    if not ac.ic or (not ac.ic_earned and (i+1) >= tries) or scrolls >= max_scrolls:
                        # print(f'{scrolls= } {ac.client_parses= }', end='')
                        return
                    if not scrolls%15:
                        load_mouse_event(max_dur=0.5)
                        ct.click()
                        # ?
                        # if not cfg.is_brave_running(0):
                            # print('Brave is shut down!')
                            # return

        if not ac.ic:
            return
        ac.update_count(0)
        avail = min(ac.ic, 12)
        tries = avail * IC_TRIES_MULTIPLIER
        tries = max(tries, IC_MIN_TRIES)
        max_tries = avail * IC_MAX_TRIES_MULTIPLIER  # if got at least 1 ad keep going; this amount only makes sense during low ptr pacing delivery though
        sleep(0.2)

        if NTP_ZOOM == 25:
            scroll_mode()
        else:
            refresh_mode()

    def check_unb_tokens(wait=False):
        string = '{"error":"Number of allowed tokens exceeded","statusCode":429}'
        err = False
        for _ in range(30):
            if m.has_enough_unb_tok(dev):
                return True
            if rl.search(string):
                err = True
                break
            if not wait:
                break
            sleep(2)
            rl.update_lines()
        print(f'  [bright_black]{string if err else "no unb_tokens"}')
        return False

    def check_flagged(rl):
        rl.update_lines()
        if dev not in cfg.flagged_devs:
            if ac.pn_earned or ac.nt_earned or ac.ic_earned:
                while dev in m.flagged:
                    m.flagged.remove(dev)
                return
        no_unblinded_msg = rl.search_unblinded_tokens()
        if no_unblinded_msg >= MIN_UNBL_TOK_MSG_TO_FLAG:
            if m.flagged.count(dev) < MIN_FLAGGED_STRIKES:
                m.flagged.append(dev)

    def manage_flagged_strikes():
        return False
        f_strikes = m.flagged.count(dev)
        if f_strikes:
            if f_strikes < MIN_FLAGGED_STRIKES:
                # not pre_flagged: try to fill unblinded tokens
                if dev not in cfg.flagged_devs:
                    visit(dev, n=1)
                # pre_flagged: can still earn ic (and nt?) when Rewards is disabled
                else:
                    ac.pn = ac.pn_ini = ac.nt = ac.nt_ini = 0
            else:
                print('    [bright_black]flagged?', end='')
                visit(dev, FLAGGED_VISITS)
                return True

    def retry_pn_by_relaunch():
        ''' Why did I make this? '''
        if not (PN_RETRY_BY_RELAUNCH and ac.pn and not ac.pn_earned and not filter_min_ptr):
            return
        ct.kill(print_=False)
        ct.start(dev)
        earn_pn()

    def escape_from_low_ptr():
        if m.ptr_filter:
            return False
        min_actv_devs = N_DEVS_TO_ESCAPE_LOW_PTR * (2 if hour() not in PERIOD_CATALOG else 1)
        if m.active_devices < min_actv_devs:
            return False
        print(f'[white]trying to escape from low ptr|av={m.active_devices}')
        m.active_devices = 0
        if filter_min_ptr(filter_=True):
            print('[white]Found available good ptr ads...')
            return True
        m.ptr_filter = False
        m.point_cat()

    def print_promises():
        print(f'{ads.h_color(ac.pn)}{ac.pn_repr:>5}{ads.h_color(ac.nt)}{ac.nt_repr:>4}{ads.h_color(ac.ic)}{ac.ic_repr:>4}', end='')

    def print_no_ads():
        if not no_ads:
            return
        x = f'({no_ads})'
        print(f'[bright_black]no ads{x:>4}')

    def results():
        ac.update_count()
        ac.update_color()

        m.all_pn_count += ac.pn_earned
        m.all_nt_count += ac.nt_earned
        m.all_ic_count += ac.ic_earned

        temp_act_dev = m.earned_devices
        m.earned_devices += 1 if (ac.pn_earned or ac.nt_earned or ac.ic_earned) else 0
        act_dev = m.earned_devices if (m.earned_devices - temp_act_dev) else ''

        f_strikes = m.flagged.count(dev)
        if f_strikes:
            print(f'     [yellow]flagged({f_strikes})', end='')

        if ac.pn_earned or ac.ic_earned or ac.nt_earned:
            sleep(1)

        print(f'   {ac.color["pn"]}{ac.pn_earned:>4}{ac.color["nt"]}{ac.nt_earned:>4}{ac.color["ic"]}{ac.ic_earned:>4}[bright_black]{f_time(t1):>5}[magenta]{act_dev:>3}[bright_black]{ac.client_parses:>3}', end='')

        # m.tr.find_cancer(dev, print_=False)

        killed = ct.kill()
        if not killed:
            print()


    # START
    t_cycle = time()

    refresh_pn_params()

    m.print_header()

    m.active_devices = 0

    m.earned_devices = 0

    m.prevent_restore_box_after_crash()

    devs = deepcopy(DEVS)

    no_ads = 0

    for dev in devs:

        if int(dev) < int(m.first_dev_to_farm):
            no_ads += 1
            continue

        if escape_from_low_ptr():
            farmer()
            return

        m.update_catalog()

        refresh_pn_params()

        t1 = time()

        ac = AdsCount(dev)

        m.got_pn = False

        m.apply_forced(ac)

        if manage_flagged_strikes():
            continue

        filters(dev, ac)

        if ac.pn or ac.nt or ac.ic:

            # print_no_ads()

            cfg.print_dev(dev)

            rl = ReLog(dev, full=False, only_bracket_lines=False, only_unique_lines=False)

            if not check_unb_tokens(wait=False):
                continue

            m.active_devices += 1

            no_ads = 0

            print_promises()

            sg = Segments(ac.first_ads, debug=SEGMENTS_DEBUG, filter_urls=FILTER_URLS)

            ct.start(dev)

            if not ac.pn_ini:  # dismiss user inactive error
                ct.open_page()
                sleep(2)

            if ac.nt:
                earn_nt()

            if ac.pn or ac.ic:
                if ac.pn:
                    earn_pn(PN_TRIES)
                if ac.ic:
                    ct.open_new_tab()
                    earn_ic()
                    earn_pn(PN_TRIES_AFTER_IC)

            # retry_pn_by_relaunch()  # isn't it deprecated as proven false?

            check_flagged(rl)

            results()

        else:
            no_ads += 1

    print_no_ads()
    print(f'{f_time(t_cycle):>40}[bright_magenta]{m.earned_devices:>3}')


def reconcile(force_redemption=False):
    '''
    Leave browser running to help reconciling process
    Duration is proportional to the amount of device's failed confirmations?
    '''
    def run_chunk():
        for dev, *_ in devs:
            # start(dev)
            ct.run_brave(dev, 'blank', perf=True)
            sleep(1)
            if not RECONCILE_OPEN_REWARDS:
                continue
            # ct.open_new_tab()
            # ct.open_page('rewards-internals')
            url = ''
            if url:
                ct.open_page(url)
                sleep(0.5)
                ct.press('f5')
                sleep(1)

    def monitor_chunk():
        devs_chunk = {dev:failed for dev, failed, *_ in devs}
        time_ini = cfg.now
        while True:
            # check data
            for dev in list(devs_chunk):
                # redeem failed confirmations mode
                if m.is_failed_redeem_mode:
                    failed = m.tr.len_failed(dev)
                    if failed:
                        devs_chunk[dev] = failed
                        continue
                # redeem unblinded payment tokens mode
                if not m.is_failed_redeem_mode and m.tr.len_unb_pay_tokens(dev):
                    continue
                devs_chunk.pop(dev, None)
            # success
            if not devs_chunk:
                return
            # print current chunk state
            elapsed = cfg.now - time_ini
            time_left = max(max_reconcile_duration - elapsed, 0)
            if m.is_failed_redeem_mode:
                devs_chunk = dict(sorted(devs_chunk.items(), key=lambda x: x[1], reverse=True))
            devs_chunk_string = " ".join( [f'{int(dev)}{"(" + str(failed) + ")" if m.is_failed_redeem_mode else ""}' for dev, failed, *_ in devs_chunk.items()] )
            clear_last_console_line()
            print(f'\r[bright_white]{len(devs_chunk)}[white] devs or [bright_white]{f_time(None, time_left)}[white] left: [bright_black]{devs_chunk_string}', end='\r')
            # max time reached
            if not time_left:
                return
            sleep(10)

    def print_ini():
        print('[white]\[reconcile]')
        # print(f'[white]Running [bright_white]{len(devs)} [white]out of [bright_white]{len(m.devs_to_reconcile)} [white]devices for max [bright_white]{max_reconcile_duration_} [white]minutes')
        print(f'[bright_white]{len(devs)}/{len(m.devs_to_reconcile)} [white]devs ', end=' ')
        if m.is_failed_redeem_mode:
            print(f'[bright_white]{devs_failed}/{total_failed} [white]failed', end=' ')
        print(f'[white]for max [bright_white]{max_reconcile_duration_} [white]minutes')
        for dev, *_ in devs:
            print(f'{cfg.dev_color(dev)}{int(dev):<4}', end='')
        print()
        for dev, failed, unbpaytok, *_ in devs:
            item = failed if m.is_failed_redeem_mode else unbpaytok
            print(f'[white]{item:<4}', end='')
        print()

    def print_fin():
        for dev, failed, unbpaytok, *_ in devs:
            color = 'white'
            # redeem failed confirmations mode
            if m.is_failed_redeem_mode:
                new_failed = m.tr.len_failed(dev)
                # success
                if new_failed == 0:
                    color = 'green'
                # fail
                elif new_failed == failed:
                    color = 'red'
                diff = max(failed - new_failed,0)
            # redeem unblinded payment tokens mode
            else:
                new_unbpaytok = m.tr.len_unb_pay_tokens(dev)
                # success
                if not new_unbpaytok:
                    color = 'green'
                # fail
                else:
                    color = 'red'
                diff = new_unbpaytok
            print(f'[{color}]{diff:<4}', end='')
        print(m.blank_space)
        rule(style='white')

    rule(style='white')

    m.update_devs_to_reconcile(force_redemption=force_redemption)
    if not m.devs_to_reconcile:
        return False
    devs = m.devs_to_reconcile[:m.reconcile_n_slots]

    total_failed = sum( [failed for dev, failed, *_ in m.devs_to_reconcile] ) if m.is_failed_redeem_mode else len( [dev for dev, failed, unb_pay_tokens, *_ in m.devs_to_reconcile if unb_pay_tokens] )
    devs_failed  = sum( [failed for dev, failed, *_ in devs] )                if m.is_failed_redeem_mode else len( [dev for dev, failed, unb_pay_tokens, *_ in devs if unb_pay_tokens] )

    # m.is_failed_redeem_mode = [failed for dev, failed, *_ in devs if failed]

    # per_dev  = len(devs) * RECONCILE_DUR_PER_DEV
    # per_conf = max([x[1] for x in devs]) * RECONCILE_DUR_PER_CONF
    # reconcile_duration = min(per_dev, per_conf)
    # reconcile_duration = RECONCILE_DUR_PER_ROUND
    # reconcile_duration = max(reconcile_duration, RECONCILE_MIN_DURATION)
    # if not has_failed:
    #     reconcile_duration = 1.5

    max_reconcile_duration_ = 5 if m.is_failed_redeem_mode else 1.5  # minutes
    max_reconcile_duration = max_reconcile_duration_ * 60

    print_ini()

    run_chunk()

    monitor_chunk()

    print_fin()

    m.devs_to_reconcile = m.devs_to_reconcile[m.reconcile_n_slots:]

    ct.kill(len(devs)+1)

    return True


def visit(dev, n):
    if not n:
        print()
        return
    t = time()
    cfg.print_dev(dev)
    print(f'[bright_black]{"":7}visit({n})', end='')
    url = 'random'
    ct.start(dev)
    events = [ct.halt, ct.press, ct.press_pgup, ct.press_pgdn, ct.click, load_mouse_event, load_mouse_event, load_mouse_event]
    for _ in range(n):
        t1 =time()
        ct.open_page(url)
        for _ in range(15):
            n = ct.r(2,3)
            event = choice(events)
            event(n=n)
            ct.halt(n)
        elapsed = time() - t1
        # print(elapsed)
        wait = max(60 - elapsed, 0)
        sleep(wait)
    m.tr.find_cancer(dev, print_=False)
    ct.halt()
    ct.kill()
    print(f'[bright_black]   {f_time(t)}')


def chill():
    wait = IDLE_STAND_BY_DURATION if hour() in PERIOD_CATALOG else IDLE_STAND_BY_DURATION * 2
    print(f'chilling for {wait} minutes...')
    countdown(wait * 60)
    print()


def idle_action():
    if IDLE_RECONCILE:
        has_failed = reconcile()
        if has_failed:
            return
    if IDLE_VISIT:
        m.update_devs_to_visit()
        dev = choice(m.devs_to_visit)
        visit(dev, n=IDLE_N_VISITS)
        m.devs_to_visit.remove(dev)
        return
    chill()


def hang():
    while m.idle:
        m.print_clock(rule_=False)
        check_last_day_redemption()
        idle_action()
        m.check_earn()
        if not m.earn:
            continue
        m.update_catalog()
        if filter_min_ptr(filter_=True):
            return
        if filter_min_ptr(filter_=False):
            return


def check_last_day_redemption():
    '''
    Prepare all devs to end month redemption
    To work between 22:00 - 00:00 on the last day of the month
    '''
    now = datetime.datetime.now()
    year, month, day, hour, minute = now.year, now.month, now.day, now.hour, now.minute
    last_day_month = calendar.monthrange(year, month)[1]
    if day != last_day_month:
        return
    if hour not in (22,23):
        return
    print('[red]Entering redemption mode')
    for dev in DEVS:
        with Preferences(dev, print_=False) as pf:
            pf.check_next_time_redemption_at()
    print('All devs redemption time changed to now\nReconciling...')
    while True:
        devs_to_redeem = reconcile(force_redemption=False)
        if not devs_to_redeem:
            break


def filter_min_ptr(filter_):
    '''
    Check scenarios filtering min_ptr or not
    If ads, apply the changes to all devs's client.json
    '''
    # nothing to do: filter_ True or False will have same results
    # if not filter_ and ads.cat_all.min_ptr >= cfg.excpt_json['min_values']['ptr']:
    if not filter_:
        return False
    m.ptr_filter = filter_
    print(f'[bright_white]filter min_ptr: {m.ptr_filter}', end=' ')
    m.point_cat()
    m.check_idle()
    # no ads
    if m.idle:
        return False
    csids_to_ban = cfg.excpt_json['bad_csids'] if filter_ else []
    # ads, but no need to apply ban to all devs
    if csids_to_ban == m.last_banned_csids:
        return True
    # ads, apply ban
    cfg.all_ban_csid(devs=DEVS, mode='add' if filter_ else 'clean')
    m.last_banned_csids = deepcopy(csids_to_ban)
    return True


def get_ready():
    check_last_day_redemption()
    m.check_and_run_unb_tok()
    m.check_earn()
    # not earn eligible, hang
    if not m.earn:
        hang()
        return
    m.update_catalog(forced=True)
    # check filtered ads
    if filter_min_ptr(filter_=True):
        return
    # check all ads
    if filter_min_ptr(filter_=False):
        return
    # no ads at all, hang
    hang()


def main():

    cfg.close_brave(print_=True)

    m.update_catalog(forced=False)

    cfg.all_clean_client_ads_history(devs=DEVS, max_size=MAX_CLIENT_HISTORY_SIZE)

    m.config_devices()

    m.input_forced()

    os.system('cls')

    m.print_catalog()

    while True:
        try:
            get_ready()

            farmer()

            m.end_cycle_routine()
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            sleep(60)
            pass


m = Manager()
