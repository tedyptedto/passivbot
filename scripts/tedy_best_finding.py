import glob
import os
import subprocess
import json
import pandas as pd
from tabulate import tabulate
import argparse
import os
import hjson
from tqdm import tqdm
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

limit_for_test = False
# limit_for_test = True


# Fonction pour parcourir les fichiers et extraire result.sharpe_ratio_long
def parcourir_et_afficher_sharpe_ratio_long(repertoire):
    resultats = []  # Liste pour stocker les résultats

    # Parcourir les fichiers
    for dossier_racine, dossiers, fichiers in os.walk(repertoire):
        for nom_fichier in fichiers:
            if nom_fichier == 'result.json':
                chemin_fichier = os.path.join(dossier_racine, nom_fichier)
                with open(chemin_fichier, 'r') as file:
                    try:
                        data = json.load(file)
                        sharpe_ratio_long = data.get('result', {}).get('sharpe_ratio_long')
                        if sharpe_ratio_long is not None:
                            coin = chemin_fichier.replace(repertoire, '').split('/')[1]
                            resultats.append((sharpe_ratio_long, coin))  # Ajouter le tuple (sharpe_ratio_long, coin)
                    except json.JSONDecodeError as e:
                        print(f"Erreur de décodage JSON pour le fichier {chemin_fichier} : {e}")

    # Trier et afficher les résultats du plus grand au plus petit sharpe_ratio_long
    resultats_tries = sorted(resultats, reverse=True)  # Tri décroissant
    for sharpe_ratio, coin in resultats_tries:
        print(f"sharpe_ratio_long : {coin} : {sharpe_ratio}")

# loop on all strategy


# ../configs/live/PBSO/BT_UNIFORMISED/bt_2020-01-01_2022-10-13_1000_1_XRPUSDT_LTCUSDT_ADAUSDT_DOTUSDT_UNIUSDT_DOGEUSDT_MATICUSDT_BNBUSDT_SOLUSDT_TRXUSDT_AVAXUSDT_USDCUSDT/

# dir_name = 'FILLED_AFTER'
dir_base = "../configs/live/PBSO/BT_UNIFORMISED/"

# repertoire_actuel = os.getcwd()
# print("Le répertoire actuel est :", repertoire_actuel)
# exit()

# Vérification que dir_base est bien un répertoire
if not os.path.isdir(dir_base):
    print("Le chemin spécifié n'est pas un répertoire valide.")
else:
    while True:
        print(f"Liste des répertoires dans {dir_base} :")
        repertoires = [d for d in os.listdir(dir_base) if os.path.isdir(os.path.join(dir_base, d))]

        for index, repertoire in enumerate(repertoires, start=1):
            print(f"{index}. {repertoire}")

        if len(repertoires) > 1:
            choix = input("Veuillez choisir un répertoire en entrant le numéro correspondant : ")
        else:
            choix = 1
        try:
            choix = int(choix)
            if 1 <= choix <= len(repertoires):
                base_dir = os.path.join(dir_base, repertoires[choix - 1])
                # Réalisez vos traitements avec le nouveau chemin sélectionné (base_dir)
                print(f"Vous avez choisi : {base_dir}")
                break  # Sortir de la boucle une fois que le choix est valide
            else:
                print("Choix invalide.")
        except ValueError:
            print("Veuillez entrer un numéro valide.")


# base_dir = os.path.realpath(dir_base + "BT_UNIFORMISED/" + dir_name + "/")
base_dir = os.path.realpath(base_dir + "/")
# find all strategies

if not os.path.exists(base_dir) :
    print('Dir not exist')
    exit()

strats_dirs = glob.glob(base_dir + '/strat_*')

array_info = []

def addTo(object, key, value):

    if key in ["avg_hrs_stuck_avg", "avg_max_stuck"]:
        if value == "NaN,":
            value = 9999

    if key in ["low_equ_bal"]:
        if value == "NaN,":
            value = 0

    if key in object:
        object[key] += value
    else:
        object[key] = value
    return object

def minTo(object, key, value):
    if key in object:
        object[key] = min(object[key], value)
    else:
        object[key] = value
    return object

# progress_strats_dirs = 0
# progress_nb_full = len(strats_dirs)
compteur = 0

# Dictionnaire pour stocker le meilleur sharpe_ratio_long pour chaque symbol
meilleur_sharpe_ratio = {}

