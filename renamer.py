import requests
from os import listdir
from os.path import isfile, join
import urllib.parse
import urllib.request
import os.path
import json
import re
import pandas as pd
import gzip
import shutil
from textblob import TextBlob
from argparse import ArgumentParser

#Arguments for program execution
parser = ArgumentParser(description='Loop throught movie directory and call IMDB API to find the exact title')

parser.add_argument("-d", "--dir", dest="dir", metavar='dir',
                    help="define the directory to search into", required=True)
parser.add_argument("-o", "--original", 
                    action="store_true", dest="getVO", default=False,
                    help="get original language title for corresponding --language, requires the download of a local IMDB database")                
parser.add_argument("-l", "--language",metavar='lang', dest="language", default="fr",
                    help="define the language for which original title is kept (default : 'fr', iso 639-1), requires --original")
parser.add_argument("-a", "--all",
                    action="store_true", dest="all", default=False,
                    help="iterate through every movie, even those already respecting the expected format")

args = parser.parse_args()

# Simple query yes / no 
def query_yn(question, default="yes"):
    """Ask a yes/no question via input() and return their answer."""

    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}

    while True:
        choice = input(question).lower()

        if default is not None and choice == "":
            return valid[default]

        if choice in valid:
            return valid[choice]

        print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

#Takes a IMDB response and parse it to obtain a list of movies name
def parse(x, file, df=None):
    
    arr=[]
    
    #If there is some results
    if 'd' in x:
        x = x["d"]
        for idx ,movie in enumerate(x):
            if 'q' in movie:
                #If results is a feature movie
                if movie["q"] == "feature":
                    
                    #If the movie have a year of release
                    if 'y' in movie:
                        
                        if args.getVO:
                            #Line of the found title in the local database
                            dfo = df.loc[df['tconst'] == movie['id']]

                            if not dfo.empty:           
                                #Original title
                                txt = TextBlob(dfo['originalTitle'].iloc[0])
                                #English title
                                name = dfo['primaryTitle'].iloc[0]
                                
                                #If the title length is greater or equal 3 - we check the langage of the title
                                #If the langage is the expected one from the user (default = 'fr'), then we keep the original title
                                if(len(txt) >= 3):
                                    lg = txt.detect_language()
                                    if lg == args.language:
                                        name = dfo['originalTitle'].iloc[0]

                        else:
                            name = movie['l']

                        name = name + " (" + str(movie['y']) + ")"

                        #Add the movie to the list
                        arr.append(name.replace(":", "").replace("?",""))
                        
                        #If the 1st result is already right, we don't look for others results
                        if name.replace(":", "").replace("?","") == file and idx == 0:
                            break
    return arr


myPath = args.dir
    
if not os.path.exists(myPath):
    print("Path : " + myPath + " - not found !")
    exit(1)


'''
    START LOCAL DATABASE - In this part we get the imdb local database
'''

df = None

if(args.getVO):

    tsv_path = os.path.dirname(os.path.realpath(__file__))
    tsv_file = os.path.join(tsv_path, 'data.tsv') 

    if(os.path.isfile(os.path.splitext(tsv_file)[0] + ".csv")):

        print("Loading local database...")
        df = pd.read_csv(os.path.splitext(tsv_file)[0] + ".csv")

    else:
        if not query_yn("No local database found, do you want to download it ? [Y/n]"):
            exit()

        print("Downloading...")
        urllib.request.urlretrieve ("https://datasets.imdbws.com/title.basics.tsv.gz", os.path.join(tsv_path, 'title.basics.tsv.gz'))
        
        print("Extracting...")
        with gzip.open(os.path.join(tsv_path, 'title.basics.tsv.gz'), 'rb') as f_in:
            with open(os.path.join(tsv_path, 'data.tsv'), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print("Sorting...")
        csv_table = pd.DataFrame()

        for chunk in pd.read_table(tsv_file, sep='\t', usecols=[0, 1, 2, 3], chunksize=50000):
            chunk = chunk[(chunk.titleType == 'movie')]
            chunk = chunk.drop(columns=['titleType'])
            csv_table = pd.concat([csv_table, chunk], ignore_index=True)

        print("Saving database...")
        csv_table.to_csv(os.path.join(tsv_path,'data.csv'),index=False)
        
        os.remove(os.path.join(tsv_path, 'title.basics.tsv.gz'))
        os.remove(tsv_file)
        
        df = csv_table
    
'''
    END LOCAL DATABASE
'''

print ("Starting to loop throught movies")

for f in listdir(myPath):
    if isfile(join(myPath, f)):
        
        #File name without extension
        ifile = os.path.splitext(f)[0]    
        
        #Search for the expected format
        search = re.search('^.*\([0-9]{4}\)$',ifile)
    
        #If it's not from the expected format or otpion --all is true
        if not search or args.all:
            
            # Remove useless caracs
            file = re.sub('\[.*\]','',ifile)
            file = re.sub('(M|m)(U|u)(L|l)(T|t)(I|i).*','',file)
            file = re.sub('(V|v)(O|o)(S|s)(T|t)(F|f)(R|r).*','',file)
            file = re.sub('avi.*','',file)
            file = re.sub('mkv.*','',file)
            file = re.sub('www.*','',file)
            file = re.sub('(H|h)(D|d).*','',file)
            file = re.sub('[0-9][0-9][0-9]([0-9])?p.*','',file)
            
            file = file.replace('.',' ')
            
            #Search for a date
            search = re.search('\(?[0-9]{4}\)?',file)
            if search:
                find = file.find(search.group())
                #If there is a date, we remove everything after the date
                if find != -1:
                    done = False;
                    if len(file) > find + len(search.group()):
                        if file[find+len(search.group())] == 'p': #If char p after date because it will be quality not date
                            file = file[0:find - 1]
                            done = True;
                    
                    if not done:
                        file = file[0:find+len(search.group())]
                                    
            
            #Get the 1st letter of the movie name, to search into IMDB API
            fletter = file[0].lower()
            
            #Build the URL
            url = "https://sg.media-imdb.com/suggests/" + fletter + "/" + urllib.parse.quote_plus(file) + ".json"
            req = requests.get(url).text

            #Parse the response to put it in a JSON format
            rname = file.replace(" ","_")
            req = req.replace(rname, '', 1)
            req = re.sub('^.*?\(', '', req)
            req = req[:-1]       

            #Parse the json to get the movie name array
            arr = parse(json.loads(req), file, df)
            
            #If the movie is in the array, then the name is already good
            if ifile in arr:
                print(file + " - Already right")
            else:
                #If not movie found
                if len(arr) == 0:
                    print ("No results found for : " + file)
                else:
                    print(f"Results found for '{f} (seached as '{file}'): select title or -1 to not update")
                    
                    #Print the list of movie found
                    for idx, title in enumerate(arr):
                        print (str(idx) + " : " + title)
                    
                    #Ask for the choice of user (-1 if no rename)
                    inp = input()
                    try:
                        response = int(inp)
                        if response >= 0 and response < len(arr):
                            os.rename(os.path.join(myPath, f),os.path.join(myPath, arr[response] + os.path.splitext(f)[1]))
                    except:
                        print("Failed to rename the file")
                        
input("Execution finished (press enter to continue)")