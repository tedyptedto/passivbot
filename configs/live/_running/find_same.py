# Prompt :
# je voudrait un programme Python qui fonctionne comme ceci :

# python3 find_same.py -orig chemin/fichier.json -directory chemin2/chemin3

# je veux que le programme cherche dans "chemin2/chemin3" tous les fichiers et que pour chaque fichier il étudie quel fichier ressemble le plur au fichier "chemin/fichier.json", le but étant qu'il crée un score de ressemblance.
# Et au fur et à mesure de sa recherche, je veux qu'il affiche quel fichier lui semble le plus ressemblant d'après tous les fichiers qu'il a parcouru et qu'il affiche aussi le score de ressemblance.
# Et qu'a la fin du coup il indique le score du fichier qui a été trouvé.

import os
import json
import argparse
from difflib import SequenceMatcher
import shutil

def calculate_similarity(file1, file2):
    """
    Calculate similarity between two JSON files using SequenceMatcher.
    """
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        json1 = json.load(f1)
        json2 = json.load(f2)
        matcher = SequenceMatcher(None, json.dumps(json1), json.dumps(json2))
        return matcher.ratio()

def find_most_similar(original_file, directory):
    """
    Find the most similar file in the directory to the original file.
    """
    max_similarity = 0
    most_similar_file = None
    total_dirs = sum(1 for _ in os.walk(directory)) - 1  # Total number of directories (excluding the root directory)
    processed_dirs = 0  # Number of processed directories

    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            processed_dirs += 1
            progress = processed_dirs / total_dirs * 100
            print(f"\rProgress: [{int(progress)}%] [{'#' * int(progress / 10)}{' ' * (10 - int(progress / 10))}]", end='', flush=True)

        for file in files:
            current_file = os.path.join(root, file)
            if current_file.endswith('.json') and current_file != original_file:
                similarity = calculate_similarity(original_file, current_file)
                if similarity == 1.0:  # If files are identical, exit
                    return current_file, similarity
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_file = current_file
                    print(f"{most_similar_file}, Score: {max_similarity}")

    return most_similar_file, max_similarity


def copy_files_to_original_directory(original_file, most_similar_file):
    """
    Copy files from the directory of the most similar file to the original file's directory.
    """
    original_directory = os.path.dirname(original_file)
    similar_directory = os.path.dirname(most_similar_file)
    destination_directory = os.path.join(original_directory, os.path.basename(original_file).split('.')[0])
    
    # Copy the entire directory recursively
    shutil.copytree(similar_directory, destination_directory, dirs_exist_ok=True)

def play_notification_sound():
    os.system("echo -e '\a'")

def main():
    parser = argparse.ArgumentParser(description="Find the most similar file to a given JSON file in a directory.")
    parser.add_argument("-orig", dest="original_file", help="Path to the original JSON file", required=True)
    parser.add_argument("-directory", dest="directory", help="Path to the directory containing JSON files", required=True)
    args = parser.parse_args()

    original_file = args.original_file
    directory = args.directory

    most_similar_file, max_similarity = find_most_similar(original_file, directory)


    print(f"\nMost similar file found: {most_similar_file}, with a similarity score of {max_similarity}")

    # Open file explorers in the directories of the original file and the most similar file
    # os.system(f"xdg-open {os.path.dirname(original_file)}")
    # os.system(f"xdg-open {os.path.dirname(most_similar_file)}")

    # Copy files from the directory of the most similar file to the original file's directory
    print("\nFiles copying to the original directory.")
    copy_files_to_original_directory(original_file, most_similar_file)

    play_notification_sound()
    
if __name__ == "__main__":
    main()
