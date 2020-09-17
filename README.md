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
- `-m, --max-downloads` will limit the number of episodes to be downloaded to the specified integer
- `-w, --write-list` is the option to write an ordered list of the episodes in the podcast in several different formats, as specified:
  - `none`
  - `text`
  - `audacious`
- `-t, --threads` is the number of threads to run concurrently; defaults to 10
- `--max-attempts` will specify the number of reattempts for a failed or refused connection. See below for more details.
- `--skip-download` will do everything but download the files. Useful for updating episode playlists without a lengthy download.
- `--verify` will scan existing files for ones with a file-size outside a 2% and list them in `results.txt`

- `-s, --suppress-progress` will disable all progress bars
- `-v, --verbose` will increase the verbosity of the information output to the console
- `--log` will log all messages to a debug level (the equivalent of `-v`) to the specified file, appending if it already exists

The `--feed`, `--file`, and `--opml` flags can all be specified multiple times to aggregate feeds from multiple locations.

Of these, only the destination is required, though one or more feeds or one or more OPML files must be provided or the program will just complete instantly.

### Maximum Reattempts

In some cases, particularly when downloading a single or a few specific podcasts with a lot of episodes at once, the remote server will receive a number of simultaneous or consecutive requests. As this may appear to be atypical behaviour, this server may refuse or close incoming connections as a rate-limiting measure. This is normal in scraping servers that do not want to be scraped.

There are several countermeasures in the downloader for this behaviour, such as randomising the download list to avoid repeated calls to the same server in a short amount of time, but this may not work if there is only one or a few podcast feeds to download. As such, the method of last resort is a sleep function to wait until the server allows the download to continue. This is done with increasing increments of 30 seconds, with the maximum number or reattempts specified by the `--max-attempts` argument. For example, if left at the default of 10, the program will sleep for 30 seconds if the connection is refused. Then, if it was refused again, it will sleep for 60 before reattempting the download. It will do this until the 10th attempt, where it will sleep for 300 seconds, or five minutes. If the connection is refused after this, then an error will occur and the download thread will move on to the next podcast episode.

The maximum number of reattempts may need to be changed in several cases. If you wish to download the episode regardless of anything else, then you may want to increase the argument. This may result in longer wait times for the downloads to complete. However, a low argument will make the program skip downloads if they time out repeatedly, missing content but completing faster.

### Warnings

The `--write-list` option should not be used with the `--limit` option. The limit option will be applied to the episode list in whatever format chosen, and this will overwrite any past episode list files. For example, if a `--limit` of 5 is chosen with `-w audacious`, then the exported Audacious playlist will only be 5 items long. Thus the `-w` option should only be used when there is not a limit.

## Example Command

Following is an example command to download a single feed to a podcasts folder.

`python3 -m podcastdownloader media/podcasts --f 'http://linustechtips.libsyn.com/wanshow' -o podcasts.opml`

## Podcast Feed Files

A feed file, for use with the `--file` option, is a simple text file with one URL that leads to the RSS feed per line. The podcastdownloader will ignore all lines beginning with a hash (#), as well as empty lines to allow comments and a rudimentary structure if desired.
