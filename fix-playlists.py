'''
fix-playlists

This script allows me to fix my playlist collection after I went through several changes of
file naming patterns. It operates by me entering a command in Windows shell to get a 
list of all the media files in my collection.
> dir /s /b *.mp3 > all.txt

Then, using Notepad++ or any RegEx capable editor, remove the front of the path up to the
genre, so the first column is the name of the first genre, 
eg. Blues/Blind Willie/Best of Blind Willie/01-001 - My Eyes Have Seen the Glory.mp3

Then, run this Regex on the entire file 
^(.+?)\\(.+?)\\(.+?)\\([0-9][0-9]-[0-9][0-9][0-9]) - (.+?)$
"$3:$5","$1\\$2\\$3\\$4 - $5"

This produces a key of the album name plus the song title, minus any extra. The data is
the proper path under the current naming rules.
e.g. "Best of Blind Willie:My Eyes Have Seen the Glory","Blues/Blind Willie/Best of Blind Willie/01-001 - My Eyes Have Seen the Glory.mp3"

There is an option to provide a new prefix, which is the path on the destination server.
e.g. /mnt/music/Albums

'''
import errno
import argparse
import os
from pathlib import Path
import shutil
import csv
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Generate Jekyll assets from files.')
    parser.add_argument('-p','--playlist', help='Input file', required=True)
    parser.add_argument('-l','--list', help='List of all files', required=True)
    parser.add_argument('-o','--output', help='Output File', required=True)
    parser.add_argument('-x','--prefix', help='Prefix for output path')

    args = parser.parse_args()

    prefix = ""
    if args.prefix is not None:
        prefix = str(args.prefix)

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    data = dict()
    with open(args.list,'r',encoding="utf-8") as f:  
        reader = csv.reader(f) 
        for line in reader: 
            key = line[0].lower()
            data[key] = line[1]
    lines = open(args.playlist, encoding="utf-8").readlines()
    
    with open(args.output, mode="wt", encoding="utf-8") as file:
        for line in lines:
            s = str(line)
            if s[0] == '#':
                if s.startswith("#EXTINF:"):
                    prevline = line
                else:
                    file.write(line)
            else:
                s = s.replace("%20"," ")
                s = s.replace("\n","")
                idx = s.rfind('/')
                if idx >= 0:
                    path = s[0:idx]
                    idx = path.rfind('/')
                    if idx >= 0:
                        path = path[idx + 1:]
                    idx = s.rfind('/')
                    song = ""
                    if idx >= 0:
                        song = s[idx + 1:]
                    idx = song.find(" - ")
                    if (idx >= 0):
                        song = song[idx + 3:]
                    search = path.lower() + ":" + song.lower()
                    if search in data:
                        result=data[search]
                        if result is not None:
                            file.write(prevline)
                            file.write("%s%s\n" % (prefix, result))
                    else:
                        print("Could not find %s" % (search))
if __name__ == '__main__':
    main()