for strat_dir in tqdm(strats_dirs):
    # find all backtests
    # progress_strats_dirs = progress_strats_dirs +  1
    # print("(" + str(progress_strats_dirs) + " / " + str(progress_nb_full) +")" + strat_dir)

    results_file = glob.glob(strat_dir + '/**/result.json', recursive=True)

    object={}
    strat_name = os.path.realpath(strat_dir).replace(base_dir, '').strip("/").split("/")[0]

    nb_coins = len(results_file)

    compteur = compteur + 1
    if (compteur > 100) and (limit_for_test):
        break

    is_first = True
    for result_file in results_file:
        data = hjson.load(open(result_file, encoding="utf-8"))

        we_ratio = data['long']['wallet_exposure_limit']
        invert_we_ratio = 1 / data['long']['wallet_exposure_limit']

        if is_first:
            object['strat'] = str(strat_name.replace('strat_','')[:5])
            addTo(object, 'Path', result_file)
            addTo(object, 'au', (not (data['result']['n_unstuck_closes_long'] == 0)))
            is_first = False
            if 'grid_span' in data['long']:
                addTo(object, 'gs', int(data['long']['grid_span'] * 100))
            else:
                addTo(object, 'gs', -1)

        addTo(object, 's_k',   data['starting_balance'])
        
        addTo(object, 's_f_equ_long', 
                    (
                        (data['result']['final_equity_long'] -  data['result']['starting_balance'] ) * (invert_we_ratio) 
                    )  
            )
        
        addTo(object, 's_f_balance', 
                    (
                        (data['result']['final_balance_long'] -  data['result']['starting_balance']) * (invert_we_ratio)
                    )  
            )
        addTo(object, 's_loss', data['result']['loss_sum_long'] * (invert_we_ratio))
        addTo(object, 'low_equ_bal', data['result']['eqbal_ratio_min_long'])
        addTo(object, 'pa_dist_mean_long', data['result']['pa_distance_mean_long'])
        addTo(object, 'l_we', data['long']['wallet_exposure_limit'])
        addTo(object, 'we_ratio', we_ratio)
        addTo(object, 'adg_exposure', data['result']['adg_per_exposure_long'] * 100)
        addTo(object, 'n_days', data['n_days'])

        addTo(object, 'avg_max_stuck', data['result']['hrs_stuck_max_long'])
        addTo(object, 'avg_hrs_stuck_avg', data['result']['hrs_stuck_avg_long'])
        
        # addTo(object, 'pa_distance_max_long', data['result']['pa_distance_max_long'])
        addTo(object, 'sharpe', data['result']['sharpe_ratio_long'])
        addTo(object, 'sum_sharpe', data['result']['sharpe_ratio_long'])
        

        minTo(object, 'most_loss', data['result']['net_pnl_plus_fees_long'])

        sharpe_ratio_long = data['result']['sharpe_ratio_long']
        symbol = data['symbol']

        if sharpe_ratio_long is not None and symbol is not None:
            if symbol not in meilleur_sharpe_ratio or meilleur_sharpe_ratio[symbol]['sharpe_ratio'] < sharpe_ratio_long:
                meilleur_sharpe_ratio[symbol] = {'sharpe_ratio': sharpe_ratio_long, 'nom_fichier': result_file.replace(base_dir, '')}

    
    if nb_coins > 0:
        object['avg_hrs_stuck_avg']   = object['avg_hrs_stuck_avg'] / nb_coins
        object['avg_max_stuck']   = object['avg_max_stuck'] / nb_coins
        object['pa_dist_mean_long']   = object['pa_dist_mean_long'] / nb_coins
        object['low_equ_bal'] = object['low_equ_bal'] / nb_coins
        object['adg_exposure'] = object['adg_exposure'] / nb_coins
        # object['pa_distance_max_long'] = object['pa_distance_max_long'] / nb_coins
        object['n_days'] = object['n_days'] / nb_coins
        object['l_we'] = object['l_we'] / nb_coins
        object['sharpe'] = object['sharpe'] / nb_coins

    array_info.append(object)

df = pd.DataFrame(array_info)

# df['s_loss']     = int(df['s_loss'])       
# df['ratio_loss']     = abs(df['s_loss']) / df['s_f_equ_long']       
# df['ratio_dist'] = df['s_f_equ_long'] / df['s_gain']       
# df['krishn_ratio'] = df['s_f_equ_long'] * df['low_equ_bal']       

df['valid_for_me'] = (  True
                        # (df['ratio_loss'] < 0.20) 
                        # & 
                        # (df['ratio_dist'] < 0.70) 
                        # & 
                        # (df['low_equ_bal'] > 4)
                        # &
                        # (df['low_equ_bal'] > 6)
                        # &
                        # (df['sum_final_equity_long'] > 0)
                        # &
                        # (df['gridspan'] >= 20)
                        # &
                        # # &
                        # # (df['sum_final_equity_long'] > 20000)
                        # &
                        # (df['pa_distance_mean_long'] < 5)
                        # &
                        # (df['pa_distance_mean_long'] < 0.20)
                        # &
                        # (df['au'] == True)
                        )
#(df['Lowest equity/balance ratio'] > 6) #& (df['pa_distance_mean_long'] < 1)
# df['valid_for_me'] = True

