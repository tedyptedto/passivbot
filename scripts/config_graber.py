import glob
import os
import requests, zipfile, io
from colorama import Fore, Style

zip_files = [

            # {'Name': 'MDCL', 'url': 'https://github.com/Skanouch/passivbot/archive/refs/heads/master.zip'}, 
            # {'Name': 'hoeckxer', 'url': 'https://github.com/hoeckxer/passivbot_configs/archive/refs/heads/main.zip'}, 

            {'Name': 'Scud', 'url': 'https://github.com/Scud0/pb/archive/refs/heads/main.zip'}, 
            {'Name': 'Enarjord', 'url': 'https://github.com/enarjord/passivbot/archive/refs/heads/master.zip'}, 
            {'Name': 'DotCom', 'url': 'https://github.com/raftheunis87/pb-configs/archive/refs/heads/main.zip'}, 
            {'Name': 'Flyingtoaster', 'url': 'https://github.com/donewiththedollar/passivbot_v5.8.0/archive/refs/heads/main.zip'}, 
            {'Name': 'donewiththedollar', 'url': 'https://github.com/donewiththedollar/passivbot_optimizations/archive/refs/heads/main.zip'}, 
            {'Name': 'JohnKearney1', 'url': 'https://github.com/JohnKearney1/PassivBot-Configurations/archive/refs/heads/main.zip'},
            {'Name': 'NaiMul', 'url': 'https://github.com/Nai-mul/passivbot_configs/archive/refs/heads/main.zip'}, 
            {'Name': 'RustyCZ', 'url': 'https://github.com/RustyCZ/pb-configs/archive/refs/heads/main.zip'}, 
            {'Name': 'jnkxnxx', 'url': 'https://github.com/jnkxnxx/pb-configs/archive/refs/heads/main.zip'}, 
        
]


print('Récupération de la liste total en provenance de https://pbconfigdb.scud.dedyn.io/')

# URL à récupérer
url = "https://pbconfigdb.scud.dedyn.io/result/data.json"

# Faire une requête GET pour obtenir le contenu JSON
response = requests.get(url)

if response.status_code == 200:
    data = response.json()  # Convertir la réponse en JSON

    # Créer un ensemble pour stocker les débuts uniques des URLs 'source'
    unique_sources = set()

    # Parcourir les données JSON pour extraire les débuts d'URL uniques
    for source in data:
        source_url_parts = source.get('source', '').split('/')
        if len(source_url_parts) >= 5:
            unique_sources.add("/".join(source_url_parts[:5]))

    # Afficher les débuts uniques des URLs 'source'
    # Vérification de la présence des débuts d'URL dans zip_files
    # Vérification de la présence des débuts d'URL dans zip_files
    for source in unique_sources:
        found = any(source in item['url'] for item in zip_files)
        if found:
            print(f"{source}" + Fore.GREEN + " OK Contenu dans la liste" + Style.RESET_ALL)
        else:
            print(f"{source}" + Fore.RED + " KO contenu dans zip_files" + Style.RESET_ALL)
            exit()
else:
    print("La requête n'a pas abouti :", response.status_code)



print("Repository to Download")
print(zip_files)

dir_to_unpack = "../configs/live/PBSO/"

if not os.path.exists(dir_to_unpack) :
    print('Dir not exist')
    exit()

print("OK : Base Directory exist")

dir_to_unpack = dir_to_unpack + "configs/"

if not os.path.exists(dir_to_unpack) :
    os.makedirs(dir_to_unpack)

print("OK : Directory exist ", dir_to_unpack)


for zip_file in zip_files:
    name = zip_file['Name']
    url = zip_file['url']

    print("--------------------")
    print("OK : Working on ", name, url)

    dir_to_unpack_by_user = dir_to_unpack+"/"+name+"/"

    if not os.path.exists(dir_to_unpack_by_user) :
        os.makedirs(dir_to_unpack_by_user)

    print("OK : Directory created ", dir_to_unpack_by_user)

    r = requests.get(url)
    print("OK : Downloading ")

    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(dir_to_unpack_by_user)
    print("OK : Extracting ")

list = glob.glob(dir_to_unpack+"/**/*", recursive=True)
for files in list :

    if (not os.path.isfile(files)):
        continue

    if (files.endswith('.json')):
        print("OK Finding : ", files)
    else:
        print("KO TO delete : ", files) 
        os.unlink(files)
    #shutil.rmtree(to_delete)