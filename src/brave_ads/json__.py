from famgz_utils import json_

from .config import cfg


class JsonManager:
    ''' Constructor Class to manage Brave JSON files '''
    def __init__(self, dev, print_, *items_to_path):
        self.dev = cfg.parse_dev(dev)
        self.path = cfg.dirs(self.dev, *items_to_path)
        self._load_prefs()
        self.null = '__null__'
        global print
        print = self._enable_print() if print_ else self._disable_print()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.done()

    def _enable_print(self):
        from famgz_utils import print
        return print

    def _disable_print(self):
        void = lambda *x, **y: None
        return void

    def _load_prefs(self):
        self.prefs = json_(self.path)

    def done(self):
        json_(self.path, self.prefs, backup=True)

    def _create_keys(self, stop_index, *keys):
        d = self.prefs
        for key in keys[:stop_index]:
            d = d.setdefault(key, {})
        return d

    def _read_key(self, stop_index, *keys):
        stop_index = stop_index or 100
        d = self.prefs
        for key in keys[:stop_index]:
            d = d.get(key, {})
        return d

    def _edit_key(self, value, *keys):
        # create/edit
        if value != self.null:
            d = self._create_keys(-1, *keys)
            d[keys[-1]] = value
        # delete
        else:
            d = self._read_key(-1, *keys)
            if keys[-1] in d:
                d.pop(keys[-1])
        print(f'[bright_black]{self.dev} edited: {">".join(keys)}')

    @staticmethod
    def _all(cls, func, *params):
        '''
        Wrapper to run one self-function for all devices
        Must receive cls from classmethod function
        '''
        funcs = [x for x in dir(cls) if not x.startswith('_') and x not in ('all_', 'done')]
        if func not in funcs:
            print(f'Invalid function: {func}')
            return
        for dev in cfg.devs:
            x = cls(dev)
            exec(f'x.{func}(*{params})')
            x.done()

    # @staticmethod
    # def _all(cls, func, *params):
    #     '''
    #     Wrapper to run one self-function for all devices
    #     '''
    #     import inspect
    #     try:
    #         frame = inspect.currentframe().f_back
    #         class_ = frame.f_locals['__class__']
    #         funcs = [x for x in dir(class_) if not x.startswith('_') and x not in ('all_', 'done')]
    #         if func not in funcs:
    #             print(f'Invalid function: {func}')
    #             return
    #         for dev in cfg.devs:
    #             cls = class_(dev)
    #             exec(f'cls.{func}(*{params})')
    #             cls.done()
    #     finally:
    #         del frame
