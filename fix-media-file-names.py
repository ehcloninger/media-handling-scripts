'''
fix-media-file-names - Attempt to normal file names by removing a bunch of the stuff that uploaders do.
'''
import os
import argparse
import pathlib 
from timeit import default_timer as timer
from unidecode import unidecode
from ffmpeg import FFmpeg
import mutagen
import mutagen.id3

def get_ext(filename, tolower=False) -> str:
    ext = ""
    idx = filename.rfind('.')
    if idx >= 0:
        ext = filename[idx + 1:]
    if tolower:
        return ext.lower()
    else:
        return ext

'''
extractPairedCharacters - Removes strings that are bounded by parentheses, brackets, etc.
'''
def extractPairedCharacters(input:str, startChar:str, endChar:str) -> str:
    ret = input
    while True:
        idx = ret.find(startChar)
        if idx >= 0:
            idx2 = ret.find(endChar, idx)
            if idx2 >= 0:
                ret = ret[:idx] + ret[idx2 + 1:]
                ret = ret.strip()
            else:
                return ret
        else:
            return ret

    return ret

'''
extractStrings - Remove specific words from the input string (e.g. PMEDIA and friends)
'''
def extractStrings(input:str, words:list) -> str:
    ret = input
    for word in words:
        while True:
            idx = ret.find(word)
            if idx >= 0:
                ret = ret[:idx] + ret[idx + len(word) + 1:]
                ret = ret.strip()
            else:
                break

    return ret

def stripStrings(input:str, minlength=0) -> str:
    ret = ""
    # Anything in parens, brackets
    ret = extractPairedCharacters(input, '(', ')')
    ret = extractPairedCharacters(ret, '[', ']')
    ret = extractPairedCharacters(ret, '<', '>')

    # These words that appear often in YTM and torrent file names
    ret = extractStrings(ret, ["VEVO", "vevo", "Vevo", "PMEDIA", "pmedia"])

    # Trailing spaces
    ret = ret.strip()

    # Periods at the end of the base name
    while ret[-1:] == '.':
        ret = ret[0:-1]

    # double spaces
    ret = ret.replace('  ', ' ')

    # We took everything, so maybe try something less drastic
    # Assumes the file names are DD-TTT - Title.ext
    if len(ret) < minlength:
        ret = input
        ret = ret.replace("(", "")
        ret = ret.replace(")", "")
        ret = ret.replace("[", "")
        ret = ret.replace("]", "")
        if len(ret) < minlength:
            return input

    return ret

def main():
    parser = argparse.ArgumentParser(description='Convert FLAC files to mp3')
    parser.add_argument('input', help='Media file or a folder of media files')
    # parser.add_argument("-b", "--bitrate", help="Bitrate (default = 320)", default=320)
    # parser.add_argument("-o", "--overwrite", help="Overwrite output?", action="store_true", default=False)
    # parser.add_argument("-d", "--delete", help="Delete FLAC on successful conversion?", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    extensions = ["flac","mkv","mp3","m4a","m4b","lrc"]

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
    for mediafile in mediafiles:
        head,tail = os.path.split(mediafile)
        idx = tail.rfind('.')
        if idx == -1:
            print("Cant process %s" % (mediafile))
            continue

        extension = tail[idx:]
        outputfilename = tail[:idx]

        idx = outputfilename.find(" - ")
        if idx >= 0:
            idx += 3

        ret = stripStrings(outputfilename, idx + 1)

        # TODO: Unicode extended characters used to bypass ASCII (e.g. emdash, division sign)
        if ret == outputfilename:
            continue

        newfilename = head + os.sep + ret + extension

        print("%s -> %s" % (mediafile, newfilename))
        try:
            os.rename(mediafile, newfilename)
        except Exception as e:
            ret = outputfilename
            ret = ret.replace('(', "")
            ret = ret.replace(')', "")
            ret = ret.replace('[', "")
            ret = ret.replace(']', "")
            newfilename = head + os.sep + ret + extension
            print("Error renaming %s. Retry with %s" % (tail, newfilename))
            os.rename(mediafile, newfilename)
        else:
            try:
                id3file = mutagen.id3.ID3(newfilename)
                if id3file is not None:
                    for tag in filter(lambda t: t.startswith(("")), id3file):
                        frame = id3file[tag]
                        if isinstance(frame, mutagen.id3.TIT2): # type: ignore
                            text = getattr(frame,"text")
                            if len(text) > 0:
                                ret = str(text[0])
                                ret = stripStrings(ret, 0)
                                if ret != text:
                                    setattr(frame, "text", ret)
                                    id3file.save()
                                    break
            except:
                pass # not an MP3 file
if __name__ == '__main__':
    main()
