# media-handling-scripts

This is a collection of Python scripts that I use to manage my music collection.
It's not the best code I've ever written, but it's not meant to be a product. It
works for me, hopefully it will work as a basis for others.

Feel free to take what you need. There are no licenses as these are cobbled 
together from the collective ideas of hundreds of people on StackOverflow and 
various forums.

My collection is deliberately lossy. FLACs are great, but they consume a lot of 
disk space. PLUS, I have noticeable hearing loss, so the extra sonic space is
mostly lost on me. MP3 at 320K bitrate works for my needs, as this library is
being streamed via Navidrome and typically sent to Bluetooth devices. If I were
playing from a dedicated device to a high-end audio system, I'd feel differently.

## Notes

* Pylance complains about subclasses not being exported by mutagen. Even though it flags this
as an error, it does work. This should be a warning, but Pylance treats it as an error. It's safe
to ignore.
* I should refactor the file scanning code into a separate module, as I use it in nearly every
one of these scripts. Someday...

## Requirements

You may need some or all of these to run the scripts. Sorry, I don't have a requirements.txt
for you to run.

* beautifulsoup4
* bs4
* eyeD3
* ffcuesplitter
* ffmpeg
* ffprobe
* lxml
* musicbrainzngs
* mutagen
* PlexAPI
* pyffmpeg
* python-ffmpeg
* python-slugify
* regex
* requests
* requests-oauthlib
* setuptools
* Unidecode
* urllib3 
