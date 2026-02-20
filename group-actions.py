'''
group-actions

Does actions on the grouping (GRP1) tag based on user choices.

'''

import os
import sys
import argparse
from pathlib import Path
from unidecode import unidecode
import mutagen
import mutagen.id3
from mutagen.mp3 import MP3
from colorama import Fore
import datetime
from enum import Enum
from math import floor, log
import csv

def format_bytes(size):
  power = 0 if size <= 0 else floor(log(size, 1024))
  return f"{round(size / 1024 ** power, 2)} {['B', 'KB', 'MB', 'GB', 'TB'][int(power)]}"

GROUP_SEPARATOR = "|"

class Recording:
    def __init__(self):
        self.path = str()
        self.artist = str()
        self.album = str()
        self.title = str()
        self.genre = set()
        self.rating = 0
        self.year = 0
        self.length = 0
        self.grouping = set()
        self.filesize = 0
        self.modified = False
    
    def fromMP3(self, mp3file:MP3):
        self.length = int(((mp3file.info.length * 1000) + 1000)/1000)
        self.path = mp3file.filename
        self.filesize = os.path.getsize(self.path) # type: ignore
        tags = getattr(mp3file, "tags")
        if tags is not None:
            for tag in filter(lambda t: t.startswith(("")), tags):
                frame = tags[tag]
                # TODO: Don't loop, just request specific frame types
                if isinstance(frame, mutagen.id3.TALB): # type: ignore
                    self.setAlbum(getattr(frame, "text"))
                elif isinstance(frame, mutagen.id3.TPE1): # type: ignore
                    self.setArtist(getattr(frame, "text"))
                elif isinstance(frame, mutagen.id3.TIT2): # type: ignore
                    self.setTitle(getattr(frame, "text"))
                elif isinstance(frame, mutagen.id3.POPM): # type: ignore
                    self.setRating(getattr(frame, "rating"))
                elif isinstance(frame, mutagen.id3.GRP1) or isinstance(frame, mutagen.id3.GP1): # type: ignore
                    self.setGrouping(getattr(frame, "text"))
                elif isinstance(frame, mutagen.id3.TCON): # type: ignore
                    self.setGenre(frame.genres)
                elif isinstance(frame, mutagen.id3.TXXX): # type: ignore
                    key = getattr(frame, "desc")
                    if key == "originalyear":
                        self.setYear(getattr(frame, "text"))
                elif isinstance(frame, mutagen.id3.TDRC): # type: ignore
                    # Choosing to prioritize the text frame originalyear over
                    # this if both exist. While this field is likely to be more
                    # accurate historically, I deliberately want each album to
                    # have the same year for each track so that Navidrome
                    # doesn't show multiple albums differentiated only by year.
                    self.setYear(getattr(frame, "text"))
        self.modified = False
        return
    
    def setArtist(self, values:list[str]):
        if values is not None and len(values) > 0:
            self.artist = str(values[0]).strip()
        return

    def setAlbum(self, values:list[str]):
        if values is not None and len(values) > 0:
            self.album = str(values[0]).strip()
        return

    def setTitle(self, values:list[str]):
        if values is not None and len(values) > 0:
            self.title = str(values[0]).strip()
        return
    
    def setRating(self, value:int):
        self.rating = value
        return
    
    def setYear(self, values:list[str]):
        if values is not None and len(values) > 0:
            # if year == 0:
            year = str(values[0]).strip()
            if len(year) > 4:
                year = year[0:4]
            self.year = int(year)
        return

    def setGrouping(self, values:list[str]):
        self.grouping.clear()
        self.addGroups(values)
        self.modified = False
        return
    
    def getGroupingAsString(self) -> str: # type: ignore
        return GROUP_SEPARATOR.join(self.grouping)
    
    def groupExists(self, group:str) -> bool:
        return group.strip() in self.grouping

    def setGenre(self, values:list):
        if values is not None and len(values) > 0:
            for value in values:
                tmp = value.strip()
                if len(tmp) > 0:
                    self.genre.add(value)
        return

    def intFromString(self, input:str) -> int:
        ret = 0
        tmp = "".join(filter(lambda x: x in "0123456789", input))
        try:
            ret = int(tmp)
        except:
            return 0
        return ret
    
    def deleteGroups(self, values:list[str]):
        if values is not None and len(values) > 0:
            for value in values:
                value = value.strip()
                if value in self.grouping:
                    self.grouping.discard(value)
                    self.modified = True
        return

    def addGroups(self, values:list[str]):
        if values is not None and len(values) > 0:
            for value in values:
                value = value.strip()
                tmp = value.split(GROUP_SEPARATOR)
                if len(tmp) > 0:
                    for i in tmp:
                        if not i in self.grouping:
                            self.grouping.add(i)
        return

    def fromList(self, line:list[str]):
        self.path = line[0].strip()
        self.artist = line[1].strip()
        self.album = line[2].strip()
        self.title = line[3].strip()
        items = line[4].split(GROUP_SEPARATOR)
        for item in items:
            value = item.strip()
            if len(value) > 0:
                self.genre.add(value)
        self.rating = self.intFromString(line[5])
        self.year = self.intFromString(line[6])
        self.length = self.intFromString(line[7])
        items = line[8].split(GROUP_SEPARATOR)
        for item in items:
            value = item.strip()
            if len(value) > 0:
                self.grouping.add(value)
        self.filesize = self.intFromString(line[9])
        return

    def toList(self) -> list:
        line = list()
        line[0] = self.path
        line[1] = self.artist
        line[2] = self.album
        line[3] = self.title
        line[4] = GROUP_SEPARATOR.join(self.genre)
        line[5] = str(self.rating)
        line[6] = str(self.year)
        line[7] = str(self.length)
        line[8] = GROUP_SEPARATOR.join(self.grouping)
        line[9] = str(self.filesize)
        return line

    def toString(self, format:str) -> str:
        ret = ""
        if format == "txt":
            ret = "%s: %s" % (self.path, ", ".join(self.grouping))
        elif format == "m3u":
            ret = "#EXTINF:%d, %s - %s - %s\n%s" % (self.length, self.artist, self.album, self.title, self.path)
        elif format == "csv":
            ret = "\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%d\"" % (self.path, self.artist, self.album, self.title, self.grouping, self.length)
        return ret