df = df[df.valid_for_me == True]

df_cleaned = df.drop(columns=['valid_for_me', 'gs', 'au', 'we_ratio', 's_k', 'Path', 'l_we', 'pa_dist_mean_long'])


# print("---------------------")
# print("Top 20 : Sorted by pa_distance_max_long")
# df.sort_values(by=[ 'pa_distance_max_long'], ascending=[True], inplace=True)
# df1 = df.head(20)
# print(tabulate(df1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

# print("---------------------")
# print("Top 20 : Sorted by most_loss")
# df.sort_values(by=[ 'most_loss'], ascending=[False], inplace=True)
# df1 = df.head(20)
# print(tabulate(df1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

# print("---------------------")
# print("Top 20 : Sorted by less avg_hrs_stuck_avg")
# df.sort_values(by=[ 'avg_hrs_stuck_avg'], ascending=[True], inplace=True)
# df1 = df.head(20)
# print(tabulate(df1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

# print("---------------------")
# print("Top 20 : Sorted by less avg_max_stuck")
# df.sort_values(by=[ 'avg_max_stuck'], ascending=[True], inplace=True)
# df1 = df.head(20)
# print(tabulate(df1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

print("---------------------")
print("Top 20 : Sorted by s_f_balance")
df_cleaned.sort_values(by=[ 's_f_balance', 's_f_equ_long'], ascending=[False, False], inplace=True)
df1 = df_cleaned.head(20)
print(tabulate(df1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".5f"))

print("---------------------")
print("Top 20 : Sorted by s_f_equ_long")
df_cleaned.sort_values(by=[ 's_f_equ_long', 's_f_balance'], ascending=[False, False], inplace=True)
df2 = df_cleaned.head(20)
print(tabulate(df2, headers='keys', tablefmt='psql', showindex=False, floatfmt=".5f"))

print("---------------------")
print("Top 20 : Sharpe ratio")
df_cleaned.sort_values(by=[ 'sharpe'], ascending=[False], inplace=True)
df3 = df_cleaned.head(20)
print(tabulate(df3, headers='keys', tablefmt='psql', showindex=False, floatfmt=".5f"))

# print("---------------------")
# print("Top 20 : Sorted by adg_exposure")
# df.sort_values(by=[ 'adg_exposure'], ascending=[False], inplace=True)
# df2 = df.head(20)
# print(tabulate(df2, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

# print("---------------------")
# print("Common on the 2 top 10 ordered by adg exposure")
# s1 = pd.merge(df1, df2, how='inner', on=['strat'])
# s1.drop(s1.columns[s1.columns.str.contains('_y$')], axis=1, inplace=True)
# s1.sort_values(by=[ 'adg_exposure_x'], ascending=[False], inplace=True)
# print(tabulate(s1, headers='keys', tablefmt='psql', showindex=False, floatfmt=".2f"))

# Affichage des meilleurs sharpe_ratio_long pour chaque symbol à la fin
for symbol, info in sorted(meilleur_sharpe_ratio.items(), key=lambda x: x[1]['sharpe_ratio'], reverse=True):
    print(f"'{symbol}', Best Sharpe_ratio_long : {info['sharpe_ratio']} [{info['nom_fichier']}]")

# df.to_csv(dir_base + 'tedy_best_finding_' + dir_name + '.csv') 

df['strat'] = df['strat'].astype(str)

# df_combined = pd.concat([df1, df2, df3], ignore_index=True)
# df_filtre = df[df['strat'].isin(df_combined['strat'])]
df_filtre = df

try:
    while True:
        # Création d'un ensemble des noms de stratégies pour la complétion
        # df_filtre['strat'] = df_filtre['strat'].astype(str)
        # df_filtre.loc[:, 'strat'] = df_filtre['strat'].astype(str)

        strategies = set(df_filtre['strat'].tolist())
        strategy_completer = WordCompleter(strategies)

        # Demander à l'utilisateur quelle stratégie il souhaite voir
        selected_strategy = prompt('Veuillez choisir une stratégie : ', completer=strategy_completer)
        # print("\033[F\033[K", end="")  # Retour à la ligne et effacement

        # Vérifier si la stratégie choisie est présente dans le DataFrame
        if selected_strategy in strategies:
            # Récupérer le chemin associé à la stratégie sélectionnée
            path = df_filtre.loc[df_filtre['strat'] == selected_strategy, 'Path'].values[0]

            # Remonter de trois niveaux pour obtenir le répertoire désiré
            repertoire_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path))))

            # Ouvrir le répertoire désiré dans l'explorateur de fichiers
            if os.path.exists(repertoire_parent):
                parcourir_et_afficher_sharpe_ratio_long(repertoire_parent)
                os.system(f'xdg-open "{repertoire_parent}"')
except KeyboardInterrupt:
    print("Interruption clavier détectée. Arrêt du programme.")