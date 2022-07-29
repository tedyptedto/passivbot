from git import Repo
import os
import glob
import hjson
from pathlib import Path
import pandas as pd
from tabulate import tabulate
import hashlib


test_mode = False
# test_mode = True

def getValueInResultTxt(content, key, long_or_short):
    i_finded = 1
    if long_or_short == "short":
        i_finded = 2

    finded = 0
    for item in content.split("\n"):
        if ("| " + key) in item:
            line = item.strip(" |").split('|')
            value = line[1].strip()
            finded += 1
            if finded == i_finded:
                return value
    return "N/C"

def generateReadme(only_trash=False):
    base_dir = os.path.realpath("./../configs/live/PBSO/")
    list_of_files = glob.glob(base_dir + "/**/config.json", recursive=True)
    data_list = []
    # print(list_of_files)
    for file in list_of_files:
        file = os.path.realpath(file)
        dir = os.path.dirname(file)

        list = glob.glob(dir + "/_backtest_*.hjson")
        file_backtest_hjson = "unknown"
        if (len(list) == 1):
            file_backtest_hjson = list[0]

        list = glob.glob(dir + "/_harmony_*.hjson")
        file_harmony_hjson = "unknown"
        if (len(list) == 1):
            file_harmony_hjson = list[0]

        list = glob.glob(dir + "/bulk_*.hjson")
        bulk_optimisation_hjson = "unknown"
        if (len(list) == 1):
            bulk_optimisation_hjson = list[0]


        group_file = {
            "file_config_json" : file,

            "file_result_txt" : dir + "/result.txt",
            "file_backtest_hjson" : file_backtest_hjson,
            "file_harmony_hjson" : file_harmony_hjson,
            "bulk_optimisation_hjson" : bulk_optimisation_hjson,
        }

        all_files_exist = True
        for key in group_file:
            # print(group_file[key])
            if not os.path.exists(group_file[key]):
                all_files_exist = False
            else:
                if (key.endswith('json')):
                    group_file[key] = {
                                    'file' : group_file[key],
                                    'file_r' : group_file[key].replace(base_dir, ''),
                                    'data' : hjson.load(open(group_file[key], encoding="utf-8")),
                    }
                else:
                    group_file[key] = {
                                    'file' : group_file[key],
                                    'file_r' : group_file[key].replace(base_dir, ''),
                                    'data' : Path(group_file[key]).read_text(),
                    }

        if not all_files_exist:
            continue

        ftxt = group_file['file_result_txt']['data']

        # op_coin = len(group_file['bulk_optimisation_hjson']['data']['coin_list'])


        parent_dir = group_file['file_config_json']['file'].replace(base_dir, '').strip("/").split("/")[0]

        uid = hashlib.md5(hjson.dumps(group_file['file_config_json']['data']).encode('utf-8')).hexdigest()[0:5]
        strat_info = {
            "uid" : uid,
            "info" : "[conf](https://github.com/tedyptedto/pbos/blob/main/" + group_file['file_config_json']['file_r'] + "#"+uid+")" + "/" +
                    "[bulk](https://github.com/tedyptedto/pbos/blob/main/" + group_file['bulk_optimisation_hjson']['file_r'] + "#"+uid+")",
            "categ" : parent_dir,
            # "op_coin" : op_coin,

            "bt_balance" : group_file['file_backtest_hjson']['data']['starting_balance'],
            "bt_coin" : getValueInResultTxt(ftxt, 'Symbol', 'long'),
            "bt_days" : int(float(getValueInResultTxt(ftxt, 'No. days', 'long'))),
            # "bt_end" : group_file['file_backtest_hjson']['data']['end_date'].replace('-', '/').strip(','),
            
            "l_bt_adg" : getValueInResultTxt(ftxt, 'ADG realized per exposure', 'long'),
            # "l_bt_gain"  : getValueInResultTxt(ftxt, 'Total gain', 'long'),
            # "l_bt_bkrupt"  : getValueInResultTxt(ftxt, 'Closest bankruptcy', 'long'),

            "s_bt_adg" : getValueInResultTxt(ftxt, 'ADG realized per exposure', 'short'),
            # "s_bt_gain"  : getValueInResultTxt(ftxt, 'Total gain', 'short'),
            # "s_bt_bkrupt"  : getValueInResultTxt(ftxt, 'Closest bankruptcy', 'short'),


            "long" : group_file['file_config_json']['data']['long']['enabled'],
            # "l_we" : group_file['file_config_json']['data']['long']['wallet_exposure_limit'],
            'l_AU' : False if (group_file['file_config_json']['data']['long']['auto_unstuck_ema_dist'] == 0) and (group_file['file_config_json']['data']['long']['auto_unstuck_wallet_exposure_threshold'] == 0) else True,
            "l_gspan" : str(int(group_file['file_config_json']['data']['long']['grid_span'] * 100)) + "%",
            "l_TP"  : str(round(group_file['file_config_json']['data']['long']['min_markup'] * 100,2)) + "% /"+str(round(group_file['file_config_json']['data']['long']['markup_range'] * 100,2))+"%/",


            "short" : group_file['file_config_json']['data']['short']['enabled'],
            # "s_we" : group_file['file_config_json']['data']['short']['wallet_exposure_limit'],
            's_AU' : False if (group_file['file_config_json']['data']['short']['auto_unstuck_ema_dist'] == 0) and (group_file['file_config_json']['data']['short']['auto_unstuck_wallet_exposure_threshold'] == 0) else True,
            "s_gspan" : str(int(group_file['file_config_json']['data']['short']['grid_span'] * 100)) + "%",
            "s_TP"  : str(round(group_file['file_config_json']['data']['short']['min_markup'] * 100,2)) + "% /"+str(round(group_file['file_config_json']['data']['short']['markup_range'] * 100,2))+"%/",

            
        }

        if only_trash:
            if (strat_info['categ'] == 'xx_trash'):
                strat_info['categ'] = group_file['file_config_json']['file'].replace(base_dir, '').strip("/").split("/")[1]
                data_list.append(strat_info)
        else:
            if not (strat_info['categ'] == 'xx_trash'):
                data_list.append(strat_info)
    
    df = pd.DataFrame(data_list)
    # df.sort_values(by=[ 'adg %', 'gain %'], ascending=[ False, False], inplace=True)
    # df.sort_values(by=[ 'categ', 'balance', 'op_coin', 'l_gridspan'], ascending=[ True, False, False, False], inplace=True)
    df.sort_values(by=[ 'categ', 'l_bt_adg'], ascending=[ True, False], inplace=True)

    return df
        



