from git import Repo
import os
import glob
import hjson
from pathlib import Path
import pandas as pd
from tabulate import tabulate


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

def generateReadme():
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

        op_coin = len(group_file['bulk_optimisation_hjson']['data']['coin_list'])


        parent_dir = group_file['file_config_json']['file'].replace(base_dir, '').strip("/").split("/")[0]

        strat_info = {
            "conf" : "[conf](https://github.com/tedyptedto/pbos/blob/main/" + group_file['file_config_json']['file_r'] + ")",
            "bulk" : "[bulk](https://github.com/tedyptedto/pbos/blob/main/" + group_file['bulk_optimisation_hjson']['file_r'] + ")",
            "categ" : parent_dir,
            "balance" : group_file['file_backtest_hjson']['data']['starting_balance'],
            "op_coin" : op_coin,
            "bt_coin" : getValueInResultTxt(ftxt, 'Symbol', 'long'),
            "days" : int(float(getValueInResultTxt(ftxt, 'No. days', 'long'))),
            "end" : group_file['file_backtest_hjson']['data']['end_date'].replace('-', '/').strip(','),

            "long" : group_file['file_config_json']['data']['long']['enabled'],
            "l_gridspan" : str(int(group_file['file_config_json']['data']['long']['grid_span'] * 100)) + "%",
            "l_we" : group_file['file_config_json']['data']['long']['wallet_exposure_limit'],
            "l_adg" : getValueInResultTxt(ftxt, 'Average daily gain', 'long'),
            "l_gain"  : getValueInResultTxt(ftxt, 'Total gain', 'long'),
            "l_bkrupt"  : getValueInResultTxt(ftxt, 'Closest bankruptcy', 'long'),


            "short" : group_file['file_config_json']['data']['short']['enabled'],
            "s_gridspan" : str(int(group_file['file_config_json']['data']['short']['grid_span'] * 100)) + "%",
            "s_we" : group_file['file_config_json']['data']['short']['wallet_exposure_limit'],
            "s_adg" : getValueInResultTxt(ftxt, 'Average daily gain', 'short'),
            "s_gain"  : getValueInResultTxt(ftxt, 'Total gain', 'short'),
            "s_bkrupt"  : getValueInResultTxt(ftxt, 'Closest bankruptcy', 'short'),
            
        }

        if not (strat_info['categ'] == 'xx_trash'):
            data_list.append(strat_info)
        # print(group_file['file_config_json']['file'].replace(base_dir, ''), "\n" , strat_info, "\n")
    return data_list
        



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

    a_info_strat = generateReadme()
    # a_info_strat_gh = []
    # for info_strat in a_info_strat:
    #     a_sub_info_strat_gh = {}
    #     for key in info_strat:
    #         a_sub_info_strat_gh["<sub>" + str(key) + "</sub>"] = "<sub>" + str(info_strat[key]) + "</sub>"
    #     a_info_strat_gh.append(a_sub_info_strat_gh)

    df = pd.DataFrame(a_info_strat)
    # df.sort_values(by=[ 'adg %', 'gain %'], ascending=[ False, False], inplace=True)
    df.sort_values(by=[ 'categ', 'balance', 'op_coin', 'l_gridspan'], ascending=[ True, False, False, False], inplace=True)
    tableau_beautiful = str(tabulate(df, headers='keys', tablefmt='github'))
    # print(tableau_beautiful)

    readme = git_folder + "/README.md"
    text_file = open(readme, "w")
    n = text_file.write('''# PBOS - PassivBotOnlyStrategy
PassivBot Strategies :

[CSV Version](https://github.com/tedyptedto/pbos/blob/main/strategy_list.csv)

[README Full Screen](https://github.com/tedyptedto/pbos/blob/main/README.md)

''' + tableau_beautiful)
    text_file.close()

    df.to_csv(git_folder + "/strategy_list.csv") 
    # content2=tabulate(df, headers='keys', tablefmt="tsv")
    # text_file=open(readme + ".tabulated.csv","w")
    # text_file.write(content2)
    # text_file.close()

print("Now repository exist, cool :)")

try:
    repo = Repo(git_directory)
    origin = repo.remote(name='origin')
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
except:
    print('Some error occured while pushing the code')    
    print("If tou have trouble by login to github, use a personnal token : https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
