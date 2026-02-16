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

import csv
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
import glob

GROUP_SEPARATOR = "|"

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

def add_terms_to_group(tags:list, terms:list) -> bool: # type: ignore
    existing_frame = None
    groups = set()
    for tag in filter(lambda t: t.startswith(("")), tags):
        frame = tags[tag]
        if isinstance(frame, mutagen.id3.TextFrame): # type: ignore
            if isinstance(frame, mutagen.id3.GRP1) or isinstance(frame, mutagen.id3.GP1): # type: ignore
                existing_frame = frame
                tmp = getattr(frame, "text")
                if tmp is not None:
                    text = str(tmp[0])
                    items = text.split(GROUP_SEPARATOR)
                    for item in items:
                        groups.add(item)
                break
    for term in terms:
        groups.add(term)
    groups = list(groups)
    groups.sort()

    if existing_frame is None:
        term = GROUP_SEPARATOR.join(groups)
        new_frame = mutagen.id3.GRP1() # type: ignore
        setattr(new_frame, "text", term)
        tags['GRP1'] = new_frame # type: ignore
        return True
    else:
        setattr(existing_frame, "text", GROUP_SEPARATOR.join(groups))
                        
    return True

def delete_terms_from_group(tags:list, terms:list) -> bool: # type: ignore
    existing_frame = None
    groups = set()
    for tag in filter(lambda t: t.startswith(("")), tags):
        frame = tags[tag]
        if isinstance(frame, mutagen.id3.TextFrame): # type: ignore
            if isinstance(frame, mutagen.id3.GRP1) or isinstance(frame, mutagen.id3.GP1): # type: ignore
                existing_frame = frame
                tmp = getattr(frame, "text")
                if tmp is not None:
                    text = str(tmp[0])
                    items = text.split(GROUP_SEPARATOR)
                    for item in items:
                        if not item.lower() in terms:
                            groups.add(item)
                break

    groups = list(groups)
    groups.sort()

    if existing_frame is not None:
        setattr(existing_frame, "text", GROUP_SEPARATOR.join(groups))
        return True
                        
    return False

