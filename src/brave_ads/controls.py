import pyautogui
import pynput
import pyperclip
import random
import string
import subprocess as sp
from ctypes import windll
from famgz_utils import run, print, load_mouse_event, min_duration, func_name
from pynput.keyboard import Key
from random import choice
from time import sleep

from .config import cfg


pyautogui.FAILSAFE = False
_kb = pynput.keyboard.Controller()  # keyboard
_ms = pynput.mouse.Controller()     # mouse


KEYBOARD_KEYS = ['\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(',
')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7',
'8', '9', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`',
'a', 'b', 'c', 'd', 'e','f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~',
'accept', 'add', 'alt', 'altleft', 'altright', 'apps', 'backspace',
'browserback', 'browserfavorites', 'browserforward', 'browserhome',
'browserrefresh', 'browsersearch', 'browserstop', 'capslock', 'clear',
'convert', 'ctrl', 'ctrlleft', 'ctrlright', 'decimal', 'del', 'delete',
'divide', 'down', 'end', 'enter', 'esc', 'escape', 'execute', 'f1', 'f10',
'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f2', 'f20',
'f21', 'f22', 'f23', 'f24', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
'final', 'fn', 'hanguel', 'hangul', 'hanja', 'help', 'home', 'insert', 'junja',
'kana', 'kanji', 'launchapp1', 'launchapp2', 'launchmail',
'launchmediaselect', 'left', 'modechange', 'multiply', 'nexttrack',
'nonconvert', 'num0', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6',
'num7', 'num8', 'num9', 'numlock', 'pagedown', 'pageup', 'pause', 'pgdn',
'pgup', 'playpause', 'prevtrack', 'print', 'printscreen', 'prntscrn',
'prtsc', 'prtscr', 'return', 'right', 'scrolllock', 'select', 'separator',
'shift', 'shiftleft', 'shiftright', 'sleep', 'space', 'stop', 'subtract', 'tab',
'up', 'volumedown', 'volumemute', 'volumeup', 'win', 'winleft', 'winright', 'yen',
'command', 'option', 'optionleft', 'optionright']


class Controls:

    def __init__(self):
        self.load_mouse_event = load_mouse_event

    def r(self, a, b):
        return random.randint(a, b)


    def ru(self, a, b):
        return random.uniform(a, b)


    def halt(self, n=0):
        r = random.uniform(0.30, 0.35)
        sleep(n + r)


    def blink(self, ):
        sleep(0.15)
        return
        sleep(random.uniform(0.15, 0.175))


    def click(self, target='blank', n=1):
        offset = self.r(-10,10)
        templates = {
            'blank':              (self.r(460,650), self.r(400,600)),  # Click on blank spot
            'ad':                 (1350+offset, 970+offset),           # Click on ad (to avoid `dismiss`)
            'close_ad':           (1520, 940),                         # Close ad (to trigger `dismiss`)
            'enable_rewards_100': (1760, 464),                         # Enable Rewards on New Tab on 1080p 100% Maximized window
            'enable_rewards_125': (1724, 576),                         # Enable Rewards on New Tab on 1080p 125% Maximized window
        }
        for _ in range(n):
            sleep(0.1)
            x, y = target if isinstance(target, (list, tuple)) and len(target) == 2 else templates[target]
            pyautogui.click(x, y)


    def pick_random_letter(self, ):
        letters = list(string.ascii_letters)
        return choice(letters)


    def press(self, *keys, n=1, print_=False):
        '''
        Press keyboard keys. Modes:
        -no "keys": choose a random letter
        -multiple "keys": use hotkey
        '''
        keys = keys or []
        n = n or 1

        # validate
        if keys:
            valid_keys =   [x for x in keys if x     in pyautogui.KEYBOARD_KEYS]
            invalid_keys = [x for x in keys if x not in pyautogui.KEYBOARD_KEYS]
            if invalid_keys:
                print(f'[yellow]\[{func_name()}]Warning, invalid keys input:[bright_white] {" ".join(invalid_keys)}')
            if not valid_keys:
                print(f'[yellow]\[{func_name()}]Warning, keys were given but none is valid. Exiting...')
                return
            keys = valid_keys

        # press
        for _ in range(n):
            if len(keys) > 1:
                pyautogui.hotkey(*keys, interval=0)
                if print_:
                    print(f'[bright_black]\[{func_name()}pressed keys: {" ".join(keys)}')
                continue
            key = keys[0] if keys else self.pick_random_letter()
            pyautogui.press(key)
            self.blink() if not keys else sleep(0.1)


    def press_esc(self, n=1):
        self.press('esc', n=n)


    def press_home(self, n=1):
        self.press('home', n=n)


    def press_pgup(self, n=1):
        self.press('pageup', n=n)


    def press_pgdn(self, n=1):
        self.press('pagedown', n=n)


    def press_alt_f_x(self, ):  # gentle quit
        _kb.press(Key.alt)
        _kb.press('f')
        _kb.release(Key.alt)
        _kb.release('f')
        sleep(0.25)
        self.press('x')


    def press_ctrl_shift_w(self, ):  # gentle quit browser
        _kb.press(Key.ctrl)
        _kb.press(Key.shift)
        _kb.press('w')
        _kb.release(Key.ctrl)
        _kb.release(Key.shift)
        _kb.release('w')


    def press_alt_space_r(self, ):  # DEPRECATED: restore window size by keyboard
        sleep(0.1)
        _kb.press(Key.alt)
        _kb.press(Key.space)
        _kb.release(Key.alt)
        _kb.release(Key.space)
        sleep(0.1)
        self.press('r')


    def press_ctrl_plus(self, x):
        sleep(0.1)
        _kb.press(Key.ctrl)
        _kb.press(x)
        _kb.release(Key.ctrl)
        _kb.release(x)


    def open_new_tab(self, click=True):
        self.press_ctrl_plus('t')
        self.blink()
        if click:
            self.click()


    def close_tab(self, n=1):
        for _ in range(n):
            if not cfg.is_brave_running():
                return
            self.press_ctrl_plus('w')


    def ctrl_tab(self, ):
        sleep(0.1)
        _kb.press(Key.ctrl)
        _kb.press(Key.tab)
        _kb.release(Key.ctrl)
        _kb.release(Key.tab)


    def silent(self, wait):
        wait = min(wait, 10)
        windll.user32.BlockInput(True)
        sleep(wait)
        windll.user32.BlockInput(False)


    @cfg.check_dev
    def run_brave(self, dev, url='blank', maximized=False, perf=False, print_=False):
        if not dev:
            raise ValueError(f'Invalid dev: {dev}')

        templates = {
            ''        : '',  # runs browser's `On Startup` option
            'blank'   : 'about:blank',
        }
        url = url.strip()
        url = templates.get(url) or url

        user_data_dir = cfg.dirs(dev, 'user_data')
        maximized = r'cmd /c start "" /max ' if maximized else ''
        perf = ' --enable-low-end-device-mode --disable-extensions' if perf else ''
        command = fr'{maximized}"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --user-data-dir="{user_data_dir}"{perf} {url}'
        if print_:
            print(f'[white]\[{func_name()}]{command}')
        prog = sp.Popen(command, stdin=sp.PIPE, stdout=sp.DEVNULL)


    def open_page(self, mode='default', sg=None, first=False, new=False):
        from .segments import u

        if new:
            self.open_new_tab()

        if not first:
            self.click(n=2)
            self.press('f6')  # focus address bar
        if sg:
            url = sg.pick()
        else:
            if mode == 'random':
                url = u.rand_url
            elif mode == 'default':
                url = u.def_url
            elif mode == 'rewards-internals':
                url = 'brave://rewards-internals'
            else:
                url = mode
        pyperclip.copy(url)
        self.press('ctrl', 'v')
        self.press('enter')


    # @timeit
    @min_duration(3.5)
    def start(self, dev):
        self.run_brave(dev, 'blank')
        sleep(0.5)
        load_mouse_event(max_dur=2)
        self.click()
        self.press(n=8)


    # @timeit
    def kill(self, n=1, print_=True, check_process=True):
        '''
        Close Brave application by input
        and ultimately by killing process.
        Should only be used in automation mode
        '''
        is_up = 0
        was_closed = False
        if not cfg.is_brave_running():
            return False
        # close n browser instances
        for _ in range(n):
            self.click()
            self.press_ctrl_shift_w()
            # press_alt_f_x()
            if not check_process:
                return False
            sleep(0.2)
            if not cfg.is_brave_running():
                return False
        # check and halt if still running
        for _ in range(10):
            if not cfg.is_brave_running():
                was_closed = True
                break
                # return False if i==0 else True
            is_up += 1
            sleep(2)
        if is_up and print_:
            print(f'[bright_yellow] up({is_up})')
        if was_closed:
            return is_up
        # finally force close
        cfg.close_brave(print_=False)
        return True


ct = Controls()
