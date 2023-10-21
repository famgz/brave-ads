import os
import requests
import traceback
from copy import deepcopy
from famgz_utils import print, input, json_, countdown
from pathlib import Path
from random import choice, shuffle
from time import sleep
from types import SimpleNamespace

from .json_preferences import Preferences
from .config import cfg
from .ads import ads
from .controls import ct

N_MAX_VIDEOS_PER_DEV = 7
N_MAX_DEVS = 1
MAX_WAIT = 5  # minutes

m = SimpleNamespace()  # manager
m.videos = None
m.devs = deepcopy(cfg.flagged_devs + cfg.frozen_devs)
shuffle(m.devs)


'''LEDGER'''
def tip(devs_code=None):
    ''' Manage devs contributions and run them to manually tip '''
    def print_tips_history():
        tips = {}
        total = 0
        for dates in ledger.values():
            for date, values in dates.items():
                tips.setdefault(date, 0)
                values = sum(values)
                tips[date] += values
                total += values
        print('Net contributions by month (-5% fee):')
        for date, value in tips.items():
            value *= 0.95
            value = round(value, 2)
            print(f'{date:<7} {value:>6} BAT')
        print(f'Total   {total:>6} BAT\n')

    # config
    if devs_code is None:
        cfg._show_devs_menu()
        devs_code = input('>')
        devs_code = devs_code or 'd'
        os.system('cls')
    devs = cfg.get_devs_group(devs_code) or cfg.devs

    from famgz_utils import year, month
    date = f'{year()}-{month()}'
    tips_range = [round(x*0.25, 2) for x in range(4,40)]  # 1.0 - 9.75
    ledger = cfg.creators_json['ledger']

    dev_tip_month = lambda dev: sum(ledger.get(dev,{}).get(date,[]))
    dev_grants = lambda dev: ads.parse_sql_publisher_info_db(dev)

    # selecting devs
    grants_all = {dev: dev_grants(dev) for dev in devs}
    grants_net = {dev: grants for dev, grants in grants_all.items() if grants}
    tips_all = {}
    tips_this_month = {dev: (grants, dev_tip_month(dev)) for dev, grants in grants_net.items()}
    tips_this_month = dict(sorted(tips_this_month.items(), key=lambda x: x[1][1]))  # sorting by tips ascending

    # running
    urls = cfg.config_json['creators']
    if not urls:
        print('[yellow]No creators urls. Exiting')
        return
    for dev, (grants, tipped) in tips_this_month.items():
        os.system('cls')
        print_tips_history()
        random_tip = min(choice(tips_range), grants)
        print(f'[bright_black]Dev {cfg.format_dev(dev, pad=0, dev_index=False)}[bright_black] has [white]{grants} BAT[bright_black] and tipped [white]{tipped}[bright_black] this month')
        print(f'[white]Random suggestion value: [bright_white]{random_tip} BAT')
        if input('[white]Enter to continue. Any key to pass\n>'):
            continue
        with Preferences(dev, print_=False) as pf:
            pf.javascript(True)
            pf.images(True)
            pf.restore_browser_window()
        grants_ini = dev_grants(dev)
        url = choice(urls)
        ct.run_brave(dev, url=url)
        sleep(3)
        input('[white]Done? Enter to continue\n>')
        grants_fin = dev_grants(dev)
        diff = grants_ini - grants_fin
        if not diff:
            input('[white]No tip was given\nEnter to continue\n>')
            continue
        ledger.setdefault(dev,{}).setdefault(date,[])
        ledger[dev][date].append(diff)
        print(f'[white]Succesfully logged [bright_white]{diff}[white] BAT on dev [bright_white]{dev}\n')
        # print(ledger)
        cfg.creators_json['ledger'] = dict(sorted(ledger.items()))
        cfg.update_json('creators')
        sleep(3)


''' YOUTUBE '''
def is_youtube_url(url):
    return 'youtube.com' in url


