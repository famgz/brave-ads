import sys
from famgz_utils import print
from pathlib import Path

from .ads import ads
from .config import cfg

opts = {
    'bats'                 : ('',                   "Create bats for app options"),
    'ads-today'            : ('',                   "24h window ads history; based on database.sqlite"),
    'ads-full'             : ('=<days range>',      "full ads history; days range: default=10 all=0"),
    'camps'                : ('=<campaign_id>',     "parse campaigns total max; input campaign_id (full or first 8 digits)"),
    'losses'               : ('',                   "show lost ads (served but not viewed)"),
    'dev'                  : ('=<dev>',             "single device stats"),
    'create-dev'           : ('',                   "create new devices"),
    'clean-client-history' : ('',                   "Clean client.json ads history"),
    'tokens'               : ('',                   "show device's `failed confirmations` `unblinded payment tokens`"),
    'unb-tok-refills'      : ('',                   "show device's all unblinded tokens refills intervals"),
    'run-low-unb-tok'      : ('',                   "runs low unblinded token devices"),
    'redeem'               : ('',                   "show device's next redemption time"),
    'grants'               : ('',                   "show device's claimed earnings"),
    'catalog'              : ('=<"f">',             'show current catalog; "f" reads from local file if exists'),
    'backup'               : ('',                   'system files backup routine'),
    'farmer'               : ('',                   "earn!"),
    'assist'               : ('',                   "dev navigation; asks for input"),
    'read-log'             : ('',                   "rich prints farmers log"),
    'random'               : ('',                   "random dev navigation"),
    'dir'                  : ('=<dev>',             "open profile folder"),
    'earnings'             : ('',                   "parse current monthly earnings from all devices; saves in data_dir\\earnings.json"),
    'payout-screenshots'   : ('',                   "take screenshots of new atb card to register the estimated payout"),
    'log-seg'              : ('',                   "Run assistant to manually log urls and its segments to `urls.json`"),
    'advt'                 : ('=<"add"/"clean">',   "To filter or not advertiser in `client.json`; default: `add`"),
    'cancer'               : ('',                   "To search for new faulty transaction ids and save to `cancer.json`"),
    'zoom-ntp'             : ('',                   "Restore New Tab Zoom to 100%"),
    'reset-redemption'     : ('',                   "Set all devs redemption time to now"),
    'creators'             : ('',                   "Configure creators and visit them with devs"),
    'tip'                  : ('',                   "Configure and open devs to tip"),
}


def make_bats():
    '''
    Create bats for app functions
    '''
    bats_folder = Path(cfg.source_dir, 'bats')
    if not bats_folder.is_dir():
        Path.mkdir(bats_folder)
    for opt in opts:
        name = f'{opt}.bat'
        bat_path = Path(bats_folder, name)
        if bat_path.exists():
            continue
        string = f'python -m brave_ads {opt}\npause\n'
        with open(bat_path, 'w') as f:
            f.write(string)


def main():

    def message():
        print('[yellow]ERROR, you must parse a mode:\n')
        [print(f'[bright_green]{mode + "[green]" + param + "[bright_black]":.<46}[white]{desc}') for mode, (param, desc) in opts.items()]

    if len(sys.argv) != 2:
        message()
        sys.exit()

    args = sys.argv[1].strip()
    opt, *arg = args.split('=')
    arg = arg[0] if arg else None

    if opt not in opts:
        message()
        sys.exit()

    if opt == 'bats':
        make_bats()

    # config.py
    if opt == 'backup':
        cfg.backup()

    elif opt == 'advt':
        mode = 'add'
        if arg is not None:
            if arg not in ('add', 'clean'):
                sys.exit(f'Invalid parameter: {arg}')
            mode = arg
        cfg.all_ban_advertiser(mode=mode)

    elif opt == 'create-dev':
        cfg.create_dev()

    elif opt == 'clean-client-history':
        devs = cfg.all_devs
        cfg.all_clean_client_ads_history(devs=devs, max_size=0)

    # farmer.py
    elif opt == 'farmer':
        from . import farmer
        farmer.main()

    # assist.py
    elif opt == 'assist':
        from . import assist
        assist.main()

    elif opt == 'read-log':
        from . import assist
        assist.read_farmer_log()

    elif opt == 'random':
        from . import assist
        assist.open_random()

    elif opt == 'dir':
        from . import assist
        if arg is not None:
            dev, *_ = list(arg)
            assist.open_profile_dir(dev)

    # earnings.py
    elif opt == 'earnings':
        from . import earnings
        earnings.main()

    elif opt == 'payout-screenshots':
        from . import earnings
        earnings.payout_screenshots()

    # segments.py
    elif opt == 'log-seg':
        from .segments import Segments
        sg = Segments()
        sg.log_url_segment()

    # json_transactions.py
    elif opt == 'cancer':
        from .json_transactions import Transactions
        tr = Transactions()
        tr.find_cancer(print_=True, full=True)

    # json_preferences.py
    elif opt == 'zoom-ntp':
        from .json_preferences import Preferences
        for dev in cfg.all_devs:
            with Preferences(dev) as pf:
                pf.zoom_ntp_out(100)

    elif opt == 'reset-redemption':
        cfg.reset_redemption_time()
        return
        from .json_preferences import Prefs
        for dev in cfg.devs:
            with Preferences(dev) as pf:
                pf.check_next_time_redemption_at()

    # ads.py
    if opt == 'ads-today':
        ads.show('today')

    elif opt == 'ads-full':
        day_range = 15
        if arg is not None:
            day_range = arg
            if not day_range.isdigit():
                sys.exit(f'Invalid day range: {day_range}')
            day_range = int(day_range)
        ads.show('full', day_range=day_range)

    elif opt == 'camps':
        ads.show('camps')

    elif opt == 'losses':
        ads.show_losses()

    elif opt == 'dev':
        if arg is not None:
            dev = arg
            cfg.print_dev(dev, end='\n')
            print(ads.parse_ads(dev, sql=True, all_camp_info=True), highlight=True)

    elif opt == 'tokens':
        ads.show('tokens')

    elif opt == 'unb-tok-refills':
        ads.show('unb-tok-refills')

    elif opt == 'run-low-unb-tok':
        ads.run_low_unb_tokens_devs(cycle_interval=1)

    elif opt == 'redeem':
        ads.show('redeem')

    elif opt == 'grants':
        ads.show('grants')

    elif opt == 'catalog':
        from_file = False
        if arg is not None:
            if arg != 'f':
                sys.exit(f'Invalid parameter: {arg}')
            from_file = True
        ads.show_catalog(from_file=from_file)

    # creators.py
    elif opt == 'creators':
        from .creators import main
        main()

    elif opt == 'tip':
        from .creators import tip
        tip()


if __name__ == '__main__':
    main()
