from git import Repo
import os
import glob
import hjson
from pathlib import Path

# @TODO : avoir un affichage plus jolie dans le readme
# @TODO : ajouter bankrupt comme info
# @TODO : ajouter le nb jours plutot que les dates

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


        group_file = {
            "file_config_json" : file,
            "file_result_txt" : dir + "/result.txt",
            "file_backtest_hjson" : file_backtest_hjson,
            "file_harmony_hjson" : file_harmony_hjson,
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
                                    'data' : hjson.load(open(group_file[key], encoding="utf-8")),
                    }
                else:
                    group_file[key] = {
                                    'file' : group_file[key],
                                    'data' : Path(group_file[key]).read_text(),
                    }

        if not all_files_exist:
            continue

        ftxt = group_file['file_result_txt']['data']
        
        strat_info = {
            "starting_balane" : group_file['file_backtest_hjson']['data']['starting_balance'],
            "start_date" : group_file['file_backtest_hjson']['data']['start_date'],
            "end_date" : group_file['file_backtest_hjson']['data']['end_date'],
            "long" : group_file['file_config_json']['data']['long']['enabled'],
            "long_gridspan" : str(int(group_file['file_config_json']['data']['long']['grid_span'] * 100)) + "%",
            "long_we" : group_file['file_config_json']['data']['long']['wallet_exposure_limit'],
            "Long_Average daily gain" : getValueInResultTxt(ftxt, 'Average daily gain', 'long'),
            "Long_Total gain"  : getValueInResultTxt(ftxt, 'Total gain', 'long'),


            "short" : group_file['file_config_json']['data']['short']['enabled'],
            "short_gridspan" : str(int(group_file['file_config_json']['data']['short']['grid_span'] * 100)) + "%",
            "short_we" : group_file['file_config_json']['data']['short']['wallet_exposure_limit'],
            "Short_Average daily gain" : getValueInResultTxt(ftxt, 'Average daily gain', 'short'),
            "Short_Total gain"  : getValueInResultTxt(ftxt, 'Total gain', 'short'),
            
        }

        print(group_file['file_config_json']['file'].replace(base_dir, ''), "\n" , strat_info, "\n")
        







# generateReadme()
# exit()


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

print("Now repository exist, cool :)")


try:
    repo = Repo(git_directory)
    origin = repo.remote(name='origin')
    print("Pull new strategies")
    origin.pull()
    print("Add new files")
    repo.git.add('--all')
    COMMIT_MESSAGE = input('Wath are you adding to the GitHub repo ?')
    print("Commit files")
    repo.index.commit(COMMIT_MESSAGE)
    origin = repo.remote(name='origin')
    print("Push to github")
    origin.push()
except:
    print('Some error occured while pushing the code')    
    print("If tou have trouble by login to github, use a personnal token : https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
