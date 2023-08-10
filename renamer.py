import requests
import os
import urllib.parse
import urllib.request
import os.path
import json
import re
import pandas as pd
import gzip
import shutil
import argparse


def query_yn(question, default="yes"):
    '''
    Ask a yes/no question via input() and return their answer.
    '''

    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}

    while True:
        choice = input(question).lower()

        if default is not None and choice == "":
            return valid[default]

        if choice in valid:
            return valid[choice]

        print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

def get_langage(movie:str, apikey:str):
    '''
    Get movie first langage with given imdb id and apikey
    '''
    params = {
        "apikey": apikey,
        "i" : movie,
        "type": "movie",
    }

    resp = requests.get("http://www.omdbapi.com/", params=params).json()

    # One or more langage seperated by comma, getting the first one
    return resp["Language"].split(",")[0]

def parse(movie_json:dict, file:str, df:pd.DataFrame=None, langage:str=None, apikey:str=None):
    '''
    Takes a IMDB response and parse it to obtain a list of movies name
    '''

    arr = []

    # If there is some results
    if 'd' in movie_json:
        movie_json = movie_json["d"]
        for idx, movie in enumerate(movie_json):
            if 'q' in movie:
                # If results is a feature movie
                if movie["q"] == "feature":

                    name = movie['l']
                    # If the movie have a year of release
                    if 'y' in movie:
                        if not df.empty:
                            # Line of the found title in the local database
                            dfo = df.loc[df['tconst'] == movie['id']]

                            if not dfo.empty:
                                # Original title
                                orignal = dfo['originalTitle'].iloc[0]

                                # If the langage is the expected one from the user (e.g. = 'french'), then we keep the original title
                                movie_langage = get_langage(movie['id'], apikey)
                                if movie_langage.lower() == langage.lower():
                                    name = orignal

                        name = f"{name} ({movie['y']})"

                        # Forbidden characters in file names
                        name = name.replace(":", "").replace("?", "")

                        # Add movie to the list
                        arr.append(name)

                        # If the 1st result is already right, we don't look for others results
                        match = re.search(r"[0-9]{4}$", file)
                        if match:
                            file = f"{file[:-4]}({match.group()})"

                        if name.lower() == file.lower() and idx == 0:
                            break
    return arr


