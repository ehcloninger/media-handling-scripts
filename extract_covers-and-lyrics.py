import eyed3    # pip install eyed3: library used to manipulate ID3 tags from mp3 files
from PIL import Image  # pip install pillow: library used to store jpg image files

from slugify import slugify  # pip install python-slugify # https://github.com/un33k/python-slugify
# library used for getting failsafe filenames (album has sometimes some not failsafe chars to be used in filenames)

import sys
import os
import json
import io
import argparse  # used for easy command line argument parser

IMAGE_EXTENSION = '.jpg'
SONGS_EXTENSION = '.mp3'
COVER_ART_FILE = 'cover.jpg'
EXCLUDED_SUBDIR = 'TEMP'  # subdirs with this name are skipped from searching inside

def get_data_files(data_files_directory, file_type):
    """
    :param data_files_directory: directory filename where the files are stored
    :param file_type: filename extension to search inside directory
    :return:  files_list: list with the filenames found
    """

    total_files = 0
    subfolder_files = 0
    files_list = list()

    try:
        for input_file in os.listdir(data_files_directory):
            full_path_input_file = os.path.join(data_files_directory, input_file)
            if os.path.isdir(full_path_input_file):
                # subdirectories processed in recursive way
                if input_file == EXCLUDED_SUBDIR:
                    # The TEMP processing subdir created by the app is not processed!
                    continue
                # recursive call!!!!
                inside_list = list()
                inside_list = get_data_files(full_path_input_file, file_type)

                cover_name = os.path.join(data_files_directory, COVER_ART_FILE)
                if not os.path.isfile(cover_name):
                    total_files += len(inside_list)
                    files_list.extend(inside_list)
                continue

            file_name, file_extension = os.path.splitext(input_file)

            if file_extension.lower() == (file_type):
                files_list.append(full_path_input_file)
                total_files += 1
                subfolder_files += 1

    except Exception as e:  # we verify the creation of output folder

        print('get-Data-Files: '
              + 'File Type: ' + str(file_type) + ' Data Directory: ' + str(data_files_directory)
              + ' has not been possible to read the files inside'
              )
        print('get-Data-Files: Exception 001: ' + str(e))
        exit(1)

    # print('get-Data-Files: '
    #      + 'File Type: ' + str(file_type) + ' Data Directory: ' + str(data_files_directory)
    #      + ' has ' + str(subfolder_files) + ' files inside'
    #      )

    return files_list


if __name__ == '__main__':
    """
    :param directory: directory filename where the files are stored
    :return:  
        n jpg files: extracted cover art jpg from every mp3 with cover art file embebed
        json COVER_ART_DATA_FILE with full info about the extracted cover art files
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='folder to parse mp3 files')
    parser.add_argument('-v','--overwrite', action="store_true", help='Overwrite', default=False)

    args = parser.parse_args()
    mp3_directory = args.directory

    # mp3_directory = r'D:\L01 Downloads\Music\[MP3]\2021 - VA - Karaoke Hits Essentials'
    # mp3_directory = r'D:\L01 Downloads\Music\[MP3]\2021 - VA - Disco Hits Essentials'
    # mp3_directory = r'D:\L01 Downloads\Music\[MP3]\2021 - VA - Karaoke Hits Essentials\TEMP'

    print('MP3 Input Directory used:' + mp3_directory)

    files_type = SONGS_EXTENSION
    mp3_files = get_data_files(mp3_directory, files_type)

    # print(*mp3_files, sep='\n') # Pretty Print https://stackoverflow.com/a/35211376

    print('MP3 Files to review: ' + str(len(mp3_files)))
    images_stored = 0
    lyrics_stored = 0
    album_data_list = list()
    covers_completed = set()
    lyrics_completed = set()
    for song_file in mp3_files:
        album_data = dict()
        safe_cover_name = "cover"

        # print("> %s" % (song_file))
        eyed3.log.setLevel("ERROR")
        song = eyed3.load(song_file)

        ##################################################################################################
        #                                 END BUILDING COVER ART FILENAME                                #
        #                                                                                                #
        ##################################################################################################
        # if there contains many images
        # https://stackoverflow.com/a/63145832
        tag = getattr(song, "tag")
        head, tail = os.path.split(song_file)
        cover_name = os.path.join(head, COVER_ART_FILE)
        if not head in covers_completed:
            print("%s" % head)
            if not os.path.isfile(cover_name) or args.overwrite:
                images = getattr(tag, "images")
                img = Image.open(io.BytesIO(images[0].image_data)).convert(mode="RGB")
                try:
                    img.save(cover_name)
                    covers_completed.add(head)
                except Exception as e:  # Exception: we cannot recover the cover art and store it at the output file
                    print("Problem extracting cover art from " + song_file)
                    print(str(e))
                    continue
                else:
                    images_stored += 1

        idx = tail.rfind(".")
        if idx > 0:
            tail = tail[0:idx] + ".txt"
        else:
            tail += ".txt"
        lyrics_name = os.path.join(head, tail)
        if not os.path.isfile(lyrics_name) or args.overwrite:
            lyrics = getattr(tag, "lyrics")
            if lyrics is not None:
                if len(lyrics) > 0:
                    the_str = ""
                    for lyric in lyrics:
                        data = getattr(lyric, "text")
                        if data is not None:
                            the_str += data
                        else:
                            data = getattr(lyric, "data")
                            if data is not None:
                                data = bytes(data)
                                tmp_str = data.decode(encoding="utf-8")
                                if the_str[0] == '\x03':
                                    idx = the_str.find('\x00')
                                    if idx >= 0:
                                        the_str = the_str[idx + 1:]
                                    the_str = the_str.replace('\x00','')
                                the_str += tmp_str
                    try:
                        with open(lyrics_name, mode="wt", encoding="utf-8") as file:
                            file.write("%s\n" % (the_str))
                    except Exception as e:
                        print("Problem extracting lyrics from " + song_file)
                        print(str(e))
                        continue
                    lyrics_stored += 1

    print("Images stored to disk: " + str(images_stored))
    print("Lyrics stored to disk: " + str(lyrics_stored))
    sys.exit()
