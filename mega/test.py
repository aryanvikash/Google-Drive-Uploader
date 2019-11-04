import mega

m = Mega.from_credentials("followaryan8@gmail.com","Vikash@12")
                    filename=m.download_from_url(url)
                    print("Downloading Complete Mega :", filename)