def get_ext(filename, tolower=False) -> str:
    ext = ""
    idx = filename.rfind('.')
    if idx >= 0:
        ext = filename[idx + 1:]
    if tolower:
        return ext.lower()
    else:
        return ext

class Action(Enum):
    ADD = 1
    DELETE = 2
    PRINT = 3
    STATS = 4
    COPY = 5

def main():
    parser = argparse.ArgumentParser(description='Do actions on MP3 file group tags')
    parser.add_argument('action', help='add, delete, print stats')
    parser.add_argument('-i','input', help='Folder of media files or a text file containing a list of files')
    parser.add_argument('-l','--list', help='List of all files')
    parser.add_argument('-d','--destination', help='Destination directory for copy')
    parser.add_argument("-f", "--format", help="Format of output (depends on action)")
    parser.add_argument("-t", "--term", action="append", help="Terms to add, delete, or print")
    parser.add_argument("-o", "--output", help="Output file for print or stat actions")
    parser.add_argument("-p", "--playlist", help="Output playlist title (inside m3u file)")
    parser.add_argument("-v", "--verbose", help="Verbose output (default: False)", action="store_true", default=False)

    args = parser.parse_args()
    
    if (args is None):
        print(Fore.RED + "Could not parse command line. Terminating." + Fore.BLACK)
        return

    actions = {
        "add":    Action.ADD,
        "delete": Action.DELETE,
        "print":  Action.PRINT,
        "stats":  Action.STATS,
        "copy":  Action.COPY
    }
    try:
        action = actions[args.action]
    except:
        print(Fore.RED + "Invalid action: %s" % args.action + Fore.BLACK)
        return

    if args.input is None and args.list is None:
        print(Fore.RED + "Must provide either --input or --list argument" % args.action + Fore.BLACK)
        return

    output_fh = None
    if args.output is None:
        if args.verbose and action in [Action.PRINT]:
            print(Fore.YELLOW + "No output file specified, so sending to stdout. This can be messy when --verbose is used." + Fore.BLACK)
        output_fh = sys.stdout
    else:
        try:
            output_fh = open(args.output, mode="wt", encoding="utf-8")
        except Exception as e:
            print(Fore.RED + "%s: %s" % (args.output, e) + Fore.BLACK)
            return
    
    destination = args.destination
    if destination is None:
        if action in [Action.COPY]:
            print(Fore.RED + "Destination required for copy action" + Fore.BLACK)
            return

    playlist = datetime.datetime.now().strftime("%B %d, %Y %I:%M%p")
    script_formats = ["bat","ps1","sh"]
    text_formats = ["txt","csv","m3u"]
    formats = text_formats + script_formats

    format = args.format
    if format is None:
        format = "txt"

    if action in [Action.PRINT]:
        if format not in text_formats:
            print(Fore.RED + "Invalid format for print action: %s" % format + Fore.BLACK)
            return

    if action in [Action.COPY]:
        if format not in script_formats:
            print(Fore.RED + "Invalid format for copy action: %s" % format + Fore.BLACK)
            return

    terms = list()
    if args.term is not None:
        for term in args.term:
            terms.append(str(term.replace(GROUP_SEPARATOR, "")))
    else:
        if action not in [Action.STATS, Action.PRINT]:
            print(Fore.RED + "Term(s) are required for this action" + Fore.BLACK)
            return

    media_extensions = ["mp3","m4a","m4b"]

    recordings = list()
    if args.list is not None:
        if action in [Action.STATS, Action.PRINT, Action.COPY]:
            with open(args.list,'rt',encoding="utf-8") as f:  
                reader = csv.reader(f) 
                for line in reader:
                    recording = Recording()
                    recording.fromList(line)
                    recordings.append(recording)
        else:
            print(Fore.RED + "The --list option is only valid for this action" + Fore.BLACK)
            return

    mediafiles = list()
    if args.verbose:
        print(Fore.GREEN + "Start Directory: %s" % (args.input) + Fore.BLACK)
    if os.path.isdir(args.input):
        for root, dirs, files in os.walk(args.input):
            for file in files:
                filename = str(file)
                if get_ext(filename, tolower=True) in media_extensions:
                    mediafiles.append(os.path.join(root, file))
        mediafiles.sort()
    else:
        with open(args.input, mode="rt", encoding='utf-8-sig') as file:
            mediafiles = [line.strip() for line in file if line.strip()]
        mediafiles.sort()
        for mediafile in reversed(mediafiles):
            if mediafile[0] == '#':
                mediafiles.remove(mediafile)
    
        if len(mediafiles) == 0:
            print(Fore.RED + "No files to process" + Fore.BLACK)
            return

    if args.verbose:
        print(Fore.GREEN + "Files to process: %d" % (len(mediafiles)) + Fore.BLACK)

    if format == "m3u":
        if args.playlist is not None:
            playlist = args.playlist
        output_fh.write("#EXTM3U\n#PLAYLIST:%s\n" % (playlist))
 
    copy_folders = set()
    total_bytes = 0
    total_files = 0

    if action in [Action.ADD, Action.DELETE]:
        for mediafile in mediafiles:
            head,tail = os.path.split(Path(mediafile))
            if args.verbose:
                print(Fore.GREEN + "%s" % (mediafile) + Fore.BLACK)
            try:
                mp3file = MP3(mediafile)
            except Exception as e:
                print(Fore.RED + "Could not open: %s" % mediafile + Fore.BLACK)
            else:
                recording = Recording()
                recording.fromMP3(mp3file)
                recordings.append(recording)
                
                if action == Action.DELETE:
                    tags = getattr(mp3file, "tags")
                    if tags is not None:
                        recording.deleteGroups(terms)
                        tags.setall('GRP1', [mutagen.id3.GRP1(text=recording.getGroupingAsString())]) # type: ignore
                        try:
                            mp3file.save()
                        except Exception as e:
                            print("Could not save %s: %s" % (mediafile, e))
                            
                elif action == Action.ADD:
                    tags = getattr(mp3file, "tags")
                    if tags is not None:
                        recording.addGroups(terms)
                        tags.setall('GRP1', [mutagen.id3.GRP1(text=recording.getGroupingAsString())]) # type: ignore
                        try:
                            mp3file.save()
                        except Exception as e:
                            print("Could not save %s: %s" % (mediafile, e))
    else:
        if len(recordings) == 0:
            for mediafile in mediafiles:
                head,tail = os.path.split(Path(mediafile))
                if args.verbose:
                    print(Fore.GREEN + "%s" % (mediafile) + Fore.BLACK)
                try:
                    mp3file = MP3(mediafile)
                except Exception as e:
                    print(Fore.RED + "Could not open: %s" % mediafile + Fore.BLACK)
                else:
                    recording = Recording()
                    recording.fromMP3(mp3file)
                    recordings.append(recording)

        for recording in recordings:   
            if action == Action.PRINT:
                do_action = False
                if len(terms) == 0:
                    do_action = True
                else:
                    for item in recording.grouping:
                        if item in terms:
                            do_action = True
                            break

                if do_action:
                    print_string = recording.toString(format)
                    output_fh.write("%s\n" % (print_string))

            elif action == Action.COPY:
                do_action = False
                if len(terms) == 0:
                    do_action = True
                else:
                    for item in recording.grouping:
                        if item in terms:
                            do_action = True
                            break

                if do_action:
                    head,tail = os.path.split(Path(recording.path))
                    total_bytes += recording.filesize
                    total_files += 1
                    copy_folders.add(head)

            elif action == Action.STATS:
                pass

    if action == Action.COPY:
        dest_folder_path = Path(destination)
        dest_folder = str(dest_folder_path.absolute())
        base_folder_path = Path(args.input)
        base_folder = str(base_folder_path.absolute())
        for folder in copy_folders:
            src_folder_path = Path(folder)
            src_folder = str(src_folder_path.absolute())
            partial_src_folder = src_folder.replace(base_folder, "")
            if partial_src_folder[0] == os.sep:
                partial_src_folder = partial_src_folder[1:]
            full_dest_path = os.path.join(dest_folder, partial_src_folder)
            full_src_path = os.path.join(src_folder, "*.*")

            if format in ["bat","ps1"]:
                print_string = "ROBOCOPY \"%s\" \"%s\" /E" % (src_folder, full_dest_path)
                output_fh.write("%s\n" % (print_string))
            elif format in ["sh"]:
                print_string = "mkdir -p \"%s\" && cp \"%s\" \"%s\" /E" % (src_folder, full_src_path, full_dest_path)
                output_fh.write("%s\n" % (print_string))
                
        print("Files to Copy: %d" % (total_files))
        print("Size of media files to copy: %s" % (format_bytes(total_bytes)))

if __name__ == '__main__':
    main()
    print(Fore.WHITE + " ")