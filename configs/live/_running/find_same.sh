#!/bin/bash

# Chemin vers le répertoire contenant les fichiers à traiter
directory="../PBSO/BT_UNIFORMISED/bt_2020-01-01_2023-12-18_1000_1/"

# Recherche des fichiers .json dans les sous-répertoires directs
files=$(find ./ -maxdepth 2 -mindepth 2 -type f -name "*.json")

# Parcours de chaque fichier trouvé
for file in $files; do
    # Récupération du nom du fichier sans le chemin
    filename=$(basename -- "$file")
    
    # Exécution de la commande python pour chaque fichier
    echo "python3 find_same.py -orig $file -directory $directory"
    python3 find_same.py -orig "$file" -directory "$directory"

    # Ajout d'un saut de ligne pour une meilleure lisibilité
    echo ""
done