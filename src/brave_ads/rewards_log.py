from datetime import datetime
from famgz_utils import timeit, print

from .config import cfg


class ReLog:
    '''
    `Rewards.log` parser, retrieving realtime log info.
    Built to work on the last browser run logs.
    '''
    def __init__(self, dev, full=False, only_bracket_lines=True, only_unique_lines=True):
        self.dev = cfg.parse_dev(dev)
        self.path = cfg.dirs(dev, 'default', 'Rewards.log')
        self.session_sep = '-' * 80  # session separator
        self.full = full
        self.only_bracket_lines = only_bracket_lines
        self.only_unique_lines = only_unique_lines
        self.start()  # so can be restarted, jumping to latest run logs

    def start(self):
        self.lines = []
        self.update_lines()
        self.last_read_line = 0  # list index

    def _update_now(self):
        self.now = datetime.now()

    def _read_log(self):
        with open(self.path, encoding='utf-8') as f:
            return f.read()

    def _update_log(self):
        self.file = self._read_log()

    def _get_last_session_sep_index(self):
        if self.full:
            return 0
        i = 0
        while True:
            srch = self.file[i:].find(self.session_sep)
            if srch == -1:
                break
            srch += len(self.session_sep)
            i += srch
        return i

    def _update_sep_index(self):
        self.last_session_start_line = self._get_last_session_sep_index()

    def _separate_header_message(self, line):
        if not line.startswith('['):
            return ('', line)
        try:
            sep = line.index(']') + 1
        except ValueError:
            sep = 48
        header = line[:sep].strip()
        message = line[sep:].strip()
        return (header, message)

    def _get_log_timestamp(self, line):
        # [Jun 02, 2022, 6:48:46.1 PM:VERBOSE2:permission_rule_util.cc(25)] Browser window is not active...
        line = line[1:line.index('M:')+1]
        return datetime.strptime(line, '%b %d, %Y, %I:%M:%S.%f %p').timestamp()

    def _get_read_point(self, time_):
        index = 0
        for i, (header, message) in enumerate(self.lines):
            log_time = self._get_log_timestamp(header)
            if log_time >= time_:
                index = i
                break
        return index

    def clean_log(self):
        import shutil
        bak_path = str(self.path) + '.bak'
        shutil.move(self.path, bak_path)

    def update_lines(self):
        self._update_now()
        self._update_log()
        self._update_sep_index()
        lines = self.file[self.last_session_start_line:].split('\n')
        for line in lines:
            if self.only_bracket_lines and not line.startswith('['):
                continue
            line = self._separate_header_message(line)  # ((header), (message))
            if self.only_unique_lines and line in self.lines:
                continue
            self.lines.append(line)
        # print(len(self.lines), 'lines')

    def read_from(self, time_=None):
        time_ = time_ or self.now.timestamp()
        assert isinstance(time_, (int, float))
        self.last_read_line = self._get_read_point(time_)
        return self.lines[self.last_read_line:]

    def search(self, string, include_header=False):
        return [(header, msg) if include_header else msg for (header, msg) in self.lines if string in msg]

    def search_unblinded_tokens(self):
        string = 'You do not have enough unblinded tokens'
        res = self.search(string)
        return len(res)

    def search_refill_unblinded_tokens_response(self):
        string1 = 'refill_unblinded_tokens.cc(139)'
        string2 = 'URL Response'
        return [self.lines[i+3][1] for i, (header, msg) in enumerate(self.lines) if string1 in header and string2 in msg]

    def search_issuers_bug(self, avoid_click=True):
        str1 = 'does not exist in payments issuer public keys'
        str2 = 'Failed to redeem unblinded token for'

        tids = []
        for i, (header, msg) in enumerate(self.lines):
            if msg.endswith(str1):
                next_line = self.lines[i+1][1]
                if not next_line.startswith(str2):
                    continue
                next_line = next_line.split()
                key   = msg.split()[3]
                ciid  = next_line[-3]
                tiid  = next_line[-7].strip(',')
                etype = next_line[-1]
                # print(f'[bright_black]{key} {ciid} {etype}')
                if etype != 'view' and avoid_click:
                    continue
                if tiid not in tids:
                    tids.append(tiid)
        return tids

    # DEPRECATD version that worked with ciids
    # def search_issuers_bug(self, avoid_click=True):
    #     str1 = 'does not exist in payments issuer public keys'
    #     str2 = 'Failed to redeem unblinded token for'

    #     data = {}
    #     for i, (header, msg) in enumerate(self.lines):
    #         if msg.endswith(str1):
    #             next_line = self.lines[i+1][1]
    #             if not next_line.startswith(str2):
    #                 continue
    #             next_line = next_line.split()
    #             key   = msg.split()[3]
    #             ciid  = next_line[-3]
    #             tiid  = next_line[-7].strip(',')
    #             etype = next_line[-1]
    #             # print(f'[bright_black]{key} {ciid} {etype}')
    #             if etype != 'view' and avoid_click:
    #                 continue
    #             data.setdefault(key,[])
    #             if ciid not in data[key]:
    #                 data[key].append(ciid)
    #     return data

    def _parse_now_as_strings(self, now=None):
        '''
        Return items as in Rewards.log types.
        Just saving the code, not sure when to use it.
        '''
        # eg.: [Jun 02, 2022, 6:48:46.1 PM:VERBOSE2:permission_rule_util.cc(25)] Browser window is not active...
        now = now or self.now
        return {
            'mt'    : now.strftime('%b'),
            'd'     : now.strftime('%d'),
            'y'     : now.strftime('%Y'),
            'h'     : now.strftime('%#I'),
            'm'     : now.strftime('%M'),
            's'     : now.strftime('%S'),
            'ms'    : now.strftime('%f')[:1],
            'am_pm' : now.strftime('%p'),
        }

    def _parse_now(self, now=None):
        now = now or self.now
        return {
            'mt'    : now.strftime('%b'),
            'd'     : now.strftime('%d'),
            'y'     : now.strftime('%Y'),
            'h'     : now.hour,
            'm'     : now.minute,
            's'     : now.second,
            'ms'    : now.microsecond,
            'am_pm' : now.strftime('%p'),
        }

    def _day_chunk(self):
        n = self._parse_now()
        return f"[{n['mt']} {n['d']}, {n['y']}, "

    def _full_chunk(self):
        '''
        Return formatted date exactly like in Rewards.log.
        Just saving the code, not sure when to use it.
        '''
        n = self._parse_now_as_strings()
        return f"[{n['mt']} {n['d']}, {n['y']}, {n['h']}:{n['m']}:{n['s']}.{n['ms']} {n['am_pm']}"
