'''
fix-ytm-titles - Attempt to normal file names from yt-dlp
'''
import os
import argparse
import pathlib 
from timeit import default_timer as timer
from unidecode import unidecode
from ffmpeg import FFmpeg
import mutagen
import mutagen.id3

def replace_unicode(input:str) -> str:
    ret = input
    ret = ret.replace('⧸','/')
    ret = ret.replace('＂','')
    ret = ret.replace('’','\'')
    ret = ret.replace('？','?')
    ret = ret.replace('，',',')
    ret = ret.replace('‘','\'')
    
    return ret

def is_number(s):
    try:
        int(s)
    except ValueError:  # Failed
        return False
    else:  # Succeeded
        return True
    
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
    parser = argparse.ArgumentParser(description='Convert FLAC files to mp3')
    parser.add_argument('input', help='Media file or a folder of media files')
    parser.add_argument('-o', '--output', help='Media file or a folder of media files', default="output.bat")

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    extensions = ["flac","mkv","mp3","m4a","m4b"]

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
    with open(args.output, mode="wt", encoding="utf-8") as file:
        for mediafile in mediafiles:
            head,tail = os.path.split(mediafile)
            idx = tail.rfind('.')
            if idx == -1:
                print("Cant process %s" % (mediafile))
                continue

            extension = str(tail[idx:])
            outputfilename = str(tail[:idx])

            ret = outputfilename

            idx = ret.find("-")
            if (idx < 0):
                continue

            track = ""
            tmp = str(ret[0:idx - 1]).strip()
            if is_number(tmp):
                track = tmp
                ret = ret[idx + 1:]
                idx = ret.find("-")
                if (idx < 0):
                    continue

            artist = str(ret[0:idx]).strip()
            title = str(ret[idx + 1:]).strip()

            if len(artist) == 0:
                continue
            
            if len(title) == 0:
                continue
            
            artist = replace_unicode(artist)
            title = replace_unicode(title)

            if track == "":
                ret = title + extension
            else:
                ret = track + " - " + title + extension

            if ret == outputfilename:
                continue

            file.write("eyed3 \"%s\" -a \"%s\" -b \"%s\" -t \"%s\"\n" % (mediafile, artist, artist, title))
            file.write("REN \"%s\" \"%s\"\n" % (mediafile, ret))

if __name__ == '__main__':
    main()