def youtube_channel_id_from_channel_name(channel_id):
    cookies = {'ezoadgid_186623': '-1', 'ezoref_186623': 'google.com', 'ezosuibasgeneris-1': 'a9f02360-6c64-4258-5abe-4be36c83e158', 'ezoab_186623': 'mod1-c', 'ezovid_186623': '1940031790', 'lp_186623': 'https://commentpicker.com/youtube-channel-id.php', 'ezovuuid_186623': '5cb59b7f-8427-4112-7eab-cdfed611d83f', 'ezds': 'ffid%3D1%2Cw%3D1920%2Ch%3D1080', 'ezohw': 'w%3D1920%2Ch%3D941', 'ezouspvv': '0', 'ezouspva': '0', 'fontsLoaded': 'true', 'PHPSESSID': 'ilqsov28r1jlv7n7rtfgvodqsd', 'ezux_ifep_186623': 'true', 'active_template::186623': 'pub_site.1663004054', 'ezopvc_186623': '3', 'ezepvv': '1126', 'ezovuuidtime_186623': '1663004055', 'ezux_lpl_186623': '1663003949780|1bbc4bee-4c7e-4db2-5378-32c07c9bd786|false', 'ezux_et_186623': '5', 'ezux_tos_186623': '136'}
    headers = {'authority': 'commentpicker.com', 'accept': '*/*', 'accept-language': 'en-US,en;q=0.9', 'referer': 'https://commentpicker.com/youtube-channel-id.php', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin', 'sec-gpc': '1', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36'}
    params = {
        'url': f'https://www.googleapis.com/youtube/v3/search?part=id,snippet&type=channel&q={channel_id}',
        'token': 'addd52c6a9055fad3c2169c0407c2eb9118ca5fd59fbba0958b98f63c4cba6d8',
    }
    r = requests.get('https://commentpicker.com/actions/youtube-channel-id.php', params=params, cookies=cookies, headers=headers)
    rj = r.json()
    channel_id = rj['items'][0]['id']['channelId']
    return channel_id


def youtube_url_to_channel_id(url):
    parts = url.split('/')
    divisor = 'channel' if 'youtube.com/channel/' in url else 'c'
    try:
        channel_id = parts[parts.index(divisor)+1]
    except IndexError:
        return None
    if divisor == 'c':
        channel_id = youtube_channel_id_from_channel_name(channel_id)
    return channel_id


def youtube_convert_duration(thumbnailOverlays):
    simpleText = [v['text']['simpleText'] for to in thumbnailOverlays for k,v in to.items() if k == 'thumbnailOverlayTimeStatusRenderer']
    simpleText = simpleText[0].strip()
    parts = [int(x) for x in reversed(simpleText.split(':'))] + [0,0,0]
    s, m, h, *_ = parts + [0,0,0]
    timestamp = s + (m*60) + (h*60*60)
    return timestamp


def get_youtube_links(url):
    channel_id = youtube_url_to_channel_id(url)
    if not channel_id:
        print('[white]No youtube channel id found')
        return

    import scrapetube
    videos = scrapetube.get_channel(channel_id=channel_id)

    # json_('C:/asd/youtube_videos.json', list(videos), indent='\t')

    videos = [
        {
            'name':     x['title']['runs'][0]['text'],
            'url':      'https://www.youtube.com/watch?v=' + x['videoId'],
            'duration': youtube_convert_duration(x['thumbnailOverlays'])
        }
        for x in videos
    ]
    return videos


''' VIMEO '''
def is_vimeo_url(url):
    return 'vimeo.com' in url


def vimeo_url_to_userid(url):
    user = [x for x in url.split('/') if x.startswith('user') and x.isalnum()]
    return user[0] if user else None


def vimeo_videoid_to_url(id):
    id = id.split('/')[-1]
    return f'https://player.vimeo.com/video/{id}?autopause=false'


