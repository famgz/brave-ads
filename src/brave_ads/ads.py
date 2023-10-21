import os
import os.path as p
import sys
from copy import deepcopy
from famgz_utils import (
    print,
    rule,
    input,
    enable_print,
    disable_print,
    json_,
    timestamp_to_date,
    timestamp_to_full_date,
    f_time,
    timeit,
    split_utc_date,
    date_to_timestamp,
    get_local_date_time,
    ldap_to_timestamp,
    dayparts,
    weekday,
    is_valid_uuid,
    clear_last_console_line
)
from os.path import join as pj
from pathlib import Path
from time import sleep
from types import SimpleNamespace

from .config import cfg


class Ads:

    def __init__(self) -> None:
        self.catalog = None
        self.campaigns = None
        self.cat = None
        self.cat_all = None
        self.cat_net = None
        self.cat_last_update_time = 0

        self.ad_types = {'ad_notification': 'pn', 'new_tab_page_ad': 'nt', 'inline_content_ad': 'ic'}
        self.ad_types_alias = {'pn': 'ad_notification', 'nt': 'new_tab_page_ad', 'ic': 'inline_content_ad', 'ad': 'ad'}
        self.ad_types_cat = {'notification': 'pn', 'new_tab_page': 'nt', 'inline_content': 'ic'}

        self.bat_price  = 0
        self.real_price = 0


    ''' UTILS '''
    def get_bat_price(self):
        if not self.bat_price:
            import requests
            url = 'https://sampson.codes/brave/ads/my_region/bat.json'
            headers = { 'authority': 'sampson.codes', 'cache-control': 'max-age=0', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36', 'accept': '*/*', 'sec-gpc': '1', 'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'cors', 'sec-fetch-dest': 'empty', 'referer': 'https://sampson.codes/brave/ads/my_region/', 'accept-language': 'en-US,en;q=0.9', }
            r = requests.get(url, headers=headers)
            rj = r.json()
            self.bat_price = rj['price']


    def get_real_price(self):
        if not self.real_price:
            import requests
            url = 'https://economia.awesomeapi.com.br/USD-BRL/1?format=json'
            headers = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36', }
            r = requests.get(url, headers=headers)
            rj = r.json()
            self.real_price = float(rj[0]['bid'])


    def limits(self, ad_type, interval):
        '''
        Fixed limits imposed by the browser.
        '''
        return {
            'pn': {
                '1h': 10,
                '24h': 100,
            },
            'nt': {  # changed after updating from v1.41.100, it's probably campaign driven now
                '1h': 4,
                '24h': 40,
            },
            'ic': {
                '1h': 6,
                '24h': 20,
            }
        }[ad_type][interval]


    def h_color(self, item, result=False):
        high = '[bright_cyan]' if result else '[bright_white]'
        low  = '[bright_black]'
        return high if item else low


    def unbtok_color(self, unbtok):
        if unbtok < 10:
            return '[red]'
        if 10 <= unbtok < 20:
            return '[yellow]'
        return '[white]'


    ''' CATALOG '''
    @property
    def min_update_interval(self):
        min_interval = 300  # 5 min
        elapsed = cfg.now - self.cat_last_update_time
        return elapsed > min_interval


    # catalog manager
    def update_catalog(self, from_file=False, file='campaigns', forced=False):
        '''
        Catalog manager.
        '''
        if self.catalog and (not self.min_update_interval and not forced):
            return

        self.cat_last_update_time = cfg.now

        self.get_catalog(from_file=from_file, file=file)

        self.parse_catalog()

        self.cat = self.cat_all

        if not from_file:
            self.update_campaigns_json()
            # self.update_segments_json()

        return True


    def save_catalog(self):
        path = pj(cfg.data_dir, 'catalog.json')
        json_(path, self.catalog, backup=True)

        path = pj(cfg.data_dir, 'catalog_last_full.json')
        old = json_(path)

        if len(self.catalog['campaigns']) < len(old.get('campaigns', [])):
            return

        json_(path, self.catalog, backup=True)


    def get_catalog(self, from_file=False, file='campaigns'):

        def get_catalog_from_file(file='campaigns'):  # For debugging or history purposes only
            path = pj(cfg.data_dir, f'{file}.json')
            if p.isfile(path):
                data = json_(path)
                return data

        if from_file:
            self.catalog = get_catalog_from_file(file=file)
            return

        tries = 100 if not self.catalog else 10
        # for i in range(1, tries):
        i=0
        while True:
            try:
                import requests
                headers = {
                    'authority': 'ads-static.brave.com',
                    'cache-control': 'max-age=0',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36',
                    'accept': '*/*',
                    'sec-gpc': '1',
                    'origin': 'https://sampson.codes',
                    'sec-fetch-site': 'cross-site',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'referer': 'https://sampson.codes/',
                    'accept-language': 'en-US,en;q=0.9',
                }
                r = requests.get('https://ads-static.brave.com/v9/catalog', headers=headers, timeout=10)
                assert r.ok
                rj = r.json()
                assert rj
                self.catalog = rj
                print() if i>0 else ...
                print('[bright_black]catalog updated')
                break
            except Exception as e:
                i+=1
                print(f'Error: {e} Unavailable catalog ({i})', end='\r')
                sleep(1)
            if i == tries:
                break

        assert self.catalog

        if not from_file:
            self.save_catalog()

        if i:
            print()

        if not self.catalog:
            print('Unavailable catalog.\nFalling back to local file...')
            self.catalog = get_catalog_from_file('catalog')
            if not self.catalog:
                sys.exit('WARNING, no catalog whatsoever! Exiting...')


    def update_segments_json(self):
        '''
        DEPRECATED: since we already found all existing
        segments on `feibnmjhecfbjpeciancnchbmlobenjn`
        Stores new segments found on catalog.
        '''
        from copy import deepcopy
        segs_path = pj(cfg.data_dir, 'segments.json')
        old = json_(segs_path) or {}
        new = deepcopy(old)
        for camps in self.catalog['campaigns']:
            for cs in camps['creativeSets']:
                for segs in cs['segments']:
                    name = segs['name'].lower()
                    parent, *child = name.split('-')
                    new.setdefault(parent, [])
                    if child:
                        child = child[0]
                        if child not in new[parent]:
                            new[parent].append(child)
        if not new or new == old:
            return
        for seg in new.values():
            seg.sort()
        json_(segs_path, new, backup=True, indent=2, sort_keys=True)
        print('[bright_black]segments.json updated')


    def update_campaigns_json(self):
        '''
        Save and update all campaigns to campaigns.json
        '''
        def sort_camp_nested_lists(camps):
            for camp in camps:
                for cs in camp['creativeSets']:
                    cs['creatives'].sort(key=lambda x: x['creativeInstanceId'])
                    cs['oses'     ].sort(key=lambda x: x['code'])
                    cs['segments' ].sort(key=lambda x: x['code'])

        path = pj(cfg.data_dir, 'campaigns.json')

        to_add = []
        add_count = 0
        update_count = 0
        old = json_(path)
        sort_camp_nested_lists(old['campaigns'])
        sort_camp_nested_lists(self.campaigns)
        old_camps_list = [c['campaignId'] for c in old['campaigns']]
        for new in self.campaigns:
            # add new campaign
            if new['campaignId'] not in old_camps_list:
                to_add.append(new)
                add_count += 1
                continue
            # update if different
            match = [x for x in old['campaigns'] if x['campaignId'] == new['campaignId']][0]
            if new != match:
                i = old['campaigns'].index(match)
                old['campaigns'][i] = new
                update_count += 1
        old['campaigns'].extend(to_add)

        if add_count or update_count:
            json_(path, old, indent=1, backup=True, n_backups=1)
            print('[bright_black]campaigns.json updated')


    def parse_catalog(self):

        def ptr(camp):
            x = camp['ptr']
            if x == 1:
                return int(x)
            if x < 0.1:
                return round(x,5)
            return round(x,2)

        def total_max(camp):
            x = sum( [x['totalMax'] for x in camp['creativeSets']] )
            return x

        def per_day(camp):
            perDay = sum( [x['perDay'] for x in camp['creativeSets']] )
            dailyCap = camp['dailyCap']
            return min(perDay, dailyCap)

        def per_hour(camp):
            return sum( [len(x['creatives']) for x in camp['creativeSets']] )

        def value(camp):
            return float(camp['creativeSets'][0]['value'])

        def ad_type(camp):
            return camp['creativeSets'][0]['creatives'][0]['type']['name']

        def creative_set_ids(camp):
            return [x['creativeSetId'] for x in camp['creativeSets']]

        def creative_instance_ids(camp):
            return [c['creativeInstanceId'] for cs in camp['creativeSets'] for c in cs['creatives']]

        def segments(camp):
            segs = []
            for cs in camp['creativeSets']:
                for seg in cs['segments']:
                    name = seg['name'].lower()
                    if 'sci-fi' in name:
                        name.replace('sci-fi', 'sci_fi')
                    segs.append(name)
            return segs

        def conversions(camp):
            return bool(camp['creativeSets'][0]['conversions'])

        def is_within_dayparts(camp):
            dps = camp['dayParts']
            if not dps:
                return True
            current_minute = dayparts()
            dow = str(weekday())  # weekday() -> 0=monday/6=sunday; not sure if catalog use this same format
            for dp in dps:
                if dow not in dp['dow']:
                    continue
                if dp['startMinute'] <= current_minute <= dp['endMinute']:
                    return True
            return False

        def desc(camp):
            def description(camp):
                desc = [x['payload']['description'] for x in camp['creativeSets'][0]['creatives'] if x['payload'].get('description')]
                desc.sort(key=lambda x: len(x))
                return desc[0] if desc else ''

            def title(camp):
                desc = [x['payload']['title'] for x in camp['creativeSets'][0]['creatives'] if x['payload'].get('title')]
                desc.sort(key=lambda x: len(x))
                return desc[0] if desc else ''

            def url(camp):
                url = camp['creativeSets'][0]['creatives'][0]['payload'].get('targetUrl')
                if not url:
                    return ''
                url = url.replace('https://', '')
                url = url.replace('www.', '')
                url = url.replace('.com', '')
                url, *_ = url.split('/')
                return url

            description = description(camp)
            fallbacks = [title(camp), url(camp)]
            fallbacks.sort(key=lambda x: len(x))
            res = description or fallbacks[0]
            return res[:15].strip()

        def is_cs_for_windows(cs):
            if not cs['oses']:
                return True
            for i in cs['oses']:
                if i['name'] == 'windows':
                    return True
            return False

        def is_camp_for_windows(camp):
            for cs in camp['creativeSets']:
                if is_cs_for_windows(cs):
                    return True
            return False

        def is_active_by_hour(camp):
            from famgz_utils import split_utc_date, date_to_timestamp
            campaign_date_utc_start = date_to_timestamp(*split_utc_date(camp['startAt']))
            campaign_date_utc_end   = date_to_timestamp(*split_utc_date(camp['endAt']))
            return campaign_date_utc_start < cfg.now_utc < campaign_date_utc_end

        def is_active_by_day(camp):
            from datetime import datetime
            day = datetime.now().day
            y, m, d, *_ = split_utc_date(camp['startAt'])
            return day == d

        def is_low_ptr(camp):
            return camp['ptr'] < cfg.excpt_json['min_values']['ptr']

        def is_low_value(camp):
            at = ad_type(camp)
            at_alias = self.ad_types_cat[at]
            value = float(camp['creativeSets'][0]['value'])
            return value < cfg.excpt_json['min_values'][at_alias]

        def is_banned_csid(camp):
            cs_id = creative_set_ids(camp)[0]
            return cs_id in cfg.excpt_json['bad_csids']

        def is_banned_advtid(camp):
            advt_id = camp['advertiserId']
            return advt_id in cfg.excpt_json['bad_advtids']

        def should_ignore(camp):
            if not is_within_dayparts(camp):
                return True
            if all_camps:
                return False
            if all_filters:
                return is_banned_csid(camp) or is_banned_advtid(camp)
            if filter_bad_csids and is_banned_csid(camp):
                return True
            if filter_bad_advtids and is_banned_advtid(camp):
                return True
            return False
            return is_low_value(camp)

        def remove_not_windows_cs():
            to_delete = []
            for i_camp, camp in enumerate(self.campaigns):
                for i_cs, cs in enumerate(camp['creativeSets']):
                    if not is_cs_for_windows(cs):
                        to_delete.append((i_camp, i_cs))

            for i_camp, i_cs in reversed(to_delete):
                del self.campaigns[i_camp]['creativeSets'][i_cs]

            self.campaigns = [x for x in self.campaigns if x['creativeSets']]

        def update_excpt_bad_csids():
            ''' Write low ptr (/value?) creative set ids in excpt.json '''
            old_bad_csids = cfg.excpt_json['bad_csids']
            new_bad_csids = [csid
                             for camp in self.campaigns
                             for csid in creative_set_ids(camp)
                             if (is_low_ptr(camp) or is_low_value(camp)) and is_valid_uuid(csid)]
                            #  if ad_type(camp) != 'new_tab_page' and (is_low_ptr(camp) or is_low_value(camp)) and is_valid_uuid(csid)]
            old_bad_csids.sort()
            new_bad_csids.sort()
            if old_bad_csids != new_bad_csids:
                cfg.excpt_json['bad_csids'] = new_bad_csids
                cfg.update_json('excpt')

        def parse_cat_available_ads(to_json=False):
            cat_available = {
                'pn': [],
                'nt': [],
                'ic': [],
            }
            for at, camps in [ ('pn', cat.pn), ('nt', cat.nt), ('ic', cat.ic) ]:
                for camp in camps:
                    dct = {
                        'advertiser_id': camp['advertiserId'],
                        'campaign_id':   camp['campaignId'],
                        'csids':         creative_set_ids(camp),
                        'ciids':         creative_instance_ids(camp),
                        'name':          desc(camp),
                        'conversions':   conversions(camp),
                        'total_max':     total_max(camp),
                        'per_day':       per_day(camp),
                        'per_hour':      per_hour(camp),
                        'value':         value(camp),
                        'ptr':           ptr(camp),
                        'start':         date_to_timestamp(*split_utc_date(camp['startAt'])),
                        'end':           date_to_timestamp(*split_utc_date(camp['endAt'])),
                        'segments':      segments(camp)
                    }
                    cat_available[at].append(dct)
            if to_json:
                path = pj(cfg.temp_dir, 'parsed_available_ads_catalog.json')
                json_(path, cat_available)
            return cat_available


        self.campaigns = deepcopy(self.catalog['campaigns'])

        remove_not_windows_cs()

        pn = [x for x in self.campaigns if ad_type(x) == 'notification'  ]
        nt = [x for x in self.campaigns if ad_type(x) == 'new_tab_page'  ]
        ic = [x for x in self.campaigns if ad_type(x) == 'inline_content']

        update_excpt_bad_csids()

        all_camps=False
        all_filters=False
        filter_bad_csids=False
        filter_bad_advtids=False

        self.cat_all = SimpleNamespace()
        self.cat_net = SimpleNamespace()

        for cat in self.cat_all, self.cat_net:
            if cat is self.cat_all:
                all_camps = True
                all_filters = False
            if cat is self.cat_net:
                all_camps = False
                all_filters = True

            cat.pn = [x for x in pn if not should_ignore(x)]
            cat.nt = [x for x in nt if not should_ignore(x) and is_active_by_hour(x)]
            cat.ic = [x for x in ic if not should_ignore(x)]

            cat.pn_min_ptr = min( [ptr(x) for x in cat.pn] or [1] )
            cat.nt_min_ptr = min( [ptr(x) for x in cat.nt] or [1] )
            cat.ic_min_ptr = min( [ptr(x) for x in cat.ic] or [1] )
            cat.min_ptr    = min(cat.pn_min_ptr, cat.ic_min_ptr)

            cat.pn_day   = sum( [per_day(x) for x in cat.pn] )
            cat.pn_value = sum( [per_day(x) * value(x) for x in cat.pn] )

            cat.nt_day   = 20 if cat.nt else 0
            cat.nt_value = cat.nt_day * value(cat.nt[0]) if cat.nt else 0

            cat.ic_day   = sum( [per_day(x) for x in cat.ic] )
            cat.ic_value = sum( [per_day(x) * value(x) for x in cat.ic] )

            cat.all_ads_day   = sum( [cat.pn_day, cat.nt_day, cat.ic_day] )
            cat.all_ads_value = sum( [cat.pn_value, cat.nt_value, cat.ic_value] )

            # parse available pn/ic ads
            cat.available = parse_cat_available_ads(to_json=False)


    def show_catalog(self, from_file=False):
        self.update_catalog(from_file=from_file)

        print(f'{"":-^36}')
        print(f'{"Available Campaigns":^36}')
        print(f'{"":-^36}')
        print(f'{"Type":6}{"Campaigns":^10}{"Ads/Day":^10}{"Value":^10}\n')
        print(f'{"ALL":6}{len(self.campaigns):^10}{self.cat.all_ads_day:^10}{self.cat.all_ads_value:^10.2f}')
        print(f'{"PN":6}{len(self.cat.pn):^10}{self.cat.pn_day:^10}{self.cat.pn_value:^10.2f}')
        print(f'{"NT":6}{len(self.cat.nt):^10}{self.cat.nt_day:^10}{self.cat.nt_value:^10.2f}')
        print(f'{"IC":6}{len(self.cat.ic):^10}{self.cat.ic_day:^10}{self.cat.ic_value:^10.2f}')


    ''' DATABASE.SQLITE '''
    @cfg.check_dev
    def sql_to_dict(self, dev, file, table, to_json=False, force_close=True):

        sql_path = {
            'database':          cfg.dirs(dev, 'ads_service', 'database.sqlite'),
            'publisher_info_db': cfg.dirs(dev, 'default', 'publisher_info_db')
        }[file]

        import sqlite3
        import pandas as pd

        for _ in range(5):
            if not os.access(sql_path, os.R_OK):
                print(f'[brigth_black]Cannot read file: {sql_path}')
                sleep(.1)
                continue
            try:
                with sqlite3.connect(sql_path) as db:
                    cursor = db.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    table = pd.read_sql_query(f"SELECT * from {table}", db)
                    data = table.to_dict(orient='index')

                if to_json:
                    path = pj(cfg.temp_dir, f'{dev}_{table}.json')
                    json_(path, data)

                return [x for x in data.values()]
            except sqlite3.OperationalError as e:
                print(e)

        '''
        # to iterate over all tables
        tables = cursor.fetchall()
        for table_name in tables:
            table_name = table_name[0]
            if table_name == 'transactions':
                table = pd.read_sql_query("SELECT * from transactions", db)
                # a = table.to_json(table_name + '.json', orient='index')
                a = table.to_dict('index')
        '''


    @cfg.check_dev
    def parse_sql_database(self, dev, sql_table='transactions', sql_confirmation_type='view', to_json=False, force_close=False):
        '''
        Return List[Dict] from single dev\n
        Tables:
            history:
                ad_events     has all ids, no values
                transactions  limited ids, values
            available:
                creative_ad_notifications
                creative_inline_content_ads
                creative_new_tab_page_ads
        Confirmation types:
            served     if available regardless
            view       if served and passed the minimum view window
            click      if viewed and clicked
            landed     if clicked and passed minimum visit window
            dismiss    if viewed and closed ?
            conversion ? (rare)
        '''
        confirmation_types = {
            'ad_events':    ['click', 'conversion', 'dismiss', 'landed', 'served', 'view'],
            'transactions': ['click', 'conversion', 'dismiss', 'landed',           'view'],
        }

        # validating confirmation type
        # all types
        if not sql_confirmation_type:
            sql_confirmation_type = confirmation_types[sql_table]
        # filter specific types, transform to list, check if exists
        else:
            sql_confirmation_type = [sql_confirmation_type] if isinstance(sql_confirmation_type, str) else sql_confirmation_type
            assert not [x for x in sql_confirmation_type if x not in confirmation_types[sql_table]]

        # reading db
        ads = self.sql_to_dict(dev, file='database', table=sql_table, to_json=False, force_close=force_close)
        if sql_table in confirmation_types:
            ads = [x for x in ads if x['confirmation_type'] in sql_confirmation_type]
            # normalizing key names to match global naming convention
            for ad in ads:
                ad['timestamp'] = ldap_to_timestamp(ad.pop('created_at'))
                if sql_table == 'transactions':
                    ad['type'] = ad.pop('ad_type')
                    ad['uuid'] = ad.pop('id')
                if sql_table == 'ad_events':
                    ad['uuid'] = ad.pop('placement_id')

        if to_json:
            path = pj(cfg.temp_dir, f'{dev}_parsed_{sql_table}.json')
            json_(path, ads)

        return ads


    @cfg.check_dev
    def parse_sql_publisher_info_db(self, dev, sql_table='balance_report_info', to_json=False, force_close=False):
        '''
        Publisher info db have a few useful info like balance_report_info and event_log
        '''
        pub_info_db = self.sql_to_dict(dev, file='publisher_info_db', table='balance_report_info', to_json=False, force_close=force_close)
        event_log   = self.sql_to_dict(dev, file='publisher_info_db', table='event_log', to_json=False, force_close=force_close)

        if sql_table == 'balance_report_info':
            claims  = sum( [float(x['grants_ads']) - float(x['auto_contribute']) - float(x['tip_recurring']) - float(x['tip']) for x in pub_info_db] )
            drained = sum( float(x['value']) for x in event_log if x['key'] == 'promotion_vbat_drained')
            data = max(claims - drained, 0)
            data = float(data) or 0

        if to_json:
            path = pj(cfg.temp_dir, f'{dev}_parsed_{sql_table}.json')
            json_(path, data)

        return data


    def sort_parsed_transactions_by_date(self, devs=None, to_json=True, structure='by_day',force_close=True):
        '''
        Return formats by structure:
        by_day -> {date: {user: {ad_type: [ad values]}}}}
        tree:  -> {year: {month: {day: {user: {ad_type: [ad values]}}}}}}
        '''
        assert structure in ('tree', 'by_day')

        cfg.close_brave()  # Force close Brave applications to avoid data corruption

        all_ads = {}

        devs = devs or cfg.devs

        for dev in devs[:]:
            ads = self.parse_sql_database(dev, to_json=False, force_close=force_close)
            for ad in ads:
                date_ = timestamp_to_date(ad['timestamp'])
                date_ = str(date_)

                ad_type = self.ad_types.get(ad['type'], ad['type'])

                if structure == 'tree':
                    year, month, day = date_.split('-')
                    all_ads.setdefault(year, {})\
                            .setdefault(month, {})\
                            .setdefault(day, {})\
                            .setdefault(dev, {})\
                            .setdefault(ad_type, [])\
                            .append(ad['value'])

                elif structure == 'by_day':
                    all_ads.setdefault(date_, {})\
                            .setdefault(dev, {})\
                            .setdefault(ad_type, [])\
                            .append(ad['value'])

        # placing latest date on top
        if structure == 'tree':
            all_ads = dict(sorted(all_ads.items(), reverse=True))  # sorting years
            for year in all_ads:
                all_ads[year] = dict(sorted(all_ads[year].items(), reverse=True))  # sorting months
                for month in all_ads[year]:
                    all_ads[year][month] = dict(sorted(all_ads[year][month].items(), reverse=True))  # sorting days

        if structure == 'by_day':
            all_ads = dict(sorted(all_ads.items(), reverse=True))

        if to_json:
            path = pj(cfg.temp_dir, f'ads_{structure}.json')
            json_(path, all_ads)

        return all_ads


    @timeit
    def show_full_ads_from_transactions_sql(self, devs_code=None, day_range=10):

        def print_devs():
            print()
            print(f'{"":7}', end='')
            for dev in devs:
                print(f'{cfg.dev_color(dev)}{cfg.fdev(dev):>6}', end='')
            # current prices
            print(f"  {f_val(1, 'bat', decimal=0)}{f_val(1, 'usd', decimal=3)}{f_val(1, 'brl', decimal=3)}", end='')
            # projections
            print(f"  {f_val(1, 'bat', decimal=0)}{f_val(1, 'usd', decimal=0, bat_price=1)}{f_val(1, 'brl', decimal=0, bat_price=1, real_price=5)}")

        def f_qty(qty, suffix=True, spacing=7):
            s = f'[{col_cur}] ads' if suffix else ""
            qty = qty or '-'
            return f'[{col_qty}]{qty:>{spacing}}{s}'

        def f_val(val, out, suffix=True, decimal=2, spacing=8, bat_price=None, real_price=None, contrast=False):
            bat_price  = bat_price  or self.bat_price
            real_price = real_price or self.real_price
            value = {
                'bat': val,
                'usd': val * bat_price,
                'brl': val * bat_price * real_price,
            }
            value = value[out]
            value = f'{value:>{spacing}.{decimal}f}' if value else f'{empty:>{spacing}}'
            currency = out.upper()
            currency = f'[{col_cur}] {currency}' if suffix else ""
            color = col_val_high if contrast else col_val
            return f'[{color}]{value}{currency}'

        col_val      = 'bright_white'
        col_val_high = 'bright_cyan'
        col_qty      = 'white'
        col_cur      = 'bright_black'

        empty = '-'

        day_range = day_range or 1000  # parsing 0 will cause full display

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'd'
            os.system('cls')
        devs = cfg.get_devs_group(devs_code) or cfg.devs

        all_ads_by_day = self.sort_parsed_transactions_by_date(devs=devs, structure='by_day', to_json=False)

        self.get_bat_price()
        self.get_real_price()

        # display daily values by device
        print('\n\n')
        rule('Full Ads History By Day', style='[white]')

        # devs = cfg.devs[:]

        print_devs()
        ads = {}

        for i, (date_, data) in enumerate(all_ads_by_day.items()):
            year_month = date_[:7]
            can_print = (i <= day_range)
            if can_print:
                print(f'[bright_white]{date_[5:]:7}')
            qty_day = val_day = 0
            for out in ('qty', 'val'):
                if can_print:
                    print(f'{"":7}', end='')
                for i, dev in enumerate(devs):
                    if can_print:
                        print(f'[bright_black]{"" if i==0 else "|"}', end='')
                    if out == 'qty':
                        x = [len(data.get(dev, {}).get(ad_type, [])) for ad_type in self.ad_types_alias | {"":""}]  # some transactions are ad_type: ""
                        x = sum(x)
                        qty_day += x
                        if can_print:
                            print(f'[white]{x or empty:>5}', end='')

                    elif out == 'val':
                        x = [sum(data.get(dev, {}).get(ad_type, [])) for ad_type in self.ad_types_alias | {"":""}]
                        x = sum(x)
                        val_day += x
                        value_f = f'{x:.2f}' if x else empty
                        if can_print:
                            print(f'[bright_white]{value_f:>5}', end='')

                    ads.setdefault(year_month, {}).setdefault(dev, {}).setdefault(out, 0)  # ads qty/val by device monthly
                    ads.setdefault(year_month, {}).setdefault(out, 0)                      # ads qty/val monthly total
                    ads.setdefault('total', {}).setdefault(dev, {}).setdefault(out, 0)     # ads qty/val by device total
                    ads.setdefault('total', {}).setdefault(out, 0)                         # ads qty/val total

                    ads[year_month][dev][out] += x
                    ads[year_month][out]      += x
                    ads['total'][dev][out]    += x
                    ads['total'][out]         += x

                # daily totals
                if out == 'qty' and can_print:
                    print('   ', f_qty(qty_day))
                elif out == 'val' and can_print:
                    print(f"   {f_val(val_day, 'bat')}{f_val(val_day, 'usd')}{f_val(val_day, 'brl')}", end='')
                    print(f"  {f_val(val_day, 'bat')}{f_val(val_day, 'usd', bat_price=1)}{f_val(val_day, 'brl', bat_price=1, real_price=5)}")

        ads['total'] = ads.pop('total')

        # display monthly values by device
        print('\n\n')
        rule('Full Ads History By Month', style='[white]')
        print_devs()
        for year_month in ads:
            print(f'[bright_white]{year_month:7}')
            for out in ('qty', 'val'):
                print(f'{"":7}', end='')
                for i, dev in enumerate(devs):
                    print(f'[bright_black]{"" if i==0 else "|"}', end='')
                    x = ads[year_month][dev][out]
                    print(f_qty(x, False, spacing=5), end='') if out == 'qty' else print(f_val(x, 'bat', False, 1, 5), end='')
                x = ads[year_month][out]
                if out == 'qty':
                    print('   ', f_qty(x))
                else:
                    contrast = True if year_month == 'total' else False
                    print(f"   {f_val(x, 'bat')}{f_val(x, 'usd')}{f_val(x, 'brl', contrast=contrast)}", end='')
                    print(f"  {f_val(x, 'bat')}{f_val(x, 'usd', bat_price=1)}{f_val(x, 'brl', bat_price=1, real_price=5, contrast=contrast)}")


    @timeit
    def show_campaigns_stats(self, devs_code=None):
        '''
        Show all device stats from given catalog campaigns.
        Reads from live catalog or file.
        When reading from file can specify which campaigns to parse.
        '''

        def labels():
            concat('\nLABELS:\n')
            [concat(f' {color}██  [white]{desc}')
                for color, desc in (
                    ('[bright_black]', 'expired'),
                    ('[magenta]',      'expired, completed'),
                    ('[bright_cyan]',  'net available'),
                    ('[red]',          'active, completed'),
                    ('[white]',        'active, completed (1h/24h only)'),
                    ('[yellow]',       'active, < 1/3 available'),
                    ('[bright_white]', 'active, > 1/3 available'),
                )
            ]
            concat()

        def separator():
            qty = max([len(camps) for camps in cat.values()])
            pad = 8 + (qty * 24)
            text = f' {ad_type.upper()} '
            concat(f'\n[bright_white]{text:─^{pad}}\n')

        def status_color(matches, camp, type_, total, expired):
            # net available
            if type_ == 'available':
                if expired:
                    return 'bright_black'
                return 'bright_cyan'
            # expired
            if expired:
                if matches >= camp['total_max']:
                    return 'magenta'
                return 'bright_black'
            # sold out
            if matches >= total:
                return 'red' if type_ == 'matches_all' else 'white'
            # < 1/3 available
            if matches >= total * (2/3):
                return 'yellow' if type_ == 'matches_all' else 'bright_white'
            # > 1/3 available
            if matches < total * (2/3):
                return 'bright_white'

        def get_camps():
            cat = {ad_type: camps for ad_type, camps in self.cat.available.items() if camps}
            if camp_id:
                return {ad_type: [camp] for ad_type, camps in cat.items() for camp in camps if camp['campaign_id'].startswith(camp_id)}
            if only_active:
                cat_active = {}
                for ad_type, camps in cat.items():
                    for camp in camps:
                        if cfg.now_utc < camp['end']:
                            cat_active.setdefault(ad_type,[]).append(camp)
                return cat_active
            return cat

        def get_dev_data(devs):
            ''' Prepare dev's data to avoid multiple readings '''
            print('Parsing devs data')
            d = {}
            for i, dev in enumerate(devs):
                clear_last_console_line()
                print(f'{i+1}/{len(devs)}', end='')
                d[dev] = ads.parse_ads(dev, sql=True, all_camp_info=True)
            return d

        def get_fallback_data(cat):
            ''' Prepare catalog campaigns data in case there's no dev record '''
            print('Parsing catalog data')
            return {
                camp['campaign_id']: {
                    'available': min(camp['total_max'], camp['per_day'], camp['per_hour']),
                    'matches_1h': (0, camp['per_hour']),
                    'matches_24h': (0, camp['per_day']),
                    'matches_all': (0, camp['total_max'])
                }
                for camps in cat.values() for camp in camps
            }

        def concat_(string='', end='\n'):
            ''' Join together all strings to run a single print function (faster?) '''
            nonlocal final_output
            final_output.append(string + end)

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'd'
            os.system('cls')
        devs = cfg.get_devs_group(devs_code)

        from_file   = False
        camp_id     = None
        only_active = False

        from_file = bool(input('Any key to read from campaigns.json\nor Enter to read from current catalog\n>'))
        if from_file:
            camp_id = input('Input campaign id (or its first 8 chars) to filter through\nor Enter to view all campaigns\n>').strip() or None
            if not camp_id:
                only_active = bool(input('Any key to show only active campaigns\nor Enter to view all campaigns\n>'))

        self.update_catalog(from_file=from_file, forced=True)

        cat = get_camps()
        devs_data = get_dev_data(devs)
        fallback_data = get_fallback_data(cat)

        final_output = []

        concat = print

        # header
        os.system('cls')
        labels()
        concat(f'[white]{"net":>14}{"1h":>5}{"24h":>5}{"all":>8}')
        concat(f'[white]{"(earned/total)":>32}')
        for ad_type, camps in cat.items():
            separator()
            # print()
            # rule(ad_type.upper(), style='white')
            # print()
            # titles
            items = (
                    ('name',          '[bright_white]'),
                    ('campaign_id',   '[bright_black]'),
                    ('advertiser_id', '[bright_black]'),
                    ('csids',         '[bright_black]'),
                    ('value',         '[white]'),
                    ('ptr',           '[bright_black]'),
                    ('conversions',   '[bright_black]')
            )
            for info, color in items:
                concat(f'[white]{info[:8]:<8}', end='')
                for camp in camps:
                    if info in ('campaign_id', 'advertiser_id'):
                        desc = camp[info][:8]
                    elif info == 'csids':
                        desc = camp[info][0][:8]
                    elif info == 'ptr':
                        desc = f'{camp[info]:.3f}' if camp[info] < 1 else camp[info]
                    else:
                        desc = f'{camp[info]}'
                    concat(f"{color}{desc:>24}", end='')
                concat()
            concat()
            # data
            for i, (dev, dev_data) in enumerate(devs_data.items()):
                clear_last_console_line()
                concat(cfg.format_dev(dev, pad=5), end='')
                for camp in camps:
                    fallback = fallback_data[camp['campaign_id']]
                    # dev_data = self.parse_ads(dev, sql=True, all_camp_info=True)
                    expired = cfg.now_utc > camp['end']
                    dev_bycamp = [x for x in dev_data[ad_type]['bycamp'] if x['campaign_id'] == camp['campaign_id']]
                    dev_bycamp = dev_bycamp[0] if dev_bycamp else fallback
                    for m, pad in [('available', 6), ('matches_1h', 5), ('matches_24h', 5), ('matches_all', 8)]:
                        nums = dev_bycamp[m]
                        if m == 'available':
                            earned = nums if nums and not expired else ''
                            total  = 0
                        else:
                            earned = nums[0]
                            total  = nums[1]
                        res = f"{earned}/{total}" if m != 'available' else earned
                        color = status_color(earned, camp, m, total, expired)
                        concat(f'[{color}]{res:>{pad}}', end='')
                concat()

        # sleep(3)
        # os.system('cls')
        # for i in final_output:
        #     print(i, end='')


    @cfg.check_dev
    def get_last_ad(self, dev, sql=False, ad_type='pn'):
        '''
        Get the newer ad value from given type within time window.
        Originally made to avoid cliking cheap `pn` ads in farmer and triggers "dismiss".
        '''
        ad_type = self.ad_types_alias[ad_type]
        ads = self.parse_sql_database(dev, sql_table='transactions', sql_confirmation_type='view') if sql else self.parse_client_json(dev)
        ads = [x for x in ads if x['type'] == ad_type]
        if not ads:
            return
        ads.sort(key=lambda x: int(x['timestamp']))
        last_ad = ads[-1]
        elapsed = cfg.now - int(last_ad['timestamp'])
        if elapsed > 300:  # overcautious 5 min window
            return
        return last_ad


    @cfg.check_dev
    def get_older_24h_ad(self, dev, camp_id=None, ad_type=None, formatted=True):
        '''
        Search for matches in an ad 24h window and
        projects how many time left to next cycle.
        Originally made to check when next `nt` cycle will be available.
        '''
        def filter_camp_id(ads):
            return [x for x in ads if x['campaign_id'].startswith(camp_id)]

        def filter_last_24h(ads):
            return [x for x in ads if x['type'] in ad_type and ((cfg.now - x['timestamp']) <= cfg.day_in_sec)]

        ad_type = [self.ad_types_alias[ad_type]] if ad_type else self.ad_types
        ads = self.parse_sql_database(dev, sql_table='ad_events', sql_confirmation_type='view')
        ads = filter_camp_id(ads) if camp_id else ads
        ads = filter_last_24h(ads)
        if ads:
            ads.sort(key=lambda x: int(x['timestamp']), reverse=True)  # --> [newer... older]
            older_ad = ads[-1]
            projection = older_ad['timestamp'] + cfg.day_in_sec
            diff = max(projection - cfg.now, 0)  # how many seconds until next ad will be available
            return f_time(None, diff, out='partial') if formatted else diff
        return '0s' if formatted else 0


    @cfg.check_dev
    def parse_losses(self, dev):
        data = self.parse_sql_database(dev, sql_table='ad_events', sql_confirmation_type=None)
        dct = {}
        for ad_type in self.ad_types:
            for conf_type in ('served', 'view'):
                dct.setdefault(ad_type, {})[conf_type] = len([x for x in data if x['type'] == ad_type and x['confirmation_type'] == conf_type])
            diff = max(dct[ad_type]['served'] - dct[ad_type]['view'], 0)
            res = f"{dct[ad_type]['view']}/{dct[ad_type]['served']}"
            print(f'[{"red" if diff else "bright_black"}]{diff:>5}[white]{res:>10}', end='')


    def show_losses(self):
        '''
        Show lost ads (served but not viewed)
        '''
        from famgz_utils import LogPrint
        log_path = pj(cfg.data_dir, 'losses')
        lp = LogPrint(log_path, dated=False)
        global print
        print = lp.print_

        print(f'\n\n{get_local_date_time():─^54}\n')
        print(f'{"":12}{"PN":^15}{"NT":^15}{"IC":^15}')
        for dev in cfg.devs:
            cfg.print_dev(dev)
            print(f' [white]{"":<7}', end=' ')
            self.parse_losses(dev)
            print()


    ''' JSON '''
    # CLIENT.JSON
    @cfg.check_dev
    def check_unblinded_tokens(self, dev):
        path = cfg.dirs(dev, 'ads_service', 'confirmations.json')
        if not p.isfile(path):
            print(f'Invalid confirmations.json path: {path}')
            return
        for _ in range(2):
            try:
                data = json_(path)
                unblinded_tokens = data['unblinded_tokens']
                return len(unblinded_tokens)
            except PermissionError:
                pass


    @cfg.check_dev
    def get_client_json(self, dev):
        path_client = cfg.dirs(dev, 'ads_service', 'client.json')
        return json_(path_client)


    def _parse_client_json_adcontent(self, ad):
        ac = ad['ad_content']
        ac['uuid']                 = ac.pop('placementId')
        ac['type']                 = ac.pop('adType')
        ac['advertiser_id']        = ac.pop('advertiserId')
        ac['campaign_id']          = ac.pop('campaignId')
        ac['creative_set_id']      = ac.pop('creativeSetId')
        ac['creative_instance_id'] = ac.pop('creativeInstanceId')
        return ac


    @cfg.check_dev
    def parse_client_json(self, dev):
        client = self.get_client_json(dev)
        return [self._parse_client_json_adcontent(x) | {'timestamp': ldap_to_timestamp(x.pop('created_at'))}
                for x in client['adsShownHistory']
                if x['ad_content']['adAction'] == 'view']


    @cfg.check_dev
    def parse_ads(self, dev, sql=False, sql_table='ad_events', sql_confirmation_type='served', force_close=False, all_camp_info=False, client_data=None):
        '''
        Major ad stats function. Parse all device ads.
        Reads from:
            client.json (faster, unreliable, safer)
            or database.sqlite (slower, reliable, sensitive).
        '''
        def get_last_ad(ads):
            # defaults
            d = {
                'campaign_id': None,
                'value':       None,
                'ptr':         None,
                'time':        cfg.day_in_sec,
                'f_time':      f'{"( - )":^7}',
            }
            if not ads:
                return d
            ads.sort(key=lambda x: int(x['timestamp']))
            last_ad = ads[-1]
            d['campaign_id'] = last_ad['campaign_id']
            d['time'] = get_last_ad_time(last_ad, False)
            d['f_time'] = get_last_ad_time(last_ad, True)
            match = [x for x in self.catalog['campaigns'] if x['campaignId'] == last_ad['campaign_id']]
            if match:
                match = match[0]
                d['value'] = float(match['creativeSets'][0]['value'])
                d['ptr']   = match['ptr']
            return d


        def get_last_ad_time(last_ad, formatted=True):
            elapsed = last_ad['timestamp']
            elapsed = cfg.now - elapsed
            if not formatted:
                return elapsed
            x = f_time(None, elapsed)
            out = f'({x:>3})'
            return f'{out:^7}'


        def filter_available_ads(at):
            res = 0
            # if at == 'nt':
            #     avail_24h = max(self.limits('nt', '24h') - len(d['nt']['24h']), 0)
            #     avail_1h  = max(self.limits('nt', '1h')  - len(d['nt']['1h'] ), 0)
            #     return min(avail_24h, avail_1h)

            for camp in self.cat.available[at]:
                # campaign_id = camp['campaign_id']
                # matches     = len( [x for x in d[at]['all'] if x.get(_campaign_id) == campaign_id] )
                # matches_24h = len( [x for x in d[at]['24h'] if x.get(_campaign_id) == campaign_id] )
                # matches_1h  = len( [x for x in d[at]['1h']  if x.get(_campaign_id) == campaign_id] )

                csids = camp['csids']
                matches     = len( [x for x in d[at]['all'] if x.get('creative_set_id') in csids] )
                matches_24h = len( [x for x in d[at]['24h'] if x.get('creative_set_id') in csids] )
                matches_1h  = len( [x for x in d[at]['1h']  if x.get('creative_set_id') in csids] )

                # max() to avoid negative number
                avail_all = max(camp['total_max'] - matches,     0)
                avail_24h = max(camp['per_day']   - matches_24h, 0)
                avail_1h  = max(camp['per_hour']  - matches_1h,  0)

                if at == 'pn':
                    available = min(avail_all, avail_24h, avail_1h, 1)
                elif at == 'nt':
                    available = min(avail_all, avail_24h)
                elif at == 'ic':
                    available = min(avail_all, avail_24h, avail_1h)

                if available or all_camp_info:
                    d[at]['bycamp'].append({
                        'advertiser_id': camp['advertiser_id'],
                        'campaign_id':   camp['campaign_id'],
                        'name':          camp['name'],
                        'value':         camp['value'],
                        'ptr':           camp['ptr'],
                        'available':     available,
                        'avail_all':     avail_all,
                        'avail_24h':     avail_24h,
                        'avail_1h':      avail_1h,
                        'matches_all':   (matches, camp['total_max']),
                        'matches_24h':   (matches_24h, camp['per_day']),
                        'matches_1h':    (matches_1h, camp['per_hour']),
                        'segments':      camp['segments']
                    })

                res += available
            res = min(res, self.limits(at, '1h'), self.limits(at, '24h'))
            return res

        self.update_catalog() if not self.catalog else ...

        ad_sql = ad_client = None
        if sql:
            ad_sql = self.parse_sql_database(dev, sql_table=sql_table, sql_confirmation_type=sql_confirmation_type, to_json=False, force_close=force_close)
        else:
            ad_client = client_data or self.parse_client_json(dev)

        d = {}
        for at in self.ad_types_alias:
            d.setdefault(at, {})

        d['ad']['all'] = ad_sql or ad_client or []
        d['pn']['all'] = [x for x in d['ad']['all'] if x['type'] == 'ad_notification']
        d['ic']['all'] = [x for x in d['ad']['all'] if x['type'] == 'inline_content_ad']
        d['nt']['all'] = [x for x in d['ad']['all'] if x['type'] == 'new_tab_page_ad']

        d['ad']['24h'] = [x for x in d['ad']['all'] if ((cfg.now - x['timestamp']) <= cfg.day_in_sec)]
        d['pn']['24h'] = [x for x in d['ad']['24h'] if x['type'] == 'ad_notification']
        d['nt']['24h'] = [x for x in d['ad']['24h'] if x['type'] == 'new_tab_page_ad']
        d['ic']['24h'] = [x for x in d['ad']['24h'] if x['type'] == 'inline_content_ad']

        d['ad']['1h'] = [x for x in d['ad']['24h'] if ((cfg.now - x['timestamp']) <= cfg.hour_in_sec)]
        d['pn']['1h'] = [x for x in d['ad']['1h']  if x['type'] == 'ad_notification']
        d['nt']['1h'] = [x for x in d['ad']['1h']  if x['type'] == 'new_tab_page_ad']
        d['ic']['1h'] = [x for x in d['ad']['1h']  if x['type'] == 'inline_content_ad']

        d['ad']['today'] = [x for x in d['ad']['24h']   if timestamp_to_date(x['timestamp']) == cfg.today]
        d['pn']['today'] = [x for x in d['ad']['today'] if x['type'] == 'ad_notification']
        d['nt']['today'] = [x for x in d['ad']['today'] if x['type'] == 'new_tab_page_ad']
        d['ic']['today'] = [x for x in d['ad']['today'] if x['type'] == 'inline_content_ad']

        d['ad']['last'] = get_last_ad(d['ad']['all'])  # ads are being sort by timestamp ascending inside this section
        d['pn']['last'] = get_last_ad(d['pn']['all'])
        d['nt']['last'] = get_last_ad(d['nt']['all'])
        d['ic']['last'] = get_last_ad(d['ic']['all'])

        # keep track of available ads to get
        for at in self.ad_types_alias:
            d[at]['available']       = 0
            d[at]['bycamp']          = []
            d[at]['color']           = 'bright_black'
            d[at]['available_color'] = 'bright_black'

        highlight_color = 'red'

        # pn track and color
        if self.cat.pn:
            # if all_camp_info or (len(d['pn']['24h']) < self.limits('pn', '24h') and get_last_ad_time(d['pn']['24h'], formatted=False) > 360):
            if all_camp_info or ( len(d['pn']['24h']) < self.limits('pn', '24h') and d['pn']['last']['time'] > 360):
                d['pn']['available'] += filter_available_ads('pn')
                if d['pn']['available']:
                    d['pn']['available_color'] = 'bright_cyan'

        # nt track and color
        if self.cat.nt and len(d['nt']['24h']) < self.limits('nt', '24h') and len(d['nt']['1h']) < self.limits('nt', '1h'):
            d['nt']['available'] = filter_available_ads('nt')
            if d['nt']['available']:
                d['nt']['color'] = d['nt']['available_color'] = highlight_color

        # ic track
        if self.cat.ic:
            if all_camp_info or (len(d['ic']['24h']) < self.limits('ic', '24h') and len(d['ic']['1h']) < self.limits('ic', '1h')):
                d['ic']['available'] += filter_available_ads('ic')
                if d['ic']['available']:
                    d['ic']['available_color'] = 'bright_cyan'

        d['ad']['available'] = d['pn']['available'] + d['nt']['available'] + d['ic']['available']

        for at in self.ad_types_alias:
            for i in ['all', '24h', '1h', 'today']:
                d[at][i] = len(d[at][i])

        return d


    @timeit
    def show_daily_ads(self, devs_code=None, sql=True, force_close=False):

        def ff(ads, pad=0):
            return f'{str(ads).zfill(pad):>4}'

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'd'
            os.system('cls')
        devs = cfg.get_devs_group(devs_code)

        self.update_catalog()

        self.show_catalog()

        self.cat = self.cat_net

        # Header
        print()
        rule('Daily Ads', characters='-', style='[white]')
        print('[white]sqlite=', sql, highlight=True, sep='')
        print(f'{" ":7}{"ALL ":^19}{"PN ":^19}{"NT":^19}{"IC ":^19}')
        print(f'{"":7}', end='')
        print(f'{"day 24h 1h (last)":^19}'*4, 'v_pn  v_ic', sep='')

        all_ad_today = 0
        all_pn_today = 0
        all_nt_today = 0
        all_ic_today = 0

        all_ad_24h = 0
        all_pn_24h = 0
        all_nt_24h = 0
        all_ic_24h = 0

        for i, dev in enumerate(devs):
            cfg.print_dev(dev)

            v_color = 'bright_white'
            v_back_color = 'black' if i%2 else 'black'
            a = self.parse_ads(dev, sql=sql, force_close=force_close)
            if not a:
                continue

            # dev results
            print(
                f"[{v_color} on {v_back_color}]{ff(a['ad']['today'])}[white]{ff(a['ad']['24h'])}{ff(a['ad']['1h'])}[bright_black]{a['ad']['last']['f_time']}"
                f"[{v_color} on {v_back_color}]{ff(a['pn']['today'])}[white]{ff(a['pn']['24h'])}{ff(a['pn']['1h'])}[bright_black]{a['pn']['last']['f_time']}"
                f"[{v_color} on {v_back_color}]{ff(a['nt']['today'])}[white]{ff(a['nt']['24h'])}{ff(a['nt']['1h'])}[{a['nt']['color']}]{a['nt']['last']['f_time']}"
                f"[{v_color} on {v_back_color}]{ff(a['ic']['today'])}[white]{ff(a['ic']['24h'])}{ff(a['ic']['1h'])}[{a['ic']['color']}]{a['ic']['last']['f_time']}"
                f"[{a['pn']['available_color']} on {v_back_color}]{a['pn']['available']:>4}[{a['ic']['available_color']}]{a['ic']['available']:>5}"
            )

            all_ad_today += a['ad']['today']
            all_pn_today += a['pn']['today']
            all_nt_today += a['nt']['today']
            all_ic_today += a['ic']['today']

            all_ad_24h += a['ad']['24h']
            all_pn_24h += a['pn']['24h']
            all_nt_24h += a['nt']['24h']
            all_ic_24h += a['ic']['24h']

        # final results
        print(
            f'{"":7}'
            f'[bright_white]{all_ad_today:>4}[white]{all_ad_24h:>4}'
            f'[bright_white]{all_pn_today:>15}[white]{all_pn_24h:>4}'
            f'[bright_white]{all_nt_today:>15}[white]{all_nt_24h:>4}'
            f'[bright_white]{all_ic_today:>15}[white]{all_ic_24h:>4}'
        )


    # CONFIRMATIONS.JSON
    @cfg.check_dev
    def payment_token_status(self, dev=None):
        from .json_transactions import Transactions

        tr = Transactions()

        path = pj(cfg.data_dir, 'tokens.json')
        dct = json_(path)
        print(f'{"":7}{"unb_pay_tokens":<15}{"failed_conf":<15}{"failed_queue":<15}{"failed_trash":<15}{"failed_click":<15}{"unb_tokens":<15}')

        all_conf = 0
        all_unbpaytok = 0
        all_unbtok = 0
        all_queue = 0
        all_trash = 0
        all_click = 0

        for data in cfg._devs_groups.values():
            name = data['name']
            devs = data['devs']

            print(f'{name} ({len(devs)})')

            if name == 'all_devs' or not devs:
                print()
                continue

            devs_conf = 0
            devs_unbpaytok = 0
            devs_unbtok = 0
            devs_queue = 0
            devs_trash = 0
            devs_click = 0

            for dev in devs:
                cfg.print_dev(dev)

                confs_json = tr.confirmations_json(dev)
                queue_json = tr.failed_json(dev, 'queue')
                trash_json = tr.failed_json(dev, 'trash')
                click_json = tr.failed_json(dev, 'click')

                conf  = len(confs_json['confirmations']['failed_confirmations'])
                unbpaytok = len(confs_json['unblinded_payment_tokens'])
                unbtok  = len(confs_json['unblinded_tokens'])
                queue_json = len(queue_json)
                trash_json = len(trash_json)
                click_json = len(click_json)

                devs_conf  += conf
                devs_unbpaytok += unbpaytok
                devs_unbtok  += unbtok
                devs_queue += queue_json
                devs_trash += trash_json
                devs_click += click_json

                all_conf  += conf
                all_unbpaytok += unbpaytok
                all_unbtok  += unbtok
                all_queue += queue_json
                all_trash += trash_json
                all_click += click_json

                dct.setdefault(dev,{})
                dct[dev].setdefault('failed_conf', {}).update({str(cfg.today): conf})
                dct[dev].setdefault('unb_pay_tok', {}).update({str(cfg.today): unbpaytok})
                dct[dev].setdefault('unb_tok',     {}).update({str(cfg.today): unbtok})
                dct[dev].setdefault('failed_queue',{}).update({str(cfg.today): queue_json})
                dct[dev].setdefault('failed_trash',{}).update({str(cfg.today): trash_json})
                dct[dev].setdefault('failed_click',{}).update({str(cfg.today): click_json})

                print(f'{self.h_color(unbpaytok, result=True)}{unbpaytok:<15}[white]{conf:<15}{queue_json:<15}{trash_json:<15}{click_json:<15}{self.unbtok_color(unbtok)}{unbtok:<15}')

            print(f'{"":7}{devs_unbpaytok:<15}{devs_conf:<15}{devs_queue:<15}{devs_trash:<15}{devs_click:<15}{devs_unbtok:<15}\n')
            saved = json_(path, dct, backup=True, indent='\t')

        print(f'{"":7}{all_unbpaytok:<15}{all_conf:<15}{all_queue:<15}{all_trash:<15}{all_click:<15}{all_unbtok:<15}\n')
        print('\n[white]Succesfully update tokens.json') if saved else ...


    def show_next_redemption(self, devs=None, sort_by_time=None, print_=True):
        from .json_preferences import Preferences
        from .json_transactions import Transactions
        from famgz_utils import timestamp_to_date, now, f_time

        global print
        if not print_:
            print = disable_print

        if sort_by_time is None:
            sort_by_time = True if input('Any key to sort by redemption time left:\n>') else False

        devs = devs or cfg.devs

        tr = Transactions()
        stats = []
        all_unbpaytok = 0
        all_unbtok = 0
        all_failed = 0
        for dev in devs:
            pf = Preferences(dev)
            time_ = pf.get_next_time_redemption_at()
            diff = max(time_ - now(), 0)

            confs_json = tr.confirmations_json(dev)
            failed    = len(confs_json['confirmations']['failed_confirmations'])
            unbpaytok = len(confs_json['unblinded_payment_tokens'])
            unbtok    = len(confs_json['unblinded_tokens'])

            all_unbpaytok += unbpaytok
            all_unbtok += unbtok
            all_failed += failed

            data = (dev, failed, unbpaytok, time_, diff, unbtok)
            stats.append(data)

        # sort by time
        if sort_by_time:
            stats.sort(key=lambda x: x[4])

        print(f'{"":<4}{"unbpaytok":<9}{"failed":<9}{"next_redemption_at":<22}{"ETA":<8}{"unbtok":<8}')
        for dev, failed, unbpaytok, time_, diff, unbtok in stats:
            date_ = str(timestamp_to_full_date(time_))
            diff = f_time(None, diff)
            color = '[white]' if unbpaytok else '[bright_black]'
            print(f'{cfg.dev_color(dev)}{cfg.fdev(dev)}{color}{unbpaytok:<9}{failed:<9}{date_:<22}{diff:<8}{self.unbtok_color(unbtok)}{unbtok:<8}')
        print(f'[bright_white]{"":4}{all_unbpaytok:<9}{all_failed:<9}')

        return stats


    def get_grants(self):
        # TODO to implement
        return


    def show_grants(self, sort_by_grants=None):
        if sort_by_grants is None:
            sort_by_grants = True if input('Any key to sort by grants values:\n>') else False

        totals = {
            'devs':    0,
            'flagged': 0,
            'claim':   0,
            'frozen':  0,
        }

        groups = {
            'devs':    [],
            'flagged': [],
            'claim':   [],
            'frozen':  [],
        }

        for group, devs in (('devs', cfg.devs), ('flagged', cfg.flagged_devs), ('claim', cfg.claim_devs), ('frozen', cfg.frozen_devs)):
            for dev in devs:
                grants = self.parse_sql_publisher_info_db(dev)
                groups[group].append( (dev, grants) )
                totals[group] += grants

        if sort_by_grants:
            for group in groups.values():
                group.sort(key=lambda x: x[1], reverse=True)

        print(f'{"devs":<12}{"flagged":<12}{"claim":<12}{"frozen":<12}')

        max_size = max( [len(x) for x in groups.values()] )

        for i in range(max_size):
            for group in groups:
                devs = groups[group]
                if i >= len(devs):
                    print(f'{"":<12}', end='')
                    continue
                dev, grants = devs[i]
                print(f'{cfg.dev_color(dev)}{cfg.fdev(dev):<4}[white]{grants:<7}', end=' ')
            print()

        print(
            f'{"":4}{totals["devs"]:<8}'
            f'{"":4}{totals["flagged"]:<8}'
            f'{"":4}{totals["claim"]:<8}'
            f'{"":4}{totals["frozen"]:<8}'
            f'{"":4}{sum( [x for x in totals.values()] )} BAT'
        )


    def update_unb_tok_refills(self, devs_code='d'):
        ''' Logs all devs unblinded tokens refills timestamps by Rewards.log '''
        from .rewards_log import ReLog

        print('[bright_black]Updating unblinded tokens refills intervals...')

        refills_path = Path(cfg.data_dir, 'refills.json')
        refills = json_(refills_path)

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'd'
            os.system('cls')

        devs = cfg.get_devs_group(devs_code) or cfg.devs

        string = 'Successfully refilled unblinded tokens'
        for dev in devs:
            rl = ReLog(dev, full=True, only_unique_lines=False)
            res = rl.search(string, include_header=True)

            refills.setdefault(dev,[])

            if not res:
                continue

            res = [int(rl._get_log_timestamp(header)) for header, msg in res]
            for t in res:
                if t not in refills[dev]:
                    refills[dev].append(t)

            refills[dev].sort()

        # sort by dev
        refills = dict(sorted(refills.items(), key=lambda x: x[0]))

        json_(refills_path, refills, backup=True, indent='\t')
        return refills


    def show_unb_tok_refills(self, sort_by_time=False):
        ''' Show device's all unblinded tokens refills intervals '''
        from .json_transactions import Transactions

        tr = Transactions()

        refills = self.update_unb_tok_refills()

        # convert timestamps into refills intervals
        now = int(cfg.now)
        for dev, timestamps in refills.items():
            timestamps.append(now)
            timestamps = list(reversed(timestamps))
            diffs = []
            for i, _ in enumerate(timestamps):
                if i == len(timestamps)-1:
                    continue
                diff = timestamps[i] - timestamps[i+1]
                diffs.append(diff)
            refills[dev] = diffs

        # sorting by max refill interval
        refills = {dev: diffs for dev, diffs in refills.items() if diffs}
        if sort_by_time:
            refills = dict(sorted(refills.items(), key=lambda x: max(x[1]), reverse=True))

        for dev, diffs in refills.items():
            if not diffs:
                continue
            cfg.print_dev(dev)
            unbtok = tr.len_unb_tokens(dev)
            print(f'{self.unbtok_color(unbtok)}{unbtok:>2}', end='  ')
            diffs = [f"({f_time(t1=None, diff=diff, out='partial2')})" for diff in diffs]
            diffs = '  '.join(diffs)
            print(f'[white]{diffs}')


    @timeit
    def run_low_unb_tokens_devs(self, devs_code=None, chunk_size=10, persists=True, cycle_interval=5, monitor_interval=2, max_chunk_duration=2):
        ''' Attemps to refill low unblinded token devices by running it '''
        from .json_transactions import Transactions
        from .controls import ct
        from .rewards_log import ReLog
        from famgz_utils import countdown

        def get_unbtok_devs():
            devs = []
            for dev in all_devs:
                unb_tok = get_unb_tok(dev)
                if unb_tok < 20:
                    devs.append(dev)
                    stats[dev] = {
                        'ini': unb_tok
                    }
            return devs

        def print_header():
            print(
                '\n'
                f'{len(low_unbtok_devs)} devs to refill unblinded tokens:\n'
                f'[white]{" ".join(low_unbtok_devs)}\n'
            )

        def run_chunk():
            print(
                f'[white]Running {len(devs_chunk)} devs chunk for max {f_time(None, max_chunk_duration)}:\n'
                f'[bright_black]{" ".join(devs_chunk)}'
            )
            for dev in devs_chunk:
                ct.run_brave(dev)
                sleep(1)

        def monitor_chunk():
            devs = devs_chunk[:]
            time_ini = cfg.now
            while True:
                for dev in devs:
                    if get_unb_tok(dev) >= 20:
                        devs.remove(dev)
                        continue
                    rl = ReLog(dev, full=False, only_bracket_lines=False, only_unique_lines=False)
                    if rl.search(err_string):
                        # print(f'found on {dev}')
                        devs.remove(dev)
                if not devs:
                    break
                if cfg.now - time_ini > max_chunk_duration:
                    break
                sleep(monitor_interval)

        def print_results():
            for dev in devs_chunk:
                cfg.print_dev(dev)
                unbtok_ini = stats[dev]['ini']
                color = '[white]' if unbtok_ini < 20 else '[bright_black]'
                print(f'{color}{unbtok_ini:>2}', end='')

                last_refill = refills.get(dev) or ''
                if last_refill:
                    last_refill = cfg.now - refills[dev][-1]
                    last_refill = f_time(t1=None, diff=last_refill, out='partial2')

                unb_tok = get_unb_tok(dev)
                color = '[bright_cyan]' if unb_tok > unbtok_ini else '[white]'
                print(f'[white] -> {color}{unb_tok:>2} ({last_refill})')


        get_unb_tok = lambda dev: tr.len_unb_tokens(dev)
        color = lambda unb_tok: self.unbtok_color(unb_tok)

        if devs_code is None:
            cfg._show_devs_menu()
            devs_code = input('>')
            devs_code = devs_code or 'd'
            os.system('cls')
        all_devs = cfg.get_devs_group(devs_code)

        tr = Transactions()

        stats = {}

        chunk_size = min(chunk_size, 10)  # devs
        cycle_interval = min(cycle_interval, 10) * 60  # minutes
        monitor_interval = min(monitor_interval, 10)  # seconds
        max_chunk_duration = max(max_chunk_duration, 2) * 60  # minutes

        err_string = '{"error":"Number of allowed tokens exceeded","statusCode":429}'

        while True:
            time_ini = cfg.now

            low_unbtok_devs = get_unbtok_devs()

            if not low_unbtok_devs:
                return

            refills = self.update_unb_tok_refills(devs_code=devs_code)

            print_header()

            while low_unbtok_devs:
                devs_chunk = low_unbtok_devs[:chunk_size]
                low_unbtok_devs = low_unbtok_devs[chunk_size:]

                run_chunk()

                monitor_chunk()

                ct.kill(len(devs_chunk))

                print_results()

            print(f'[bright_black]elapsed {f_time(time_ini)}')

            if not persists:
                return

            countdown(cycle_interval)


    def show(self, mode, day_range=10):
        while True:
            os.system('cls')
            print()

            if mode == 'today':
                self.show_daily_ads()

            elif mode == 'full':
                self.show_full_ads_from_transactions_sql(day_range=day_range)

            elif mode == 'camps':
                self.show_campaigns_stats()

            elif mode == 'tokens':
                self.payment_token_status()

            elif mode == 'unb-tok-refills':
                self.show_unb_tok_refills()

            elif mode == 'redeem':
                self.show_next_redemption()

            elif mode == 'grants':
                self.show_grants()

            if input('\n[white]\[Empty to refresh. Any key to exit]\n>'):
                break


ads = Ads()
