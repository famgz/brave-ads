from famgz_utils import json_, print, func_name
from os import path as p
from os.path import join as pj

from .config import cfg

ENABLE_MANAGER = False  # bool
SHOULD_MANAGER_FIND_CANCER = False  # bool


class Transactions:

    def __init__(self, devs=None):
        self.devs = devs or cfg.devs
        self.public_keys = None

    def confirmations_json(self, dev, data=None):
        path = cfg.dirs(dev, 'ads_service', 'confirmations.json')
        if data is None:
            return json_(path)
        json_(path, data, backup=True)

    def failed_json(self, dev, file, data=None):
        assert file in ['queue', 'trash', 'click']
        ads_service = cfg.dirs(dev, 'ads_service')
        path = pj(ads_service, f'failed_{file}.json')
        if not p.isfile(path):
            json_(path, [])
            return []
        if data is None:
            return json_(path) or []
        json_(path, data, backup=True)

    def cancer_json(self, data=None):
        path = pj(cfg.config_dir, 'cancer.json')
        if not p.isfile(path):
            json_(path, [])
            return []
        if data is None:
            return json_(path) or []
        saved = json_(path, data, backup=True, n_backups=100, sort_keys=True, indent='\t')
        return saved

    def get_cancer_ciids(self):
        cancer = self.cancer_json()
        cancer_ciids = []
        for key, ciids in cancer.items():
            for x in ciids:
                if x not in cancer_ciids:
                    cancer_ciids.append(x)
        return cancer_ciids

    def find_cancer(self, dev=None, print_=True, full=False):
        '''
        Collects faulty transaction_ids from Rewards.log
        '''
        devs = [dev] if dev else self.devs

        from .rewards_log import ReLog
        cancer = self.cancer_json()
        print(f'[white]\[{func_name()}]') if print_ else ...
        all_added = 0
        for dev in devs:
            if dev in cfg.flagged_devs:
                ...
                # continue
            rl = ReLog(dev, full=full)
            tids = rl.search_issuers_bug(avoid_click=True)
            added = 0
            for tid in tids:
                if tid not in cancer:
                    cancer.append(tid)
                    added += 1
            if added:
                print(f'[bright_black]{dev}:{added}', end=' ') if print_ else ...
                all_added += added
        cancer.sort()
        saved = self.cancer_json(data=cancer)
        if print_:
            if all_added:
                print(f'\n[white]{all_added} cancer tids added')
            # if saved:
            #     print('[bright_black]cancer.json updated')

    @cfg.check_dev
    def len_failed(self, dev):
        confs = self.confirmations_json(dev)
        confs = confs['confirmations']['failed_confirmations']
        return len(confs)

    @cfg.check_dev
    def len_unb_pay_tokens(self, dev):
        unb_pay_tokens = self.confirmations_json(dev)
        unb_pay_tokens = unb_pay_tokens['unblinded_payment_tokens']
        return len(unb_pay_tokens)

    @cfg.check_dev
    def len_unb_tokens(self, dev):
        unb_tokens = self.confirmations_json(dev)
        return len(unb_tokens['unblinded_tokens'])

    def sort_by_timestamp(self, data, reverse=False):
        if not data:
            return
        data.sort(key=lambda x: float(x['timestamp_in_seconds']), reverse=reverse)

    @cfg.check_dev
    def manage_failed_confs(self, dev=None, print_=False, filter_click=True, filter_trash=True, sort_failed=True):
        devs    = [dev]    if dev    else self.devs
        print(f'[white]\[{func_name()}]')

        if SHOULD_MANAGER_FIND_CANCER or filter_trash:
            self.find_cancer()
            cancer_tids = self.cancer_json()
            print(f'[white]{len(cancer_tids)} cancer tids')

        print(f'[white]manage={bool(ENABLE_MANAGER)}', end=' ')
        if ENABLE_MANAGER:
            print(f'[white]{sort_failed=} {filter_trash=} {filter_click=}')

        cfg.close_brave()

        stats = []
        all_failed = 0

        for dev in devs:

            # print(f'[bright_black]{dev}', end=' ')

            confs = self.confirmations_json(dev)
            failed = confs['confirmations']['failed_confirmations']

            if not ENABLE_MANAGER:
                all_failed += len(failed)
                n_failed = len(failed)
                n_unb_pay_tokens = len(confs['unblinded_payment_tokens'])
                stats.append((dev, n_failed, n_unb_pay_tokens))
                print('\r', end='')
                continue

            click_queue = []
            trash_queue = []
            # remove faulty items from queue
            if filter_click or filter_trash:
                for item in failed[::]:
                    # click/dismiss
                    if filter_click:
                        if item['type'] != 'view':
                            failed.remove(item)
                            if item not in click_queue:
                                click_queue.append(item)
                    # bad tids
                    elif filter_trash:
                        if item['transaction_id'] in cancer_tids:
                            failed.remove(item)
                            if item not in trash_queue:
                                trash_queue.append(item)
            all_failed += len(failed)

            n_failed = len(failed)
            n_unb_pay_tokens = len(confs['unblinded_payment_tokens'])
            stats.append((dev, n_failed, n_unb_pay_tokens))

            # place newest ads on top and save changes to confirmations.json
            if sort_failed:
                self.sort_by_timestamp(failed, reverse=True)
            self.confirmations_json(dev, confs)

            # save click/dismiss items to failed_click.json
            if click_queue:
                click = self.failed_json(dev, 'click')
                for item in click_queue:
                    if item not in click:
                        click.append(item)
                self.failed_json(dev, 'click', click)

            # save bad items to failed_trash.json
            if trash_queue:
                trash = self.failed_json(dev, 'trash')
                for item in trash_queue:
                    if item not in trash:
                        trash.append(item)
                self.failed_json(dev, 'trash', trash)

            # print status
            if click_queue or trash_queue:
                if print_:
                    print(f'\n[white]failed: {n_failed}')
                    if click_queue:
                        print(f'[white]click: {len(click_queue)}')
                    if trash_queue:
                        print(f'[white]trash: {len(trash_queue)}')
            else:
                continue
                print('\r', end='')

        print(f'\n[bright_white]{all_failed} [white]failed confirmations left')
        return stats

    def move_all_trash_to_confs(self):
        print(f'[white]\[{func_name()}]')
        for dev in self.devs:
            print(dev)
            confs = self.confirmations_json(dev)
            failed = confs['confirmations']['failed_confirmations']
            trash = self.failed_json(dev, 'trash')
            for item in trash[::]:
                trash.remove(item)
                if item not in failed:
                    failed.append(item)
            self.confirmations_json(dev, confs)
            self.failed_json(dev, 'trash', trash)

    @cfg.check_dev
    def empty_failed_sort_queue(self, dev=None):
        '''
        Deprecated since we are not using failed_queue.json anymore
        '''
        confs  = self.confirmations_json(dev)
        failed = len(confs['confirmations']['failed_confirmations'])

        # self.check_public_keys(dev, confs)

        queue = self.failed_json(dev, 'queue')

        if not failed:
            return

        for _ in range(failed):
            item = confs['confirmations']['failed_confirmations'].pop(0)
            if item not in queue:
                queue.append(item)

        temp = []
        for i in queue:
            if i not in temp:
                temp.append(i)

        queue = temp

        self.sort_by_timestamp(queue)

        self.confirmations_json(dev, confs)
        self.failed_json(dev, 'queue', queue)

        print(f'[white]\[{func_name()}]{failed} items removed from {cfg.device_alias(dev)} confirmations.json')

    def all_empty_failed_sort_keys(self):
        for dev in self.devs:
            self.empty_failed_sort_queue(dev)

    def public_keys_json(self, keys_to_add=None):
        path = cfg.dirs(None, None, 'data', 'public_keys.json')

        if not self.public_keys:
            self.public_keys = json_(path) or []

        if keys_to_add:
            new_keys = [x for x in keys_to_add if x not in self.public_keys]
            if new_keys:
                self.public_keys.extend(new_keys)
                json_(path, self.public_keys, backup=True, indent='\t')
                print(f'[white]{len(new_keys)} keys added to public_keys.json')

    @cfg.check_dev
    def check_public_keys(self, dev=None, data=None):
        confs  = data or self.confirmations_json(dev)
        keys = confs['issuers'][0]['publicKeys']
        self.public_keys_json(keys)

    def all_check_public_keys(self):
        url = 'https://static.ads.brave.com/v1/issuers/'

        for dev in self.devs:
            confs  = self.confirmations_json(dev)
            keys = confs['issuers'][0]['publicKeys']
            self.public_keys_json(keys)