def get_vimeo_jwt():
    cookies = { 'language': 'en', 'vuid': 'pl382127052.1804092257', 'vimeo_cart': '%7B%22stock%22%3A%7B%22store%22%3A%22stock%22%2C%22version%22%3A1%2C%22quantities%22%3A%5B%5D%2C%22items%22%3A%5B%5D%2C%22attributes%22%3A%5B%5D%2C%22currency%22%3A%22BRL%22%2C%22items_sorted_by_index%22%3A%5B%5D%2C%22items_count%22%3A0%7D%7D', 'has_logged_in': '1', 'is_logged_in': '1', 'has_uploaded': '1', 'player': '"volume=0"', '_abexps': '%7B%22202%22%3A%22yes%22%2C%221057%22%3A%22false%22%2C%222540%22%3A%22variant%22%2C%222573%22%3A%22variant%22%7D', 'notification_storage_limit_alert': '1662835455', 'vimeo': 'OHLZPtSSetdMVHLXXDtLPXSdMxHcL4ZBD%2C4DcLecNtDaeNScLdtB3eeDPD3PBd4tXDLMiwiViN5_59biw_ViY3HLXXDtLP4eeM5i_Ic9j3H9ubNwizNVi9wMIH44L4eaDt%2CNBXtS4dd3eXSXXBtSZXe%2CSBL4XdtNNP%2Cd4dBt4c%2CcPeP%2CdZDcSXLDPD', 'clips': '748353012%2C748344029%2C748320879%2C748318866%2C748317363', '__cf_bm': 'qWOUSbdEaaquizzCQhMmoOFFL5raHVCCca.JHJTPWOQ-1662851159-0-AbiJUXOEgD4cKiuYKdCsE0zw8MLXKJdxXnySHj7L9x3e9xZKNa1uEmiikkTiR2cm6VkIgxQg0kutdwN85BZ27yg=', 'OptanonConsent': 'isGpcEnabled=1&datestamp=Sat+Sep+10+2022+20%3A04%3A28+GMT-0300+(Brasilia+Standard+Time)&version=6.29.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A0&AwaitingReconsent=false', '_abexps': '%7B%22202%22%3A%22yes%22%2C%221057%22%3A%22false%22%2C%222540%22%3A%22variant%22%2C%222573%22%3A%22variant%22%7D', }
    headers = { 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'keep-alive', 'Referer': 'https://vimeo.com/user179833584', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-origin', 'Sec-GPC': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36', 'newrelic': 'eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjM5Mjg0IiwiYXAiOiI3NDQ3NDY4IiwiaWQiOiIxYTcxNWE3MmUyYzFjYzAzIiwidHIiOiJkMDIxZGZmNmZlNmZiY2ZkNzg1YzZiM2NkNjVlMTk0MCIsInRpIjoxNjYyODUxMDc1MTU1fX0=', 'traceparent': '00-d021dff6fe6fbcfd785c6b3cd65e1940-1a715a72e2c1cc03-01', 'tracestate': '39284@nr=0-1-39284-7447468-1a715a72e2c1cc03----1662851075155', 'x-requested-with': 'XMLHttpRequest', }
    r = requests.get('https://vimeo.com/_next/jwt', cookies=cookies, headers=headers)
    rj = r.json()
    return rj['token']


