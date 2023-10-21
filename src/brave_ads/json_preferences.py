from famgz_utils import ldap_to_timestamp

from .config import cfg
from .json__ import JsonManager


class Preferences(JsonManager):

    def __init__(self, dev, print_=True):
        super().__init__(dev, print_, 'default', 'Preferences')
        global print
        print = self._enable_print() if print_ else self._disable_print()

    @classmethod
    def all_(cls, func, *params):
        JsonManager._all(cls, func, *params)

    '''GETTERS'''
    def get_wallet_id(self):
        import json
        data = self._read_key(None, 'brave', 'rewards', 'wallets', 'brave')
        # response is json as string; needs to loads then
        data = json.loads(data) if data else {}
        assert isinstance(data, dict)
        # print(data)
        return data

    def get_next_time_redemption_at(self):
        data = self._read_key(None, 'brave', 'brave_ads', 'rewards', 'next_time_redemption_at')
        data = data or cfg.now  # new devs may have no redemption time yet
        data = int(data)
        if len(str(data)) == 17:
            data = ldap_to_timestamp(data)
        return int(data)

    '''SETTERS'''
    def rewards(self, enable:bool):
        ''' WARNING: don't use this on fresh devices, it causes "invalid wallet" flagging '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'brave_ads', 'enabled')
        self._edit_key(value, 'brave', 'rewards', 'enabled')

    def news(self, enable:bool):
        ''' Apply it after manually enabling rewards only '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'new_tab_page', 'show_brave_today')
        self._edit_key(value, 'brave', 'today', 'opted_in')

    def ntp_background_color(self, color=None):
        ''' Change new tab page background to solid black '''
        color = color or "#000000"
        value = {
            "random": False,
            "selected_value": color,
            "type": "color"
        }
        self._edit_key(value, 'brave', 'new_tab_page', 'background')

    def bookmarks_bar(self, enable:bool):
        ''' Show bookmarks '''
        value = True if enable else False
        self._edit_key(value, 'bookmark_bar', 'show_on_all_tabs')

    def clear_cache_on_exit(self, enable:bool):
        value = True if enable else False
        self._edit_key(value, 'browser', 'clear_data', 'cache_on_exit')

    def restore_browser_window(self, scale=None):
        '''
        Set Brave window dimensions to "restore" mode
        Currently only works with 1080p displays
        '''
        scale = scale or cfg.config_json['windows_display_scale']
        assert scale in (100, 125)

        wp = self.prefs['browser']['window_placement']

        if scale == 100:
            wp['maximized']        = False
            wp['bottom']           = 1047
            wp['left']             = 429
            wp['right']            = 1927
            wp['top']              = 0
            wp['work_area_bottom'] = 1040
            wp['work_area_left']   = 0
            wp['work_area_right']  = 1920
            wp['work_area_top']    = 0

        elif scale == 125:
            wp['maximized']        = False
            wp['bottom']           = 824
            wp['left']             = 329
            wp['right']            = 1536
            wp['top']              = 0
            wp['work_area_bottom'] = 824
            wp['work_area_left']   = 0
            wp['work_area_right']  = 1536
            wp['work_area_top']    = 0

    def javascript(self, enable:bool):
        value = self.null if enable else 2
        self._edit_key(value, 'profile', 'default_content_setting_values', 'javascript')

    def images(self, enable:bool):
        value = self.null if enable else 2
        self._edit_key(value, 'profile', 'default_content_setting_values', 'images')

    def cookies(self, enable:bool):
        value = 1 if enable else 2
        self._edit_key(value, 'profile', 'default_content_setting_values', 'cookies')

    def exit_type_normal(self):
        self._edit_key('Normal', 'profile', 'exit_type')
        self._edit_key(3, 'sessions', 'session_data_status')

    def translate(self, enable:bool):
        value = True if enable else False
        self._edit_key(value, 'translate', 'enabled')

    def ads_per_hour(self):
        ''' Set Max Ads per hour '''
        value = "10"
        self._edit_key(value, 'brave', 'brave_ads', 'ads_per_hour')

    def auto_contribute(self, enable:bool):
        ''' Disable Rewards Auto-Contribute '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'rewards', 'ac', 'enabled')

    def social_media_blocking(self, enable:bool):
        ''' Social media blocking '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'fb_embed_default')
        self._edit_key(value, 'brave', 'google_login_default')
        self._edit_key(value, 'brave', 'twitter_embed_default')

    def hangouts(self, enable:bool):
        '''
        Extension > Hangouts
        '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'hangouts_enabled')

    def webtorrent(self, enable:bool):
        ''' Extension > WebTorrent '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'webtorrent_enabled')

    def wallet_icon(self, enable:bool):
        ''' Show Brave Wallet icon on toolbar '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'wallet', 'show_wallet_icon_on_toolbar')

    def confirm_close_tabs(self, enable:bool):
        ''' Display confirmation box when closing Brave with multiple tabs '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'enable_window_closing_confirm')

    def shields_stats_badge_visible(self, enable:bool):
        ''' Show the number of blocked items on the Shields icon '''
        value = True if enable else False
        self._edit_key(value, 'shields', 'stats_badge_visible')
        self._edit_key(value, 'brave', 'shields', 'stats_badge_visible')

    def shields_aggressive(self, enable:bool):
        ''' Settings > Shields > Trackers & ads blocking '''
        value = {"*,*": { "expiration": "0", "last_modified": "13305684722138906", "model": 0, "setting": 2 }} if enable else {}
        self._edit_key(value, 'profile', 'content_settings', 'exceptions', 'shieldsAds')
        self._edit_key(value, 'profile', 'content_settings', 'exceptions', 'trackers')
        self._edit_key(value, 'profile', 'content_settings', 'exceptions', 'cosmeticFiltering')

    def spellchecking(self, enable:bool):
        ''' Settings > Languages > Spell Check '''
        value = True if enable else False
        self._edit_key(value, 'browser', 'enable_spellchecking')
        self._edit_key(value, 'spellcheck', 'use_spelling_service')

    def welcome_page(self, enable:bool):
        ''' First run welcome page dismiss '''
        value = True if enable else False
        self._edit_key(value, 'browser', 'has_seen_welcome_page')

    def dismiss_wallpaper_notification(self, enable:bool):
        ''' Dismiss card that appears when earn nt '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'branded_wallpaper_notification_dismissed')

    def zoom_ntp_out(self, percent:int = 50):
        '''
        Zoom New Tab Page out to facilitate visualizing Inline Content Ads.
        Available zoom "percent": 25, 33, 50, 67, 75, 80, 90, 100, 110
        '''
        d = {
            110 :  0.5227586988632231,
            100 :  0,  # browser will delete the key after session
            90  : -0.5778829311823857,
            80  : -1.2239010857415447,
            75  : -1.5778829311823859,
            67  : -2.2239010857415455,
            50  : -3.8017840169239308,
            33  : -6.025685102665476,
            25  : -7.6035680338478615,
        }
        value = d[percent]
        timestamp = '13298243314180364'
        self._edit_key(value,     'partition', 'per_host_zoom_levels', 'x', 'newtab', 'zoom_level')
        self._edit_key(timestamp, 'partition', 'per_host_zoom_levels', 'x', 'newtab', 'last_modified')

    def next_time_redemption_at(self, timestamp=None):
        ''' Change scheduled redemption time '''
        timestamp = timestamp or cfg.now
        self._edit_key(timestamp, 'brave', 'brave_ads', 'rewards', 'next_time_redemption_at')

    def check_next_time_redemption_at(self):
        redemption_time = self.get_next_time_redemption_at()
        diff = max(redemption_time - cfg.now, 0)
        if diff > 0:
            self.next_time_redemption_at()
            print(f'[white]{self.dev} redemption time changed to now!')
        return
        from famgz_utils import timestamp_to_full_date, month
        redemption_time = self.get_next_time_redemption_at()
        redemption_month = timestamp_to_full_date(redemption_time).month
        if redemption_month != month():
            self.next_time_redemption_at()
            print(f'[white]{self.dev} -> current month: {month()}; redemption month: {redemption_month}; changed!')
