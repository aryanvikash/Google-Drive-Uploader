from time import time
import subprocess
import os
import re
import wget
import os.path




def download_wget(url):
    wget_start = time()
    proc = subprocess.Popen(["wget", url])
    proc.communicate()
    # print("proc",com)
    wget_end = time()
    print("wget -> %s" % (wget_end - wget_start))



if __name__ == '__main__':
    # url ="https://raw.githubusercontent.com/out386/aria-telegram-mirror-bot/master/README.md"
    try:
            print(download(url))
            
    except Exception  as e :
            filename = wget.download(url)
            print(filename)