def main():
    parser = argparse.ArgumentParser(description='Do actions on MP3 file group tags')
    parser.add_argument('input', help='Folder of media files or a text file containing a list of files')
    parser.add_argument('action', help='(a)dd, (c)opy, (d)elete, (m)ove, (p)rint')
    parser.add_argument('-l','--list', help='List of all files')
    parser.add_argument("-f", "--format", help="Format of output (depends on action)")
    parser.add_argument("-t", "--term", action="append", help="Terms to add, delete, or print")
    parser.add_argument("-o", "--output", help="Output file for copy, move, or print actions")
    parser.add_argument("-d", "--destination", help="Destination directory for copy and move actions")
    parser.add_argument("-p", "--playlist", help="Output playlist title (inside m3u file)")
    parser.add_argument("--dryrun", help="Do a dry run and print results", action="store_true", default=False)
    parser.add_argument("--sidecar", help="Copy/Move sidecar files (.lrc, .txt, .jpg, .png)", action="store_true", default=False)
    parser.add_argument("--case", help="Terms are case sensitive on delete, copy, move, print (default: False)", action="store_true", default=False)
    parser.add_argument("-v", "--verbose", help="Verbose output (default: False)", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print(Fore.RED + "Could not parse command line. Terminating." + Fore.BLACK)
        return

    copy_commands = {"bat":"COPY", "ps1":"COPY", "sh":"cp"}
    move_commands = {"bat":"MOVE", "ps1":"MOVE", "sh":"mv"}
    makedir_commands = {"bat":"MD", "ps1":"MD", "sh":"mkdir"}

    # The single characters are shortcuts
    actions = ["add","a","copy","c","delete","d","move","m","print","p"]
    action = str(args.action).lower()
    idx = -1
    try:
        idx = actions.index(action)
    except:
        print(Fore.RED + "Invalid action: %s" % args.action + Fore.BLACK)
        return

    # normalize the action to the full word, not the shortcut
    if len(action) == 1:
        action = actions[idx - 1]
    
    output_fh = None
    if args.output is None:
        if args.verbose and action in ["copy", "move", "print"]:
            print(Fore.YELLOW + "No output file specified, so sending to stdout. This can be messy when --verbose is used." + Fore.BLACK)
        output_fh = sys.stdout
    else:
        try:
            output_fh = open(args.output, mode="wt", encoding="utf-8")
        except Exception as e:
            print(Fore.RED + "%s: %s" % (args.output, e) + Fore.BLACK)
            return
        
    playlist = datetime.datetime.now().strftime("%B %d, %Y %I:%M%p")
    script_formats = ["bat","ps1","sh"]
    playlist_formats = ["m3u"]
    text_formats = ["txt","csv"]
    formats = script_formats + playlist_formats + text_formats

    format = ""
    if args.format is not None:
        if action == "print":
            if args.format in formats:
                format = args.format
            else:
                print(Fore.RED + "Invalid format: %s" % args.format + Fore.BLACK)
                return
        else:
            format = args.format

    if action in ["copy","move"]:
        if format not in script_formats:
            print(Fore.RED + "Invalid format for %s: %s" % (action, format) + Fore.BLACK)
            return
    
    if len(format) == 0:
        format = "txt"

    terms = list()
    if args.term is not None:
        for term in args.term:
            if args.case or action == "add":
                terms.append(str(term))
            else:
                terms.append(str(term).lower())
    else:
        if action != "print":
            print(Fore.RED + "Term(s) are required for '%s'" % (action) + Fore.BLACK)
            return

    destination = ""
    if args.destination is not None:
        destination = args.destination
        if len(destination) > 1:
            while destination[-1] == os.sep and len(destination) > 1:
                destination = destination[0:-1]
        output_fh.write("%s \"%s\"\n" % (makedir_commands[format], destination))
    else:
        if action in ["copy","move"]:
            print(Fore.RED + "Destination is required for '%s'" % (action) + Fore.BLACK)
            return

    media_extensions = ["mp3","m4a","m4b"]
    lyrics_extensions = ["lrc","txt"]
    image_extensions = ["jpg","png"]
    cover_images = ["cover","front"]
    sidecar_extensions = lyrics_extensions + image_extensions

    if args.list is not None:
        if action != "print":
            print(Fore.RED + "The --list option is only valid for the 'print' action" + Fore.BLACK)
        else:
            with open(args.list,'rt',encoding="utf-8") as f:  
                reader = csv.reader(f) 
                if args.playlist is not None:
                    playlist = args.playlist
                output_fh.write("#EXTM3U\n#PLAYLIST:%s\n" % (playlist))
                for line in reader:
                    if reader.line_num == 1:
                        continue
                    recording = {
                        "path":line[0],
                        "artist": line[1],
                        "album": line[2],
                        "title": line[3],
                        "genre": line[4],
                        "rating": int(line[5]),
                        "year": int(line[6]),
                        "length": int(line[7]),
                        "grouping": line[8]
                    }

                    if len(recording["grouping"]) > 0:
                        do_print = False
                        if len(terms) == 0:
                            do_print = True
                        else:
                            items = recording["grouping"].lower().split(GROUP_SEPARATOR)
                            for item in items:
                                if item in terms:
                                    do_print = True
                                    break

                        if do_print:
                            if format == "txt":
                                output_fh.write("%s: %s\n" % (recording["path"], recording["grouping"]))
                            elif format == "m3u":
                                output_fh.write("#EXTINF:%d, %s - %s - %s\n" % (recording["length"], recording["artist"], recording["album"], recording["title"]))
                                output_fh.write("%s\n" % (recording["path"]))
                            elif format == "csv":
                                output_fh.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%d\"\n" % 
                                                (recording["path"], recording["artist"], recording["album"], recording["title"], recording["grouping"], recording["length"]))
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

    if args.verbose or args.dryrun:
        print(Fore.GREEN + "Files to process: %d" % (len(mediafiles)) + Fore.BLACK)

    if format == "m3u":
        if args.playlist is not None:
            playlist = args.playlist
        output_fh.write("#EXTM3U\n#PLAYLIST:%s\n" % (playlist))
 
    created_dirs = dict()
    for mediafile in mediafiles:
        head,tail = os.path.split(Path(mediafile))
        if args.verbose or args.dryrun:
            print(Fore.GREEN + "%s" % (mediafile) + Fore.BLACK)
        mp3file = MP3(mediafile)

        if mp3file is not None:
            tags = getattr(mp3file, "tags")
            if action == "delete":
                changed = delete_terms_from_group(tags, terms)
                if changed:
                    if args.verbose or args.dryrun:
                        print(Fore.GREEN + "%s" % (getattr(tags['GRP1'], "text")) + Fore.BLACK)
                    if args.dryrun == False:
                        mp3file.save()
                else:
                    print(Fore.YELLOW + "%s: Group 'GRP1' not found" % (mediafile) + Fore.BLACK)
            if action == "add":
                changed = add_terms_to_group(tags, terms)
                if args.verbose or args.dryrun:
                    print(Fore.GREEN + "%s" % (getattr(tags['GRP1'], "text")) + Fore.BLACK)
                if args.dryrun == False:
                    if changed:
                        mp3file.save()
            else:
                thegroup = ""
                theartist = ""
                thealbum = ""
                thetitle = ""
                thelength = int(((mp3file.info.length * 1000) + 1000)/1000)

                for tag in filter(lambda t: t.startswith(("")), tags):
                    frame = tags[tag]
                    if isinstance(frame, mutagen.id3.TextFrame): # type: ignore
                        if isinstance(frame, mutagen.id3.TALB): # type: ignore
                            tmp = getattr(frame, "text")
                            if tmp is not None:
                                thealbum = str(tmp[0])
                        elif isinstance(frame, mutagen.id3.TPE1): # type: ignore
                            tmp = getattr(frame, "text")
                            if tmp is not None:
                                theartist = str(tmp[0])
                        elif isinstance(frame, mutagen.id3.TIT2): # type: ignore
                            tmp = getattr(frame, "text")
                            if tmp is not None:
                                thetitle = str(tmp[0])
                        elif isinstance(frame, mutagen.id3.GRP1) or isinstance(frame, mutagen.id3.GP1): # type: ignore
                            tmp = getattr(frame, "text")
                            if tmp is not None:
                                if thegroup == "":
                                    thegroup = GROUP_SEPARATOR.join(tmp)
                                else:
                                    print(Fore.YELLOW + "Found multiple Group tags. Keeping '%s', ignoring '%s'" % (thegroup, str(tmp)) + Fore.BLACK)

                                if args.verbose:
                                    print(Fore.GREEN + "Found Group: %s" % (str(tmp)) + Fore.BLACK)

                if action == "print":
                    if len(thegroup) > 0:
                        do_print = False
                        if len(terms) == 0:
                            do_print = True
                        else:
                            items = thegroup.lower().split(GROUP_SEPARATOR)
                            for item in items:
                                if item in terms:
                                    do_print = True
                                    break

                        if do_print:
                            if format == "txt":
                                output_fh.write("%s: %s\n" % (mediafile, thegroup))
                            elif format == "m3u":
                                output_fh.write("#EXTINF:%d, %s - %s - %s\n" % (thelength, theartist, thealbum, thetitle))
                                output_fh.write("%s\n" % (mediafile))
                            elif format == "csv":
                                output_fh.write("\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%d\"\n" % (mediafile, theartist, thealbum, thetitle, thegroup, thelength))
                elif action == "copy" or action == "move":
                    if len(thegroup) > 0:
                        do_command = False
                        if len(terms) == 0:
                            do_command = True
                        else:
                            items = thegroup.lower().split(GROUP_SEPARATOR)
                            for item in items:
                                if item in terms:
                                    do_command = True
                                    break

                        if do_command:
                            command = ""
                            if action == "copy":
                                command = copy_commands[format]
                            else:
                                command = move_commands[format]

                            action_files = list()
                            action_files.append(mediafile)

                            if args.sidecar:
                                idx = mediafile.rfind('.')
                                if idx >= 0:
                                    pattern = mediafile[0:idx] + ".*"
                                    files = glob.glob(pattern)
                                    for file in files:
                                        filename = str(file)
                                        if get_ext(filename, tolower=True) in sidecar_extensions:
                                            action_files.append(file)

                            for file in action_files:
                                desthead,desttail = os.path.split(Path(file))
                                dest_dir = destination
                                src_dir = args.input

                                root_path = desthead.split(os.sep)
                                if len(root_path) > 1:
                                    for dir in root_path[1:]:
                                        src_dir += os.sep + dir
                                        dest_dir += os.sep + dir
                                        if dest_dir not in created_dirs:
                                            output_fh.write("%s \"%s\"\n" % (makedir_commands[format], dest_dir))
                                            created_dirs[dest_dir] = src_dir
                                    
                                dest_filename = dest_dir + os.sep + desttail
                                output_fh.write("%s \"%s\" \"%s\"\n" % (command, file, dest_filename))

    # Clean up, get the cover.jpg and other directory-specific files  
    if action == "copy" or action == "move":
        if action == "copy":
            command = copy_commands[format]
        else:
            command = move_commands[format]
        if args.sidecar:
            for key in created_dirs:
                for sidecar in image_extensions:
                    for image in cover_images:
                        pattern = created_dirs[key] + os.sep + image + "." + sidecar
                        files = glob.glob(pattern)
                        for file in files:
                            idx = file.rfind(os.sep)
                            dest_file = key + os.sep + file[idx + 1:]
                            output_fh.write("%s \"%s\" \"%s\"\n" % (command, file, dest_file))


if __name__ == '__main__':
    main()