git_folder     = os.path.realpath("./../configs/live/PBSO/")
git_directory  = os.path.realpath("./../configs/live/PBSO/.git")

if not os.path.exists(git_folder):
    os.makedirs(git_folder)

if not os.path.exists(git_directory):
    # Repo don't exist
    try:
        print("Cloning repo from Github : https://github.com/tedyptedto/pbos.git")
        Repo.clone_from('https://github.com/tedyptedto/pbos.git', git_folder)
    except:
        print("End of process")
        exit("WARNING => Initalisation needed : The directory " + git_folder + " must be empty. Rename it and lunch again this script. And after, past your directories in the new PBSO directory. And run again this script.")


def generateAutoFiles():
    ######################
    # Generate the ReadMe info
    ######################

    df = generateReadme()
    tableau_beautiful = str(tabulate(df, headers='keys', tablefmt='github', showindex=False))

    df_trash = generateReadme(only_trash=True)
    tableau_beautiful_trash = str(tabulate(df_trash, headers='keys', tablefmt='github', showindex=False))

    readme = git_folder + "/README.md"
    text_file = open(readme, "w")
    n = text_file.write('''# PBOS - PassivBotOnlyStrategy - PassivBot Strategies

[CSV Version](https://github.com/tedyptedto/pbos/blob/main/strategy_list.csv)

[README Full Screen](https://github.com/tedyptedto/pbos/blob/main/README.md)

''' + tableau_beautiful + 
# '''

# # xx_Trash PassivBot (old) Strategies :

# [README Full Screen](https://github.com/tedyptedto/pbos/blob/main/README.md)

# ''' + tableau_beautiful_trash +
""
)
    text_file.close()

    df.drop(columns=['info'])
    df.to_csv(git_folder + "/strategy_list.csv") 
    # content2=tabulate(df, headers='keys', tablefmt="tsv")
    # text_file=open(readme + ".tabulated.csv","w")
    # text_file.write(content2)
    # text_file.close()

if test_mode:
    print("Generate Auto files (readme and csv)")
    generateAutoFiles()
    exit()

try:
    print("Now repository exist, cool :)")
    repo = Repo(git_directory)
    origin = repo.remote(name='origin')

    print("Initialize auto generated files")
    repo.git.checkout('README.md')
    repo.git.checkout('strategy_list.csv')

    print("Pull new strategies")
    origin.pull()

    print("Generate Auto files (readme and csv)")
    generateAutoFiles()

    print("Add new files")
    repo.git.add('--all')
    COMMIT_MESSAGE = input('Wath are you adding to the GitHub repo (Commit comment) ? ')
    print("Commit files")
    repo.index.commit(COMMIT_MESSAGE)
    origin = repo.remote(name='origin')
    print("Push to github")
    print('Information for FIRST USE :')    
    print("You will be asked to enter your github login and a password")
    print("Password is in fact a personnal token, this how you can create it : https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
    origin.push()
    print('All is ok !')  
except Exception as e:
    print(e)
    print('--- INFO ---')    
    print('Some error occured while pushing the code')    
    print("If tou have trouble by login to github, use a personnal token : https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
