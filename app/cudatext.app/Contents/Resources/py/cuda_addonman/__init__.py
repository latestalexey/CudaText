import os
import re
import shutil
import json
import collections
import webbrowser
from cudatext import *
from urllib.parse import unquote
from .work_local import *
from .work_remote import *
from .work_dlg_config import *
from .work_github import *
from .work_cudatext_updates import check_cudatext
from . import opt

dir_for_all = os.path.join(os.path.expanduser('~'), 'CudaText_addons')
fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_addonman.json')

PREINST = 'preinstalled'
STD_MODULES = (
  'cuda_addonman',
  'cuda_comments',
  'cuda_insert_time',
  'cuda_make_plugin',
  'cuda_multi_installer',
  'cuda_new_file',
  'cuda_options_editor',
  'cuda_palette',
  'cuda_project_man',
  'cuda_show_unsaved',
  'cuda_tabs_list',
  'cuda_testing_code_tree',
  'cuda_testing_dlg_proc',
  'cuda_testing_gaps',
  'cudax_lib',
  )


class Command:

    def __init__(self):
        if os.path.isfile(fn_config):
            data = json.loads(open(fn_config).read(), object_pairs_hook=collections.OrderedDict)
            opt.ch_user = data.get('channels_user', opt.ch_user)
            opt.suggest_readme = data.get('suggest_readme', True)
            opt.install_confirm = data.get('install_confirm', True)
            opt.proxy = data.get('proxy', '')


    def do_config(self):
        res = do_config_dialog()
        if res is None: return

        data = {}
        data['channels_user'] = opt.ch_user
        data['suggest_readme'] = opt.suggest_readme
        data['install_confirm'] = opt.install_confirm
        data['proxy'] = opt.proxy

        with open(fn_config, 'w') as f:
            f.write(json.dumps(data, indent=4))


    def do_show_links(self):

        msg_status('Downloading list...')
        items = get_remote_addons_list(opt.ch_def+opt.ch_user)
        msg_status('')
        if not items:
            msg_status('Cannot download list')
            return

        res = sorted([item['url'] for item in items])
        file_open('')
        ed.set_text_all('\n'.join(res)+'\n')


    def do_download_all(self):
        global dir_for_all
        res = dlg_input('Folder to save files:', dir_for_all)
        if not res: return
        dir_for_all = res
        if not os.path.isdir(dir_for_all):
            os.mkdir(dir_for_all)
        if not os.path.isdir(dir_for_all):
            msg_box('Cannot create dir: '+dir_for_all, MB_OK+MB_ICONERROR)
            return

        msg_status('Downloading list...')
        items = get_remote_addons_list(opt.ch_def+opt.ch_user)
        msg_status('')
        if not items:
            msg_status('Cannot download list')
            return

        err = 0
        stopped = False
        app_proc(PROC_SET_ESCAPE, False)

        for (i, item) in enumerate(items):
            url = item['url']

            if app_proc(PROC_GET_ESCAPE, '')==True:
                app_proc(PROC_SET_ESCAPE, False)
                if msg_box('Stop downloading?', MB_OKCANCEL+MB_ICONQUESTION)==ID_OK:
                    stopped = True
                    break

            app_proc(PROC_PROGRESSBAR, (i+1)*100//len(items))
            msg_status('Downloading: %d/%d'%(i+1, len(items)), True) #must be with True

            name = unquote(url.split('/')[-1])
            dir = os.path.join(dir_for_all, name.split('.')[0])
            if not os.path.isdir(dir):
                os.mkdir(dir)
            fn = os.path.join(dir, name)
            res = get_url(url, fn)
            if res == False: #abort button
                break
            if not os.path.isfile(fn):
                err += 1
                print('Cannot download file: '+url)
                continue

        app_proc(PROC_PROGRESSBAR, 0)
        app_proc(PROC_PROGRESSBAR, -1)

        text = 'Download done' if not stopped else 'Download stopped'
        if err>0:
            text += '\nErrors occured, see Python console'
        msg_box(text, MB_OK+MB_ICONINFO)


    def do_reinstall_addon(self):
        self.do_install_addon(True)

    def do_install_addon(self, reinstall=False):

        caption = 'Re-install' if reinstall else 'Install'
        msg_status('Downloading list...')
        items = get_remote_addons_list(opt.ch_def+opt.ch_user)
        msg_status('')
        if not items:
            msg_status('Cannot download list')
            return

        items = sorted(items,
            key=lambda item: (item['kind'], item['name'])
            )

        kinds = sorted(list(set([i['kind'] for i in items])))

        installed_list = get_installed_list()
        if reinstall:
            items = [i for i in items if i.get('module', '') in installed_list]
        else:
            items = [i for i in items if i.get('module', '') not in installed_list]

        names = ['<Category>'] + [ i['kind']+': '+i['name']+'\t'+i['desc'] for i in items ]

        res = dlg_menu(
            MENU_LIST_ALT+MENU_NO_FUZZY+MENU_NO_FULLFILTER,
            names,
            caption=caption
            )
        if res is None: return

        if res==0:
            res = dlg_menu(
                MENU_LIST,
                kinds,
                caption='Category'
                )
            if res is None: return

            need_kind = kinds[res]
            items = [ i for i in items if i['kind']==need_kind ]
            names = [ i['kind']+': '+i['name']+'\t'+i['desc'] for i in items ]

            res = dlg_menu(
                MENU_LIST_ALT+MENU_NO_FUZZY+MENU_NO_FULLFILTER,
                names,
                caption=caption+' / Category "'+need_kind+'"'
                )
            if res is None: return

            name = items[res]['name']
            url = items[res]['url']
            version = items[res]['v']
            kind = items[res]['kind']

        else:
            res -= 1
            name = items[res]['name']
            url = items[res]['url']
            version = items[res]['v']
            kind = items[res]['kind']

        self.do_install_single(name, url, version, kind)


    def do_install_single(self, name, url, version, kind):
        #check for CudaLint
        if 'linter.' in url:
            if not 'cuda_lint' in get_installed_list():
                msg_box('This is linter, it requires CudaLint plugin installed', MB_OK+MB_ICONWARNING)
                return

        #check for CudaTree
        if 'treehelper.' in url:
            if not 'cuda_tree' in get_installed_list():
                msg_box('This is TreeHelper, it requires CudaTree plugin installed', MB_OK+MB_ICONWARNING)
                return

        #download
        fn = get_plugin_zip(url)
        if not os.path.isfile(fn):
            msg_status('Cannot download file')
            return

        s_options = '' if opt.install_confirm else '/silent'
        ok = file_open(fn, options=s_options)

        msg_status('Addon installed' if ok else 'Installation cancelled')
        if not ok:
            os.remove(fn)
            return

        #save version
        props = do_save_version(url, fn, version)
        os.remove(fn)

        if props:
            #suggest readme
            m = props[2]
            if m and opt.suggest_readme:
                names = []
                fn = get_readme_of_module(m)
                if fn:
                    names.append((get_name_of_module(m)+': view readme', fn))
                fn = get_history_of_module(m)
                if fn:
                    names.append((get_name_of_module(m)+': view history', fn))

                if names:
                    res = dlg_menu(MENU_LIST, [s[0] for s in names])
                    if res is None: return
                    file_open(names[res][1])


    def do_install_lexer(self):
        """Not used. For future? Suggest only lexers to install"""

        items = get_avail_list()
        items = [l for l in items if l[0].startswith('Lexer:')]

        res = dlg_menu(MENU_LIST, [l[0] for l in items])
        if res is None: return
        res = items[res]
        url = get_item_url(res[2])
        fn = get_plugin_zip(url)
        if os.path.isfile(fn):
            file_open(fn)

    def do_remove(self):
        m = get_installed_choice('Remove', STD_MODULES)
        if not m:
            return
        if msg_box('Remove plugin: '+get_name_of_module(m), MB_OKCANCEL+MB_ICONQUESTION)!=ID_OK:
            return
        
        do_remove_version_of_plugin(m)
        if do_remove_module(m):
            msg_box('Removed, restart program to see changes', MB_OK+MB_ICONINFO)

    def do_remove_data(self):
        path = get_installed_data_choice()
        if path is None:
            return

        if os.path.isfile(path):
            msg = 'Remove data file:'
        else:
            msg = 'Remove data folder:'
        if msg_box(msg+'\n'+path, MB_OKCANCEL+MB_ICONQUESTION)!=ID_OK:
            return

        if do_remove_data(path):
            msg_box('Removed, restart program to see changes', MB_OK+MB_ICONINFO)


    def do_edit(self):
        m = get_installed_choice('Edit')
        if m is None: return
        fn = get_initpy_of_module(m)
        file_open(fn)
        msg_status('Opened: '+fn)

    def do_homepage(self):
        m = get_installed_choice('Visit homepage')
        if m is None: return
        s = get_homepage_of_module(m)
        if s:
            webbrowser.open_new_tab(s)
            msg_status('Opened browser: '+s)
        else:
            msg_box('Plugin "%s" doesn\'t have "homepage" field in install.inf' % \
              get_name_of_module(m), MB_OK+MB_ICONWARNING)

    def do_readme(self):
        m = get_installed_choice('Open readme')
        if m is None: return
        s = get_readme_of_module(m)
        if s:
            file_open(s)
        else:
            msg_status('Plugin "%s" doesn\'t have readme' % get_name_of_module(m))

    def do_history(self):
        m = get_installed_choice('Open history')
        if m is None: return
        s = get_history_of_module(m)
        if s:
            file_open(s)
        else:
            msg_status('Plugin "%s" doesn\'t have history' % get_name_of_module(m))


    def do_update(self):

        msg_status('Downloading list...')
        remotes = get_remote_addons_list(opt.ch_def+opt.ch_user)
        msg_status('')
        if not remotes:
            msg_status('Cannot download list')
            return

        modules = get_installed_list()
        modules = [m for m in modules if m not in STD_MODULES] + [m for m in modules if m in STD_MODULES]
        modules_selected = []
        text_col = []

        for m in modules:
            name = get_name_of_module(m)

            v_local = '?'
            if m in STD_MODULES:
                v_local = PREINST
            col_item = name+'\r'+m+'\r'+v_local+'\r?'

            remote_item = [d for d in remotes if d.get('module', '')==m]
            if remote_item:

                url = remote_item[0]['url']
                v_remote = remote_item[0]['v']
                v_local = get_addon_version(url) or get_addon_version_old(m) or v_local

                col_item = name + '\r' + m + '\r' + v_local + '\r' + v_remote
                if v_local == PREINST:
                    s = '0'
                elif v_local == '?':
                    s = '1'
                elif v_local < v_remote:
                    s = '1'
                else:
                    s = '0'
            else:
                s = '0'

            modules_selected.append(s)
            text_col.append(col_item)

        #move preinstalled to end
        #--breaks checks, commented
        #text_col = [t for t in text_col if PREINST not in t] +\
                   #[t for t in text_col if PREINST in t]

        text_col_head = 'Name=220\rFolder=170\rLocal=125\rAvailable=125'
        text_items = '\t'.join([text_col_head]+text_col)
        text_val = '0;'+','.join(modules_selected)
        text_val_initial = text_val

        RES_OK = 0
        RES_CANCEL = 1
        RES_LIST = 2
        RES_SEL_NONE = 3
        RES_SEL_NEW = 4
        c1 = chr(1)

        while True:
            text = '\n'.join([
              c1.join(['type=button', 'pos=464,500,564,0', 'cap=Update', 'props=1']),
              c1.join(['type=button', 'pos=570,500,670,0', 'cap=Cancel']),
              c1.join(['type=checklistview', 'pos=6,6,670,490', 'items='+text_items, 'val='+text_val, 'props=1']),
              c1.join(['type=button', 'pos=6,500,100,0', 'cap=Deselect all']),
              c1.join(['type=button', 'pos=106,500,200,0', 'cap=Select new']),
              ])

            res = dlg_custom('Update plugins', 676, 532, text)
            if res is None: return

            res, text = res
            if res == RES_SEL_NONE:
                text_val = '0;'
                continue
            if res == RES_SEL_NEW:
                text_val = text_val_initial
                continue
            if res == RES_CANCEL:
                return
            if res == RES_OK:
                break

        text = text.splitlines()[RES_LIST]
        text = text.split(';')[1].split(',')

        modules = [m for (i, m) in enumerate(modules) if 0<=i<len(text) and text[i]=='1']
        if not modules: return
        print('Updating addons:')
        fail_count = 0

        for remote in remotes:
            m = remote.get('module', '')
            if not m in modules: continue

            print('  [%s] %s' % (remote['kind'], remote['name']))
            msg_status('Updating: [%s] %s' % (remote['kind'], remote['name']), True)
            do_remove_module(m) # delete old dir

            url = remote['url']

            fn = get_plugin_zip(url)
            if not fn: continue
            if os.path.isfile(fn) and file_open(fn, options='/silent'):
                do_save_version(url, fn, remote['v'])
            else:
                fail_count += 1
                print('  '+remote['name']+' - Update failed')

        s = 'Done'
        if fail_count>0:
            s += ', with %d fail(s)'%fail_count
        print(s)
        msg_status(s)


    def check_cudatext_updates(self):

        check_cudatext()

    def install_from_github(self):

        do_install_from_github()
