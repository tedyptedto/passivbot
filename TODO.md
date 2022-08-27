


@DONE : i will run again the full backtest of all strats
@DONE : git add --all / git comit / git push Puis delete nettoyer + @TODO
@DONE : uniformized backtest, can be more speedy with running backtest in //
        https://gist.github.com/davidgardenier/c4008e70eea93e548533fd9f93a5a330
        Problem is for cache files and if there is other data used from the previous bt
@DONE : en local sur machine faire un git pull
@DONE : mettre à jour les script pour avoir le uniformized en 3 processeurs
@DONE : Ajouter le gridspan, sum loss
@DONE : ratio, ratio between sum(loss)/sum(profit)

@DONE : faire un pull puis un nouveau uniformised.py
@DONE : mettre à jour le Readme pour tout présenter
        revoir le readme avec les nouveaux CSV
@DONE : delete the old directory of old backtest (but make a save on your laptop)
cancel =>     delete the old CSV file ? or not ? (Make a Save in local computer)

@DONE : and check the eb1ed strategy and on coin i am running check the jpg

@FORGET : fait chier je me suis trompé de dates !!! car je voulais comparer avec maintenant et les dip
        surtout sur ma stratégie...

old => 1483b
@TODO : choose a new strategy => b4483

@TODO : and after, compare again reality vs backtest

Question :
@TODO : si bull, couper le AU ?


@TODO : demande dotcom
A cool feature would be to run the inspect_opt_results.py multiple times after the optimizer has done it's job
so in the bulk config, you could add the different score formulas you want to do the inspect on
["adgPADstd", "adg_mean", "adg_min", "adgPADmean", "adgrealizedPADmean", "adgrealizedPADstd"]
these are all the options you can choose
I mainly use "adgrealizedPADmean" and "adgrealizedPADstd"
and then the inspect step will run multiple times, generating different configs
then the backtest ofcourse needs to run multiple times
probably the output in the resulting configs folder should change as well then
for example
GRTUSDT_20220808113925_7b781/adgrealizedPADstd/config.json
GRTUSDT_20220808113925_7b781/adgrealizedPADstd/result.txt
etc...
and make a subfolder per score formula
as an additional improvement, we can add the -p option as well to the inspect

@TODO : demande MDCL
clairement
j'ai eu une idée a ajouter sur le script bulk. Car je vais utiliser le nouveau serveur de krishna pour faire les 3 version des harmony sur les 120 coins binance. Comme je les lancerais toutes les semaines ou deux, ce serait bien de pouvoir effacer les données des bougies uniquement si on change les dates.
Attend, je m'explique
quand on lance une opti avec de nouvelles dates, il telecharge les nouvelles données des dates selectionnée, une ofis qu'il la fait, il les compiles dans un gros fichier situé dans backtest/"coin"/caches/
qui ressemble a ceci
2019-11-01_2022-08-03_ohlcv_cache.npy
date de départ et date de fin
une fois que je change la date de fin pour tenir a jour les bougies, il me recrée un fichier mais ne supprime pas le précédent
afin de gagner ded l'espace disque, le script pourrait comporter un ligne lui demandant de verifier si les dates correspondent au fichier, si non, suppression
et reload des nouvelles données
car les opti que je vais lancer, seront en 1 sec
ca va etre assez FAT
et je vais les runs toutes les semaines ou 2


c'est absolument pas pressé, je n'ai pas encore le serveur, et le temps que je relance les batchs pas avant 2 semaines 😄
sorry, l'exemple du dessus sont les OHLCV, les ticks sont comme ceci
2019-11-01_2022-07-28_ticks_cache.npy 

