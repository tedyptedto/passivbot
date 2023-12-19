import glob
import os
import requests, zipfile, io

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