def get_vimeo_links(url):
    userid = vimeo_url_to_userid(url)
    if not userid:
        print('[white]No vimeo userid found')
        return

    token = get_vimeo_jwt()

    headers = { 'Accept': 'application/vnd.vimeo.*; version=3.4.2', 'Accept-Language': 'en', 'Authorization': f'jwt {token}', 'Connection': 'keep-alive', 'Content-Type': 'application/json', 'Origin': 'https://vimeo.com', 'Referer': 'https://vimeo.com/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-GPC': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36', }
    # params = { 'autopause': '0', 'autoplay': '0', 'controls': '1', 'like': '1', 'logo': '1', 'loop': '0', 'share': '1', 'watch_later': '1', 'info_on_pause': '1', 'badge': '1', 'playbar': '1', 'default_to_hd': '1', 'volume': '1', 'include_videos': '1', 'fields': 'uri,title,userUri,uri,unbounded,position,clip_uris,videos.total,videos.data.video_details,videos.data.profile_section_uri,videos.data.is_staff_pick,videos.data.show_featured_comment,videos.data.featured_comment,videos.data.column_width,videos.data.clip.uri,videos.data.clip.name,videos.data.clip.type,videos.data.clip.categories.name,videos.data.clip.categories.uri,videos.data.clip.config_url,videos.data.clip.pictures,videos.data.clip.height,videos.data.clip.width,videos.data.clip.duration,videos.data.clip.description,videos.data.clip.created_time,videos.data.clip.user.uri,videos.data.clip.user.name,videos.data.clip.user.link,videos.data.clip.user.location,videos.data.clip.user.bio,videos.data.clip.user.membership.badge,videos.data.clip.user.skills,videos.data.clip.user.background_video,videos.data.clip.user.available_for_hire,videos.data.clip.user.pictures.sizes,videos.data.clip.user.is_expert,videos.data.clip.badge.type,videos.data.clip.metadata.connections.comments.total,videos.data.clip.live.scheduled_start_time,videos.data.clip.live.status,videos.data.clip.content_rating', 'videos_count_per_section': '10', 'page': '1', 'per_page': '4', }
    params = {'videos_count_per_section': '10', 'page': '1', 'per_page': '50'}
    # r = requests.get(f'https://api.vimeo.com/users/{userid}/profile_sections', params=params, headers=headers)
    r = requests.get(f'https://api.vimeo.com/users/{userid}/videos', params=params, headers=headers)
    videos = r.json()
    videos = [
        {
            'name':     str(x['name']),
            'url':      vimeo_videoid_to_url(x['uri']),
            'duration': max(int(x['duration']) + 1, 0)  # for some reason vimeo subtracts 1 second
        }
        for x in videos['data'] if x['type'] == 'video'
    ]
    json_('C:/asd/vimeo_videos.json', videos, indent='\t')
    return videos


''' VISIT '''
def get_videos_to_visit():
    if m.videos:
        return
    m.videos = [x for data in cfg.creators_json['channels'].values() for x in data]


def configure_devs():
    for dev in m.devs:
        with Preferences(dev, print_=False) as pf:
            pf.restore_browser_window()
            pf.confirm_close_tabs(False)
            pf.images(True)
            pf.javascript(True)
            pf.cookies(True)
            pf.exit_type_normal()


def update_creators_links():
    try:
        for creator_url in cfg.config_json['creators']:
            videos = None
            if is_vimeo_url(creator_url):
                videos = get_vimeo_links(creator_url)
            elif is_youtube_url(creator_url):
                videos = get_youtube_links(creator_url)
            if not videos:
                continue
            cfg.creators_json['channels'][creator_url] = videos
        # return
        cfg.update_json('creators')
    except:
        print(f'[red]Unable to get creators link: {traceback.format_exc()}')


def select_duration(videos):
    duration = max( [x['duration'] for x in videos] )
    duration = min(duration, MAX_WAIT * 60)  # max 5 minutes
    return duration


def select_videos():
    videos = deepcopy(m.videos)
    shuffle(videos)
    videos = videos[:N_MAX_VIDEOS_PER_DEV]
    return videos


def visit_videos():
    cfg.close_brave()
    devs = m.devs[:N_MAX_DEVS]
    videos = select_videos()
    duration = select_duration(videos)
    for dev in devs:
        cfg.print_dev(dev, end='\n')
        for i, video in enumerate(videos):
            url = video['url']
            ct.run_brave(dev, url)
            sleep(3)
            # press space to play video if vimeo
            if is_vimeo_url(url):
                ct.press('space')
                sleep(0.25)
    countdown(duration)
    print(" "*20)
    ct.kill(n=len(devs))
    for dev in devs:
        m.devs.remove(dev)


def main():
    print('Getting creators links')
    update_creators_links()
    get_videos_to_visit()
    if not m.videos:
        print('No video urls to visit')
        return
    print('Configuring devs')
    configure_devs()
    sleep(10)
    while True:
        if not m.devs:
            m.devs = deepcopy(cfg.all_devs)
            shuffle(m.devs)
        visit_videos()
