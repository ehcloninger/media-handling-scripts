'''
delete-media-tag-value

Purges tags with strings that match certain values

NOTE: This function is destructive to your media files. Run this first on a sample and always keep 
a backup in case something goes wrong.

Some uploaders to music sites put their own stamp on the metadata. This script searches for them 
and removes them. It limits its activities to these tag types
* TextFrame
* UrlFrame
* Lyrics (USLT)

It may be necessary to extend the class to the numeric text frame, paired text frame, time stamp
text frame, etc. if it proves that these uploaders are getting obnoxious.
'''

import os
import argparse
from pathlib import Path
from unidecode import unidecode
import mutagen
import mutagen.id3
import re

def get_ext(filename, tolower=False) -> str:
    ext = ""
    idx = filename.rfind('.')
    if idx >= 0:
        ext = filename[idx + 1:]
    if tolower:
        return ext.lower()
    else:
        return ext
    
def term_exists(tag:str, terms:list, case=False) -> bool:
    if not case:
        tag = tag.lower()

    for term in terms:
        if tag.find(term) >= 0:
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description='List metadata tags from media files')
    parser.add_argument('input', help='Media file or a folder of media files')
    parser.add_argument("-t", "--term", action="append", help="Search Terms to delete from tags")
    parser.add_argument("-l", "--list", help="Search Terms to delete from tags")
    parser.add_argument("-c", "--case", help="Case sensisitive", action="store_true", default=False)
    parser.add_argument("--dryrun", help="Do a dry run and print results", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    # The user can provide both --list and --term values, so put them all in a combined search list
    terms = list()
    if args.term is not None:
        for term in args.term:
            if args.case:
                terms.append(str(term))
            else:
                terms.append(str(term).lower())

    if args.list is not None:
        my_list = []
        with open(args.list, mode="rt", encoding="utf-8") as file:
            if args.case:
                my_list = [x.rstrip() for x in file]
            else:
                my_list = [x.rstrip().lower() for x in file]
        terms.extend(my_list)

    if len(terms) == 0:
        print("Must provide either --term or --list option")
        return

    media_extensions = ["mp3","m4a","m4b"]

    mediafiles = list()
    if os.path.isdir(args.input):
        for root, dirs, files in os.walk(args.input):
            for file in files:
                filename = str(file)
                if get_ext(filename, tolower=True) in media_extensions:
                    mediafiles.append(os.path.join(root, file))
    else:
        filename = str(args.input)
        if get_ext(filename, tolower=True) in media_extensions:
            mediafiles.append(args.input)
        else:
            print("%s is not a supported media file type" % args.input)
    mediafiles.sort()
    
    if len(mediafiles) == 0:
        print("No files to process")
        return

    # This is the part where the magic happens. Walk the list of tag types in the input
    # file and mark the ones that need to be deleted.
    for mediafile in mediafiles:
        head,tail = os.path.split(Path(mediafile))
        output_str = tail + ":"

        id3file = mutagen.id3.ID3(mediafile)
        if id3file is not None:
            to_delete = list()
            to_modify = list()
            for tag in filter(lambda t: t.startswith(("")), id3file):
                frame = id3file[tag]
                if isinstance(frame, mutagen.id3.TextFrame):
                    if term_exists(str(getattr(frame,"text")), terms, args.case):
                        if isinstance(frame, mutagen.id3.TPE1) or isinstance(frame, mutagen.id3.TPE2):
                            to_modify.append(tag)
                        else:
                            to_delete.append(tag)
                elif isinstance(frame, mutagen.id3.UrlFrame):
                    if term_exists(str(getattr(frame,"url")), terms, args.case):
                        to_delete.append(tag)
                elif isinstance(frame, mutagen.id3.USLT):
                    if term_exists(str(getattr(frame,"text")), terms, args.case):
                        to_delete.append(tag)

            if (len(to_delete) > 0) or (len(to_modify) > 0):
                for tag in to_modify:
                    frame = id3file[tag]
                    text = getattr(frame,"text")
                    if len(text) > 0:
                        text = text[0] 
                        for term in terms:
                            itext = re.compile(re.escape(term), re.IGNORECASE)
                            text = itext.sub("", text).strip()
                        text = text.replace("  "," ")
                        setattr(frame, "text", text)
                        output_str += " " + id3file[tag].FrameID

                for tag in to_delete:
                    output_str += " " + id3file[tag].FrameID
                    del id3file[tag]
                if not args.dryrun:
                    id3file.save()
                print(output_str)

if __name__ == '__main__':
    main()
