'''
id3-rate-group - Manually modify the rating and group values in bulk

This is a work in progress. I want to be able to assign group and ratings in bulk. MP3Tag and
Picard are great at what they do, but bulk applying custom ratings and groupings requires a lot
of mouse movement and typing. This goes through all the files and allows me to provide a rating
or group (or both) to each title with minimal typing.

This tool uses the POPM field. According to the docs, this field is 0-255, which means the typical
0-5 rating needs to be mapped onto a 0-255 scale by multiplying by 51.0.

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
from colorama import Fore, Back, Style

def get_ext(filename, tolower=False) -> str:
    ext = ""
    idx = filename.rfind('.')
    if idx >= 0:
        ext = filename[idx + 1:]
    if tolower:
        return ext.lower()
    else:
        return ext
    
def do_rating(old_rating=0) -> int:
    while True:
        if old_rating == 0:
            print(Fore.RED + "Enter a Rating from 0-5 OR <ENTER> for none")
        else:
            if old_rating > 192:
                old_rating = 5
            elif old_rating > 128:
                old_rating = 4
            elif old_rating > 64:
                old_rating = 3
            elif old_rating > 1:
                old_rating = 2
            else:
                old_rating = 1
            print(Fore.RED + "Enter a Rating from 0-5 OR <ENTER> for none (current value: %d)" % (old_rating))
        i = input("> ")
        if len(i) == 0:
            return 0
        try:
            val = int(i)
            if 0 <= val <= 5:
                return val
        except:
            pass
    return 0
    
def do_group(values:list, old_value:str) -> int:
    while True:
        if len(values) == 0:
            return 0
        i = 1
        print(Fore.RED + "Enter a number for the group OR <ENTER> for none (current value: %s)" % (old_value))
        for value in values:
            print(Fore.YELLOW + "%2d: %s" % (i, value))
            i += 1
        i = input("> ")
        if len(i) == 0:
            return 0
        try:
            val = int(i)
            if 0 < val <= len(values):
                return val - 1
        except Exception as e:
            pass
    return 0
    
def main():
    parser = argparse.ArgumentParser(description='Group and rate media files with ID3 tags')
    parser.add_argument('input', help='Media file or a folder of media files')
    parser.add_argument("-g", "--group", help="Perform grouping operation", action="store_true", default=False)
    parser.add_argument("-r", "--rating", help="Perform rating operation (0-5)", action="store_true", default=False)
    parser.add_argument("-v", "--value", action="append", help="Value for grouping (start with 1)")
    parser.add_argument("-e", "--email", help="Email for rating", default="")
    parser.add_argument("-o", "--overwrite", help="Overwrite existing rating/grouping (default is to skip)", action="store_true", default=False)

    args = parser.parse_args()

    group_values = []
    if args.value is None or len(args.value) == 0:
        group_values = ["Daily","Weekly","Monthly","Quarterly","Yearly"]
    else:
        group_values = args.value
    rating_values = [0, 1, 64, 128, 196, 255] # from https://www.mediamonkey.com/forum/viewtopic.php?p=358524

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    extensions = ["mp3"] # TODO: Add m4a, m4b, flac, etc.

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
    mediafiles.sort()
    
    if len(mediafiles) == 0:
        print("No files to process")
        return

    total = len(mediafiles)
    i = 1
    for mediafile in mediafiles:
        head,tail = os.path.split(Path(mediafile))
        
        print(Fore.GREEN + "%d/%d: %s" % (i, total, tail))
        i += 1

        try:
            id3file = mutagen.id3.ID3(mediafile)
            if id3file is not None:
                found_rating = False
                found_group = False
                for tag in filter(lambda t: t.startswith(("")), id3file):
                    frame = id3file[tag]
                    if isinstance(frame, mutagen.id3.POPM):
                        found_rating = True
                        if (args.rating) and (args.overwrite):
                            old_rating = getattr(frame, "rating")
                            new_rating = do_rating(new_rating)
                            if new_rating > 0 and new_rating < len(rating_values):
                                frame.rating = rating_values[new_rating]
                                frame.email = args.email
                    elif isinstance(frame, mutagen.id3.GRP1):
                        found_group = True
                        if (args.group) and (args.overwrite):
                            text = getattr(frame, "text")
                            new_group = do_group(group_values, text)
                            if new_group > 0 and new_group < len(group_values):
                                frame.group = group_values[new_group]

                if args.rating and not found_rating:
                    new_rating = do_rating()
                    if new_rating > 0 and new_rating < len(rating_values):
                        frame = mutagen.id3.POPM(email=args.email, rating=rating_values[new_rating])
                        id3file.add(frame)
                        found_rating = True

                if args.group and not found_group:
                    new_group = do_group(group_values,"")
                    if new_group > 0 and new_group < len(group_values):
                        frame = mutagen.id3.GRP1(text=group_values[new_group])
                        id3file.add(frame)
                        found_group = True

                if found_rating or found_group:
                    id3file.save()
        except Exception as e:
            print(e)
            pass

        print(Fore.BLACK + " ")

if __name__ == '__main__':
    main()
