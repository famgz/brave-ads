from .json__ import JsonManager


class LocalState(JsonManager):

    def __init__(self, dev, print_=True):
        super().__init__(dev, print_, 'user_data', 'Local State')
        global print
        print = self._enable_print() if print_ else self._disable_print()

    @classmethod
    def all_(cls, func, *params):
        JsonManager._all(cls, func, *params)

    '''SETTERS'''
    def flags(self, enable:bool):
        '''
        Enable BraveRewardsVerboseLogging
        Enable CustomAdNotifications
        Enable BraveNews
        Disable BraveNewsCardPeek
        '''
        value = ["brave-ads-custom-push-notifications-ads@1","brave-news-peek@2","brave-news@1","brave-rewards-verbose-logging@1"] if enable else []
        self._edit_key(value, 'browser', 'enabled_labs_experiments')

    def p3a(self, enable:bool):
        '''
        P3A: Privacy Preserving Product Analytics
        '''
        value = True if enable else False
        self._edit_key(value, 'brave', 'p3a', 'enabled')
        self._edit_key(value, 'brave', 'stats', 'reporting_enabled')
        value = 0 if enable else 3
        self._edit_key(3, 'brave_shields', 'p3a_usage')
