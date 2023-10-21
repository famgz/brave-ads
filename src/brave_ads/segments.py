import os
from famgz_utils import print, json_, log_txt, site_is_up
from os.path import join as pj
from random import choice

from .config import cfg


class Urls:
    msg = 'Classified text with the top segment as '

    def __init__(self):
        self.urls_json_path = pj(cfg.config_dir, 'urls.json')
        self.urls_json = self.load_urls_json()
        self.all_urls = self.fetch_urls()
        self.default_par_segs = ('crypto', 'technology & computing')
        self.default_urls = self.fetch_urls(par=self.default_par_segs)

    def load_urls_json(self):
        return json_(self.urls_json_path)

    def fetch_urls(self, par: list = None, chi: list = None):
        links = []
        par = [par] if par and isinstance(par, str) else par
        chi = [chi] if chi and isinstance(par, str) else chi
        for parent, children in self.urls_json.items():
            if par and parent not in par:
                continue
            for child, urls in children.items():
                if chi and child not in chi:
                    continue
                for url in urls:
                    if url not in links:
                        links.append(url)
        return sorted(links)

    @property
    def rand_url(self):
        return choice(self.all_urls)

    @property
    def def_url(self):
        return choice(self.default_urls)


class Segments(Urls):

    def __init__(self, parsed_ads={}, debug=False, filter_urls=True):
        '''
        `parsed_ads` is the data returned from
        gooz.brave_dev.ads.parse_ads() function.
        '''
        super().__init__()
        self.ads = parsed_ads
        self.debug = debug
        self.filter_urls = filter_urls
        self.all_segments = self.load_all_existing_segments()
        self.segs_scored = self.score_segments(self.ads)
        self.segs_index = 0
        self.find_append_matches_urls()
        self.matches_urls = self.filter_matches_urls()
        self.fallback_to_def = False  # flag to alternate between def_url and rand_url as fallback

        if self.debug:
            print('\nALL SEGMENTS SCORED')
            print(self.segs_scored, highlight=True)
            print('\nFILTERED SEGMENTS SCORED')
            print(self.matches_urls, highlight=True)

    def fallback(self):
        self.fallback_to_def = not self.fallback_to_def
        return self.def_url if self.fallback_to_def else self.rand_url

    def pick(self):
        if not self.matches_urls:
            return self.fallback()
        if self.segs_index >= len(self.matches_urls):
            self.segs_index = 0
        urls = [data['urls'] for data in self.matches_urls[self.segs_index].values()][0]
        self.segs_index += 1
        url = choice(urls)
        if self.debug:
            print('PICKED:', url)
        return url

    def split_segment(self, seg):
        '''
        Separate and parse parent/child segments.
        Missing child will be fallback to parent.
        Note: cannot use split() directly because there might be segments
        with multi-hyphen text like "Hobbies & Interests-sci-fi".
        EDIT: "sci-fi" is actually the only exception, but let's move on
        '''
        seg = seg.strip().strip('-').lower()
        if '-' in seg:
            i = seg.index('-')
            parent = seg[:i]
            child  = seg[i+1:]
        else:
            parent = child = seg
        return parent, child

    def load_all_existing_segments(self):
        '''
        Load all existing segments found on `feibnmjhecfbjpeciancnchbmlobenjn.json`
        '''
        path = pj(cfg.config_dir, 'all_segments.json')
        return json_(path)

    def filter_matches_urls(self):
        # working with lists for better slicing/indexing
        no_low_ptr_urls   = [{seg: data} for seg, data in self.segs_scored.items() if data['urls'] and not [pt for pt in data['ptrs'] if pt <= 0.1]]
        all_urls          = [{seg: data} for seg, data in self.segs_scored.items() if data['urls']]
        return no_low_ptr_urls or all_urls if self.filter_urls else all_urls

    def warn_no_url_segments(self, seg):
        '''
        Log campaigns missing matching urls.
        '''
        path = pj(cfg.data_dir, 'empty_segments.json')
        data = json_(path) or {}
        data.setdefault(seg, [])
        for camp_id in self.segs_scored[seg]['camps']:
            if camp_id not in data[seg]:
                data[seg].append(camp_id)
        json_(path, data, sort_keys=True, indent='\t', backup=True)

    def find_append_matches_urls(self):
        '''
        Append matching urls to segments if exists.
        '''
        for seg in self.segs_scored:
            parent, child = self.split_segment(seg)
            child = None if child == parent else child
            urls = self.fetch_urls(par=parent, chi=child)
            self.segs_scored[seg]['urls'] = urls
            if not urls:
                self.warn_no_url_segments(seg)

    def validate_segment(self, seg):
        seg = f'{seg}-{seg}' if '-' not in seg else seg
        return seg in self.all_segments

    def score_segments(self, parsed_ads):
        '''
        Receives device data from Ads.parse_ads()
        and assigns points to each segment based
        on its value*occurrence.
        Currently only working with `pn` ad type.
        '''
        segs = {}
        for camp in parsed_ads.get('pn',{}).get('bycamp',{}):
            value = camp['value']
            ptr   = camp['ptr']
            camps = camp['campaign_id']
            for seg in camp['segments']:
                if seg == 'untargeted' or not self.validate_segment(seg):
                    continue
                segs.setdefault(seg, {'val':0, 'qty':0, 'ptrs':[], 'camps':[]})
                segs[seg]['val'  ] += value
                segs[seg]['qty'  ] += 1
                segs[seg]['ptrs' ].append(ptr)
                segs[seg]['camps'].append(camps)
        # sort by total value; TODO: find a way to sort by total value and total qty?
        segs = dict(sorted(segs.items(), key=lambda x: x[1]['val'], reverse=True))
        # round value's decimal places
        for x in segs.values():
            x['val'] = round(x['val'], 3)
        return segs

    def log_url_segment(self):
        '''
        Log Url and its Segments on urls.json by manual input.
        Must open url in browser and monitor its segments on Rewards Internals > Logs.
        Next version to be automated with rewards_log.py asssist.
        '''
        def clean_url(url):
            return url
            url = url.replace('www.', '')
            url = url.replace('http://', '')
            url = 'https://' + url if not url.startswith('https://') else url
            return url

        def is_url_logged(url):
            for parent, children in self.urls_json.items():
                for child, urls in children.items():
                    if url in urls:
                        print('\n[red]Url already logged as:')
                        print({parent: {child:[url]}}, highlight=True)
                        return True

        while True:
            url = input('\nInput url. Empty to finish:\n>').lower().strip()
            if not url:
                break

            os.system('cls')

            url = clean_url(url)
            print(f'\n[blue]{url}')

            if is_url_logged(url):
                continue

            # if not site_is_up(url):
            #     print('[red]Url is unavailable, please check.')
            #     continue

            print('url OK')

            seg = input('\nInput segment:\n>').lower().strip()

            if seg not in self.all_segments:
                print('[red]Invalid segment. Please recheck')
                continue

            parent, child = self.split_segment(seg)
            print(f'[bright_cyan]{parent}')
            print(f'[bright_cyan]{child}')

            data = self.load_urls_json()
            data.setdefault(parent,{}).setdefault(child,[]).append(url)
            json_(self.urls_json_path, data, indent='\t', backup=True, sort_keys=True)
            print('\nSuccesfully logged:')
            print({parent: {child:[url]}}, highlight=True)


