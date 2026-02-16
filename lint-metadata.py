'''
lint-metadata - looks at metadata in folders for inconsistencies and incorrect data

'''

import os
import argparse
from pathlib import Path
from unidecode import unidecode
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
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
    
def check_tracks(dir:str, values:set, discs, outfile):
    tracks = list()
    for value in values:
        idx = str(value).find('/')
        if idx > 0:
            value = str(value)[0:idx]
            try:
                tracks.append(int(value))
            except:
                pass
    tracks.sort()    
    if len(tracks) > 0:
        if tracks[0] != 1:
            outfile.write("%s: First track has tracknumber = %d\n" % (dir, tracks[0]))
        current = tracks[0]
        for track in tracks[1:]:
            if track != current + 1:
                if track == current:
                    if discs == 1:
                        outfile.write("%s: More than one track %d.\n" % (dir, track))
                else:
                    outfile.write("%s: Missing track number between %d and %d\n" % (dir, current, track))

            current = track
    else:
        outfile.write("%s: Missing track numbers\n" % (dir))
    return

def check_same(dir:str, values:set, keystr:str, outfile, discs=1, optional=False, func=None) -> bool:
    if len(values) == 0 and not optional:
        outfile.write("%s: No %s in album\n" % (dir, keystr))
        return True
    elif len(values) > discs:
        outfile.write("%s: Different %s in same album\n" % (dir, keystr))
        return False
    return True
    
def process_files(dir:str, mediafiles:list, args, outfile):
    file_frames = dict()
    for mediafile in mediafiles:
        try:
            ez = EasyID3(mediafile)
            file_frames[mediafile] = ez
            # print(ez.pprint())
        except Exception as e: 
            print(e)
            continue

    keys = ["date","musicbrainz_albumid","tracknumber","artist","albumartist","album","musicbrainz_albumartistid","musicbrainz_artistid","discnumber","genre"]
    values = dict()
    for key in keys:
        values[key] = set()
    for mediafile, ez in file_frames.items():
        for key in keys:
            if key in ez.valid_keys:
                try:
                    alist = ez[key]
                    if alist is not None:
                        if len(alist) > 0:
                            values[key].add(alist[0])
                except Exception as e:
                    pass

    discs = len(values["discnumber"])
    check_same(dir, values["artist"], "artist", outfile)
    check_same(dir, values["albumartist"], "albumartist", outfile)
    check_same(dir, values["album"], "album", outfile)
    check_same(dir, values["date"], "date", outfile)
    for date in values["date"]:
        if len(date) != 4:
            outfile.write("%s: Date length is not 4: %s\n" % (dir, date))

    check_same(dir, values["genre"], "genre", outfile)

    # TODO: Check if missing AlbumID in individual songs
    if not check_same(dir, values["musicbrainz_albumid"], "musicbrainz_albumid", outfile, discs, optional=True):
        outfile.write("* This may be due to a multi-album collection with different Disk IDs\n")

    # TODO: Do a better job of handling multiple artistid/albumartistid values for duets and compilations
    check_same(dir, values["musicbrainz_albumartistid"], "musicbrainz_albumartistid", outfile, optional=True)
    check_same(dir, values["musicbrainz_artistid"], "musicbrainz_artistid", outfile, optional=True)
    check_tracks(dir, values["tracknumber"], discs, outfile)

    return
    
def main():
    parser = argparse.ArgumentParser(description='Group and rate media files with ID3 tags')
    parser.add_argument('input', help='Media file or a folder of media files')
    parser.add_argument("-o", "--output", help="Output File", default="lint-metadata.log")
    parser.add_argument("-v", "--verbose", help="Be verbose (default: False)", action="store_true", default=False)

    # TODO: Add option to ignore certain folder names or patterns (e.g. '.git','Playlists')

    args = parser.parse_args()

    if (args is None):
        print(Fore.RED + "Could not parse command line. Terminating." + Fore.BLACK)
        return

    # This code uses ID3, so the input format needs to support it. Ideally, use a library
    # or tool that supports multiple formats
    extensions = ["mp3","m4a","m4b"] # TODO: Add flac, etc.

    # Search input directory for files with the matching extension or if a single file,
    # Make sure it's the supported extension(s)
    mediadirs = list()
    if len(next(os.walk(args.input))[1]) == 0:
        mediadirs.append(args.input)
    else:
        for root, dirs, files in os.walk(args.input):
            for dir in dirs:
                mediadirs.append(os.path.join(root, dir))

    # For convenience sake, sort the list of found media files by path, in case os.walk() didn't
    mediadirs.sort()
    if len(mediadirs) == 0:
        print("No files to process")
        return

    outfile = open(args.output, "wt", encoding="utf-8")

    total = len(mediadirs)
    i = 0

    for mediadir in mediadirs:
        if args.verbose:
            i += 1
            print(Fore.GREEN + "%d/%d: %s" % (i, total, mediadir) + Fore.BLACK)

        files = os.listdir(mediadir)
        mediafiles = list()
        for file in files:
            filename = str(file)
            if get_ext(filename, tolower=True) in extensions:
                mediafiles.append(os.path.join(mediadir, file))

        if len(mediafiles) > 0:
            process_files(mediadir, mediafiles, args, outfile)
        else:
            if len(next(os.walk(mediadir))[1]) == 0:
                outfile.write("%s: Empty folder\n" % (mediadir))

    outfile.close()  

if __name__ == '__main__':
    main()