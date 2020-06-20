# podcast-downloader

This is a simple tool for downloading all the available episodes in an RSS feed to disk, where they can be listened to offline. 

Firstly, Python 3 must be installed, then the requirements must be installed. These are documented in `requirements.txt` and can be installed via the command `python3 -m pip install -r requirements.txt`.

## Arguments

There are three arguments to be supplied to the program:

- `destination` is the directory that the folder structure will be created in and the podcasts downloaded to
- `-f, --feed` is the URL for the RSS feed of the podcast
- `-o, --opml` is the location of an OPML file with podcast data
- `--file` is the location of a simple text file with an RSS feed URL on each line
- `-l, --limit` is the maximum number of episodes to try and download from the feed. If left blank, it is all episodes, but a small number is fastest for updating a feed
- `-t, --threads` is the number of threads to run concurrently; defaults to 10

Of these, only the destination is required, though one or more feeds and an OPML file must be provided or the program will just complete instantly.

## Example Command

Following is an example command to download a single feed to a podcasts folder.

`python3 -m podcastdownloader media/podcasts --f 'http://linustechtips.libsyn.com/wanshow' -o podcasts.opml`