u = Urls()


"""
def extract_segment(text):
    msg = 'Classified text with the top segment as '
    return text[text.find(msg)+len(msg):].strip()


def get_urls_segments():

    def clean_log():
        with open(log_path, 'w', encoding='utf-8') as f:
            f.truncate()

    from .farmer import run_brave
    urls = json_(urls_path)
    log_path = cfg.dirs(1,2, 'default', 'Rewards.log')
    run_brave(1,2,'')
    sleep(5)

    for url, segments in urls.items():
        print(url, segments)
        # log_txt(log_path, ' ')  # truncate
        clean_log()
        run_brave(1,2,url)
        sleep(5)
        log = log_txt(log_path)
        seg = [x for x in log if x.startswith('[') and msg in x]
        print(seg)
        if seg:
            seg = seg[0]
            seg = extract_segment(seg)
            print(seg)
            if seg not in urls[url]:
                urls[url].append(seg)
        sleep(1)
        # input('...')
        # json_(urls_path, urls, indent=2, sort_keys=True)


def get_all_catalog_segs():
    segs = set()
    data = json_(pj(cfg.data_dir, 'campaigns.json'))
    for camp in data['campaigns']:
        for cs in camp['creativeSets']:
            for sg in cs['segments']:
                name = sg['name']
                segs.add(name)
    segs = list(segs)
    segs.sort(key=str.casefold)
    json_(pj(cfg.source_dir, 'segments.json'), segs, indent=2)
    print(segs)


def sort_urls_json_by_segments():
    '''
    Disposable single run function to sort old urls.json by segments.
    '''
    file = json_('urls.json')
    d = {}
    for url, segs in file.items():
        for seg in segs:
            parent, child = split_segment(seg)
            d.setdefault(parent, {}).setdefault(child, []).append(url)
    print(d)
    json_('urls2.json', d, indent='\t', sort_keys=True)
"""
