'''
generate-metadata-list - Searches a file structure and extracts the metadata to build a playlist generator

'''

import os
import argparse
from pathlib import Path
from unidecode import unidecode
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp3 import MPEGInfo
from mutagen import mp3
from colorama import Fore

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
    parser.add_argument("-o", "--output", help="Output File", default="ratings-list.txt")
    parser.add_argument("-x", "--extractprefix", help="Prefix to remove from path names")
    parser.add_argument("-p", "--prefix", help="Prefix to add from path names")
    parser.add_argument("-v", "--verbose", help="Be verbose (default: False)", action="store_true", default=False)
    parser.add_argument("-z", "--zero", help="Output files with 0 rating (default: False)", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    # This code uses ID3, so the input format needs to support it. Ideally, use a library
    # or tool that supports multiple formats
    extensions = ["mp3","m4a","m4b"] # TODO: Add m4a, m4b, flac, etc.

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

    outfile = open(args.output, "wt", encoding="utf-8")
    outfile.write("\"Path\",\"Artist\",\"Album\",\"Title\",\"Genre\",\"Rating\",\"Year\",\"Length\",\"Grouping\",\"File Size\"\n")

    total = len(mediafiles)
    i = 0
    printed = ""
    for mediafile in mediafiles:
        filepath = str(mediafile.replace("\\","/"))
        if (args.extractprefix):
            if filepath.startswith(args.extractprefix):
                filepath = filepath.replace(args.extractprefix, "")
        if (args.prefix):
            filepath = args.prefix + "/" + filepath
            filepath = filepath.replace("/./","/")
            filepath = filepath.replace("//","/")


        i += 1
        head,tail = os.path.split(Path(mediafile))
        if args.verbose:
            if head != printed:
                print(Fore.GREEN + "%d/%d: %s" % (i, total, head) + Fore.BLACK)
                printed = head
        try:
            # id3file = mutagen.id3.ID3(mediafile)
            mp3file = MP3(mediafile)
            if mp3file is not None:
                rating = 0
                year = 0
                length = int(((mp3file.info.length * 1000) + 1000)/1000)
                filesize = os.path.getsize(mediafile)
                title = ""
                genre = ""
                artist = ""
                grouping = ""
                album = ""
                tags = getattr(mp3file, "tags")
                for tag in filter(lambda t: t.startswith(("")), tags):
                    frame = tags[tag]
                    if isinstance(frame, mutagen.id3.POPM): # type: ignore
                        rating = getattr(frame, "rating")
                    elif isinstance(frame, mutagen.id3.TXXX): # type: ignore
                        key = getattr(frame, "desc")
                        if key == "originalyear":
                            tmp = getattr(frame, "text")
                            if len(tmp) > 0:
                                # if year == 0:
                                year = str(tmp[0]).strip()
                                if len(year) > 4:
                                    print("%s: Year shortened to %s" % (mediafile, year))
                                    year = year[0:4]
                                year = int(year)
                                # else:
                                #     if int(tmp[0]) != year and args.verbose:
                                #         print("Conflicting dates for %s (%s, %d)" % (mediafile, tmp[0], year))
                    elif isinstance(frame, mutagen.id3.TIT2): # type: ignore
                        tmp = getattr(frame, "text")
                        if len(tmp) > 0:
                            title = tmp[0]
                    elif isinstance(frame, mutagen.id3.TALB): # type: ignore
                        tmp = getattr(frame, "text")
                        if len(tmp) > 0:
                            album = tmp[0]
                    elif isinstance(frame, mutagen.id3.TDRC): # type: ignore
                        # Choosing to prioritize the text frame originalyear over
                        # this if both exist. While this field is likely to be more
                        # accurate historically, I deliberately want each album to
                        # have the same year for each track so that Navidrome
                        # doesn't show multiple albums differentiated only by year.
                        if year == 0:
                            tmp = getattr(frame, "text")
                            if len(tmp) > 0:
                                if year == 0:
                                    year = str(tmp[0])
                                    # MBZ puts in YYYY-MM-DD if it's available. I just want the year
                                    if len(year) > 4:
                                        year = year[0:4]
                                        print("%s: Year shortened to %s" % (mediafile, year))
                                    year = int(year)
                            # else:
                            #     if int(tmp[0]) != year and args.verbose:
                            #         print("Conflicting dates for %s (%s, %d)" % (mediafile, tmp[0], year))
                    elif isinstance(frame, mutagen.id3.TPE1): # type: ignore
                        tmp = getattr(frame, "text")
                        if len(tmp) > 0:
                            artist = tmp[0]
                    elif isinstance(frame, mutagen.id3.TCON): # type: ignore
                        tmp = getattr(frame, "genres")
                        if len(tmp) > 0:
                            genre = tmp[0]
                    elif isinstance(frame, mutagen.id3.TCON): # type: ignore
                        tmp = getattr(frame, "genres")
                        if len(tmp) > 0:
                            genre = tmp[0]
                    elif isinstance(frame, mutagen.id3.GRP1): # type: ignore
                        tmp = getattr(frame, "text")
                        if len(tmp) > 0:
                            grouping = tmp[0]

                if rating > 0 or args.zero:
                    if year == 0:
                        print("%s: Year is 0" % (mediafile))
                    outfile.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%d\",\"%d\",\"%d\",\"%s\",\"%d\"\n" % (filepath.replace("\"","\\\"").replace('\\','/'), artist.replace("\"","\"\""), album.replace("\"","\"\""), title.replace("\"","\"\""), genre.replace("\"","\"\""), rating, year, length, grouping, filesize))
            else:
                print("Can't find necessary ID3 tags for %s" % (mediafile))
                continue

        except Exception as e:
            print(e)
            continue

    outfile.close()  

if __name__ == '__main__':
    main()