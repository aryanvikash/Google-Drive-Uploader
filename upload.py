#!/usr/bin/env python3
import argparse
import json
import os
import os.path as path
import re
from creds import Creds
from plugins import TEXT
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
drive: GoogleDrive
http = None
initial_folder = None


def upload(filename: str, update, context, parent_folder: str = None) -> None:

    FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
    drive: GoogleDrive
    http = None
    initial_folder = None
    gauth: drive.GoogleAuth = GoogleAuth()

    ID = update.message.from_user.id
    ID = str(ID)
    gauth.LoadCredentialsFile(
        path.join(path.dirname(path.abspath(__file__)), ID))

    if gauth.credentials is None:
        print("not Auth Users")
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
        gauth.SaveCredentialsFile(
            path.join(path.dirname(path.abspath(__file__)), ID))
    else:
        # Initialize the saved creds
        gauth.Authorize()
    drive = GoogleDrive(gauth)
    http = drive.auth.Get_Http_Object()
    if not path.exists(filename):
        print(f"Specified filename {filename} does not exist!")
        return
    # print(filename)
    
    if not Creds.TEAMDRIVE_FOLDER_ID :

        if parent_folder:

                # Check the files and folers in the root foled
                file_list = drive.ListFile(
                    {'q': "'root' in parents and trashed=false"}).GetList()
                for file_folder in file_list:
                    if file_folder['title'] == parent_folder:
                        # Get the matching folder id
                        folderid = file_folder['id']
                        # print(folderid)
                        print("Folder Already Exist  !!  Trying To Upload")
                        # We need to leave this if it's done
                        break
                else:
                    # Create folder
                    folder_metadata = {'title': parent_folder,
                                       'mimeType': 'application/vnd.google-apps.folder'}
                    folder = drive.CreateFile(folder_metadata)
                    folder.Upload()
                    folderid = folder['id']
                    # Get folder info and print to screen
                    foldertitle = folder['title']
                    # folderid = folder['id']
                    print('title: %s, id: %s' % (foldertitle, folderid))

    file_params = {'title': filename.split('/')[-1]}
    
    if Creds.TEAMDRIVE_FOLDER_ID :
        file_params['parents'] = [{"kind": "drive#fileLink", "teamDriveId": Creds.TEAMDRIVE_ID, "id":Creds.TEAMDRIVE_FOLDER_ID}]
        
    else:
        if parent_folder:
            file_params['parents'] = [{"kind": "drive#fileLink", "id": folderid}]
        
    file_to_upload = drive.CreateFile(file_params)
    file_to_upload.SetContentFile(filename)
    try:
        file_to_upload.Upload(param={"supportsTeamDrives" : True , "http": http})
        
        
    except Exception as e:
        print("upload",e)
    if not Creds.TEAMDRIVE_FOLDER_ID:
        file_to_upload.FetchMetadata()
        file_to_upload.InsertPermission({
        'type':  'anyone', 'value': 'anyone', 'role':  'reader', 'withLink': True
    })
        
    return file_to_upload['webContentLink']
