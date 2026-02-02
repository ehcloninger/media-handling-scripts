'''
flac-to-mp3 - Recursively convert FLAC audio (and mkv) into mp3 at a specified bitrate

FLAC is great, but it produces really large files. For the collector looking to pare down
their collection for internet streaming, it's better to use MP3 at a high bit rate. I chose
320k by default. However, if the source material can't support 320k, ffmpeg is going to
downsample to whatever it chooses.

'''

import os
import argparse
from pathlib import Path
from timeit import default_timer as timer
from ffmpeg import FFmpeg

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
    parser.add_argument("-b", "--bitrate", help="Bitrate (default = 320)", default=320)
    parser.add_argument("-o", "--overwrite", help="Overwrite output?", action="store_true", default=False)
    parser.add_argument("-d", "--delete", help="Delete FLAC on successful conversion?", action="store_true", default=False)

    args = parser.parse_args()

    if (args is None):
        print("Could not parse command line. Terminating.")
        return

    extensions = ["flac","mkv"]

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

    # Copy the metadata from the source material. Generate ID3v2.3 (although 2.4 is better)
    output_options = {'map_metadata':'0', 'id3v2_version':'3', 'ab':'%dk' % (args.bitrate)}
    overwrite = 'n'
    if args.overwrite:
        overwrite = 'y'

    total = len(mediafiles)
    i = 1
    start = timer()
    for mediafile in mediafiles:
        head,tail = os.path.split(Path(mediafile))
        idx = mediafile.rfind('.')
        if idx == -1:
            print("Cant process %s" % (mediafile))
            continue

        outputfilename = mediafile[:idx] + ".mp3"

        # Make sure there isn't a .cue file that needs to be processed first. The presence of a 
        # cue file for the album suggests there is a single file that needs to be split first.
        # If this is detected, don't process but alert the user to what they need to do.
        cuefilename = mediafile[:idx] + ".cue"
        if os.path.exists(cuefilename):
            print("Cue file exists for %s. Skipping. Try\n ffcuesplitter -i \"%s\" -f mp3 -o \"%s\"" % (mediafile, cuefilename, mediafile[:idx]))
            continue
        cuefilename = mediafile + ".cue"
        if os.path.exists(cuefilename):
            print("Cue file exists for %s. Skipping. Try\n ffcuesplitter -i \"%s\" -f mp3 -o \"%s\"" % (mediafile, cuefilename, mediafile[:idx]))
            continue
        
        print("%d/%d: %s" % (i, total, mediafile))
        i += 1

        if os.path.exists(outputfilename) and not args.overwrite:
            print('Output file exists: %s' % (outputfilename))
        else:
            try:
                ffmpeg = (FFmpeg()
                    .option(overwrite)
                    .input(mediafile)
                    .output(
                        outputfilename,
                        output_options
                    )
                ) 
                ffmpeg.execute()
            except Exception as e:
                print("Error converting %s: %s" % (mediafile, e))
            else:
                if args.delete:
                    os.remove(mediafile)
    end = timer()
    print("Duration: %10.2d" % (end - start))

if __name__ == '__main__':
    main()
