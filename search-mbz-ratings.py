'''
search-mbz-ratings - Searches a Musicbrainz database for song ratings and generates a 
script to call eyed3 with commands to set the rating values for the songs, if found.

NOTE: Pylance complains about subclasses not being exported by mutagen. Even though it flags this
as an error, it does work. This should be a warning, but Pylance treats it as an error. It's safe
to ignore.

'''

import os
import argparse
from pathlib import Path
from unidecode import unidecode
import mutagen
import mutagen.id3
from colorama import Fore
import requests

# get_ext - check that the file extension is supported
def get_ext(filename, tolower=False) -> str:
    ext = ""
    idx = filename.rfind('.')
    if idx >= 0:
        ext = filename[idx + 1:]
    if tolower:
        return ext.lower()
    else:
        return ext
    
def main():
    parser = argparse.ArgumentParser(description='Group and rate media files with ID3 tags')
    parser.add_argument('input', help='Media file or a folder of media files')
    parser.add_argument("-s", "--server", help="Perform grouping operation", required=True)
    parser.add_argument("-o", "--output", help="Output File", default="output.bat")
    parser.add_argument("-e", "--email", help="Email address for POPM field (default: MusicBee)", default="MusicBee")
    parser.add_argument("-p", "--params", help="Extra eyed3 params (default: --quiet)", default="--quiet")
    parser.add_argument("-z", "--zero", help="Set items with no rating to 0 (default: False)", action="store_true", default=False)
    parser.add_argument("-v", "--verbose", help="Be verbose (default: False)", action="store_true", default=False)
    parser.add_argument("-w", "--overwrite", help="Overwrite existing ratings in POPM tags (default: False)", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    server = str(args.server)
    if server[-1:] == '/':
        server = server[0:-1]

    # Please use this against your own MB server or be nice to the public server
    if server.lower().find("musicbrainz.org") >= 0:
        resp = ""
        while resp != "I AGREE":
            print(Fore.RED + "Please use a mirror server. Type I AGREE to continue. > " + Fore.BLACK)
            resp = input()

    # This code uses ID3, so the input format needs to support it. Ideally, use a library
    # or tool that supports multiple formats
    extensions = ["mp3"] # TODO: Add m4a, m4b, flac, etc.

    # Search input directory for files with the matching extension or if a single file,
    # Make sure it's the supported extension(s)
    mediafiles = list()
    if os.path.isdir(args.input):
        for root, dirs, files in os.walk(args.input):
            for file in files:
                filename = str(file)
                if get_ext(filename, tolower=True) in extensions:
                    mediafiles.append(os.path.join(root, file))
    else:
        filename = str(args.input)
        if get_ext(filename, tolower=True) in extensions:
            mediafiles.append(args.input)
        else:
            print("%s is not a supported media file type" % args.input)

    # For convenience sake, sort the list of found media files by path, in case os.walk() didn't
    mediafiles.sort()
    
    if len(mediafiles) == 0:
        print("No files to process")
        return

    # We only need to call the API once per album, although we have a list of files, so generate
    # a set (unique) of MB album IDs (GUIDs) taken from the source files themselves
    release_ids = set()
    total = len(mediafiles)
    recordings = []
    if args.verbose:
        print(Fore.GREEN + "Processing %d Files" % (total) + Fore.BLACK)
    printed = ""
    print("Step 1: Find Media Files")
    for mediafile in mediafiles:
        head,tail = os.path.split(Path(mediafile))
        if args.verbose:
            if head != printed:
                print(Fore.GREEN + "%s" % (head) + Fore.BLACK)
                printed = head
        try:
            id3file = mutagen.id3.ID3(mediafile)
            if id3file is not None:
                recording = {
                    "path": mediafile,
                    "release_id": "",
                    "recording_id": "",
                    "track_no": 0,
                    "rating": 0,
                    "exists" : False
                }
                for tag in filter(lambda t: t.startswith(("")), id3file):
                    frame = id3file[tag]
                    if isinstance(frame, mutagen.id3.TRCK): # type: ignore
                        track = getattr(frame, "text")
                        if len(track) > 0:
                            track_no = track[0]
                            idx = track_no.find('/')
                            if idx >= 0:
                                track_no = track_no[0:idx]
                            idx = track_no.find('.')
                            if idx >= 0:
                                track_no = track_no[0:idx]
                            recording["track_no"] = int(track_no)
                    if isinstance(frame, mutagen.id3.POPM): # type: ignore
                        rating = getattr(frame, "rating")
                        recording["rating"] = int(rating)
                        recording["exists"] = True
                    elif isinstance(frame, mutagen.id3.TXXX): # type: ignore
                        desc = getattr(frame, "desc")
                        text = getattr(frame, "text")
                        if len(text) > 0:
                            if desc == "MusicBrainz Album Id":
                                recording["release_id"] = text[0]
                            elif desc == "MusicBrainz Release Track Id":
                                recording["recording_id"] = text[0]
            else:
                if args.verbose:
                    print("Can't find necessary ID3 tags for %s" % (mediafile))
                continue

        except Exception as e:
            print(e)
            continue

        if recording["track_no"] == 0 or recording["release_id"] == "":
            if args.verbose:
                print("Can't find necessary ID3 tags for %s" % (mediafile))
            continue

        if (not recording["exists"]) or args.overwrite:
            if recording["rating"] == 0 or args.zero:
                release_ids.add(recording["release_id"])
                recordings.append(recording)

    if len(release_ids) == 0:
        print("No Releases needing changed found among input files at %s" % args.input)
        return
    
    # Go through the album IDs found and request JSON information about the album from the MB server
    i = 1
    total = len(release_ids)
    output_recordings = []
    print("Step 2: Query Server for information on %d releases" % (total))
    for rid in release_ids:
        this_release = []

        # Go through the list of recordings in reverse. If a match of release ID is found,
        # remove the recording from the full list and place it into the list of ones to work
        # on next. This is so the list will get shorter over time and quicker to traverse,
        # but also let us know which ones weren't found in MB, so the user can try a better match.
        for recording in reversed(recordings):
            if recording['release_id'] == rid:
                recordings.pop(recordings.index(recording))
                this_release.append(recording)

        if len(this_release) == 0:
            print("No recordings found for %s" % (rid))
            continue

        if args.verbose:
            path = str(this_release[0]["path"])
            idx = path.rfind(os.sep)
            if idx >= 0:
                path = path[0:idx]
            print(Fore.GREEN + "Querying %d/%d: %s" % (i, total, path) + Fore.BLACK)
        i += 1

        payload = {
            "inc":"aliases+artist-credits+labels+recordings+ratings",
            "fmt":"json"
        }
        headers = {
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        url = server + "/ws/2/release/" + str(rid)
        
        response = None
        try:
            response = requests.get(url, params=payload, headers=headers)
            if response.status_code != 200:
                print("Error %d retrieving data for %s" % (response.status_code, this_release[0]["path"]))
                continue
            
        except Exception as e:
            print(e)
            continue

        release = response.json()
        if release is None:
            print("Empty response")
            continue

        # NOTE: This is not great code. It's not Pythonic by any means, but it works. This may not 
        # work for all album queries and may require some adjustment. 
        # Basically, look through the list of returned tracks to find the rating if it exists for the 
        # track. If it does, try to find the track in the list of files with the matching track ID/position
        for media in release["media"]:
            if "tracks" in media:
                for track in media["tracks"]:
                    if "recording" in track and "position" in track:
                        recording = track["recording"]
                        position = int(track["position"])
                        if "rating" in recording:
                            rating = recording["rating"]
                            if "value" in rating:
                                value = rating["value"]
                                if value is not None:
                                    rating = int(float(value) * 51.0)
                                    for item in this_release:
                                        if item["track_no"] == position:
                                            item["rating"] = rating
                                            break

        # Generate the output. This is a generic script output and should be compliant with
        # bash, powershell, CMD, etc. so long as the eyed3 module is installed.
        for recording in this_release:
            output_recordings.append(recording)
        
    # To be honest, this should probably just reopen the file with mutagen and write the POPM
    # tag directly, but I'll use this for now.
    sorted_recordings = sorted(output_recordings, key=lambda k: k["path"])

    outfile = open(args.output, "wt", encoding="utf-8")
    for recording in sorted_recordings:
        if recording["rating"] > 0 or args.zero:
            outfile.write("eyed3 \"%s\" --add-popularity \"%s:%d:0\" %s\n" % 
                          (recording["path"], args.email, recording["rating"], args.params))
    outfile.close()  

    # Let the user know that some files didn't match in the database. If this happens, they may
    # Want to update their MB IDs with Picard.
    if len(recordings) > 0:
        print(Fore.YELLOW + "NOTE: Ratings were not found for some recordings" + Fore.BLACK)
        for recording in recordings:
            print("%s" % (recording["path"]))

if __name__ == '__main__':
    main()