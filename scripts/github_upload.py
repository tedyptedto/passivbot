from git import Repo
import os

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
        exit("The directory " + git_folder + " must be empty. Rename it and lunch again.")

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