def load_database():
    '''
        Load or downlaod IMDB title basic database
    '''

    df = None
    tsv_path = os.path.dirname(os.path.realpath(__file__))
    tsv_file = os.path.join(tsv_path, 'data.tsv')

    if(os.path.isfile(os.path.splitext(tsv_file)[0] + ".csv")):

        print("[*] Loading local database...")
        df = pd.read_csv(os.path.splitext(tsv_file)[0] + ".csv")

    else:
        if not query_yn("No local database found, do you want to download it ? [Y/n]"):
            exit()

        print("[*] Downloading https://datasets.imdbws.com/title.basics.tsv.gz")
        urllib.request.urlretrieve(
            "https://datasets.imdbws.com/title.basics.tsv.gz", os.path.join(tsv_path, 'title.basics.tsv.gz'))

        print("Extracting...")
        with gzip.open(os.path.join(tsv_path, 'title.basics.tsv.gz'), 'rb') as f_in:
            with open(os.path.join(tsv_path, 'data.tsv'), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        print("[*] Sorting...")
        csv_table = pd.DataFrame()

        for chunk in pd.read_table(tsv_file, sep='\t', usecols=[0, 1, 2, 3], chunksize=50000):
            chunk = chunk[(chunk.titleType == 'movie')]
            chunk = chunk.drop(columns=['titleType'])
            csv_table = pd.concat([csv_table, chunk], ignore_index=True)

        print("[*] Saving database...")
        csv_table.to_csv(os.path.join(tsv_path, 'data.csv'), index=False)

        os.remove(os.path.join(tsv_path, 'title.basics.tsv.gz'))
        os.remove(tsv_file)

        df = csv_table
            
    return df


def rename_movies(path:str, all:bool=False, df:pd.DataFrame=None, langage:str=None, apikey:str=None):
    print("[*] Starting to loop throught movies")

    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)):

            # File name without extension
            ifile = os.path.splitext(f)[0]

            # Search for the expected format
            search = re.search('^.*\([0-9]{4}\)$', ifile)

            # If it's not from the expected format or otpion --all is true
            if not search or all:

                # Remove useless strings
                file = re.sub(r'\[.*\]', '', ifile)
                file = re.sub(r'(M|m)(U|u)(L|l)(T|t)(I|i).*', '', file)
                file = re.sub(r'(V|v)(O|o)(S|s)(T|t)(F|f)(R|r).*', '', file)
                file = re.sub(r'avi.*', '', file)
                file = re.sub(r'mkv.*', '', file)
                file = re.sub(r'www.*', '', file)
                file = re.sub(r'(H|h)(D|d).*', '', file)
                file = re.sub(r'[0-9]{3}([0-9])?p.*', '', file)

                file = file.replace('.', ' ')

                # Search for a date
                search = re.search('\(?[0-9]{4}\)?', file)
                if search:
                    find = file.find(search.group())
                    # If there is a date, we remove everything after the date
                    if find != -1:
                        done = False
                        if len(file) > find + len(search.group()):
                            # If char p after date because it will be quality not date
                            if file[find+len(search.group())] == 'p':
                                file = file[0:find - 1]
                                done = True

                        if not done:
                            file = file[0:find+len(search.group())]

                # Get the 1st letter of the movie name, to search into IMDB API
                fletter = file[0].lower()

                # Build the URL
                url = f"https://sg.media-imdb.com/suggests/{fletter}/{urllib.parse.quote_plus(file)}.json"
                req = requests.get(url).text

                # Parse the response to put it in a JSON format
                req = req[req.find("({") + 1: -1]

                # Parse the json to get the movie name array
                arr = parse(json.loads(req), file, df, langage, apikey)

                # If the movie is in the array, then the name is already good
                if ifile in arr:
                    print(f"[+] {file} - Already right")
                else:
                    # If not movie found
                    if len(arr) == 0:
                        print("[-] No results found for : " + file)
                    else:
                        print(f"[+] Results found for '{f}' (searched as '{file}'):")
                        print(f"[+] Enter movie ID or -1 to not update")

                        # Print the list of movie found
                        for idx, title in enumerate(arr):
                            print(str(idx) + " : " + title)

                        # Ask for the choice of user (-1 if no rename)
                        inp = input()
                        try:
                            response = int(inp)
                            if response >= 0 and response < len(arr):
                                os.rename(os.path.join(path, f), os.path.join(
                                    path, arr[response] + os.path.splitext(f)[1]))
                        except:
                            print("[-] Failed to rename the file")



def def_args():
    parser = argparse.ArgumentParser(
        description='Loop throught movie directory and call IMDB API to find the exact title')

    parser.add_argument(dest="dir", metavar='dir',
                        help="define the directory to search into")
    parser.add_argument("-l", "--langage", default=False,
                        help="define the language for which original title is kept, requires downloading local database and OMDB API key")
    parser.add_argument("-k", "--key", default=False,
                        help="OMDB API key (get one at https://www.omdbapi.com")
    parser.add_argument("-a", "--all", action="store_true", default=False,
                        help="iterate through every movie, even those already respecting the expected format: movie_name (movie_year)")

    return parser.parse_args()


if __name__ == "__main__":

    args = def_args()

    if args.langage and not args.key:
        print(f"[-] OMDB API key required with --langage (-l), use --key (-k)")
        exit(1)

    movie_path = args.dir
    if not os.path.exists(movie_path):
        print(f"[-] Path: {movie_path} not found !")
        exit(1)
    
    df = None
    if args.langage:
        df = load_database()

    rename_movies(movie_path, args.all, df, args.langage, args.key)
    
    input("[+] Execution finished (press enter to continue)")