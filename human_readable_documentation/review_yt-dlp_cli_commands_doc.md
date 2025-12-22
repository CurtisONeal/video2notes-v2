review_yt-dlp_cli_commands_doc.md

# CLI Commands
https://github.com/yt-dlp/yt-dlp

yt-dlp is a feature-rich command-line audio/video downloader with support for [thousands of sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md). The project is a fork of [youtube-dl](https://github.com/ytdl-org/youtube-dl) based on the now inactive [youtube-dlc](https://github.com/blackjack4494/yt-dlc).

## README.md
https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file

## Example command

```
$ yt-dlp --print filename -o "test video.%(ext)s" BaW_jenozKc
test video.webm    # Literal name with correct extension

$ yt-dlp --print filename -o "%(title)s.%(ext)s" BaW_jenozKc
youtube-dl test video ''_ä↭𝕐.webm    # All kinds of weird characters

$ yt-dlp --print filename -o "%(title)s.%(ext)s" BaW_jenozKc --restrict-filenames
youtube-dl_test_video_.webm    # Restricted file name

# Download YouTube playlist videos in separate directory indexed by video order in a playlist
$ yt-dlp -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" "https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re"

# Download YouTube playlist videos in separate directories according to their uploaded year
$ yt-dlp -o "%(upload_date>%Y)s/%(title)s.%(ext)s" "https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re"

# Prefix playlist index with " - " separator, but only if it is available
$ yt-dlp -o "%(playlist_index&{} - |)s%(title)s.%(ext)s" BaW_jenozKc "https://www.youtube.com/user/TheLinuxFoundation/playlists"

# Download all playlists of YouTube channel/user keeping each playlist in separate directory:
$ yt-dlp -o "%(uploader)s/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" "https://www.youtube.com/user/TheLinuxFoundation/playlists"

----------
# Download Udemy course keeping each chapter in separate directory under MyVideos directory in your home

$ yt-dlp -u user -p password -P "~/MyVideos" -o "%(playlist)s/%(chapter_number)s - %(chapter)s/%(title)s.%(ext)s" "https://www.udemy.com/java-tutorial"
----------

# Download entire series season keeping each series and each season in separate directory under C:/MyVideos
$ yt-dlp -P "C:/MyVideos" -o "%(series)s/%(season_number)s - %(season)s/%(episode_number)s - %(episode)s.%(ext)s" "https://videomore.ru/kino_v_detalayah/5_sezon/367617"

# Download video as "C:\MyVideos\uploader\title.ext", subtitles as "C:\MyVideos\subs\uploader\title.ext"
# and put all temporary files in "C:\MyVideos\tmp"

$ yt-dlp -P "C:/MyVideos" -P "temp:tmp" -P "subtitle:subs" -o "%(uploader)s/%(title)s.%(ext)s" BaW_jenozKc --write-subs

# Download video as "C:\MyVideos\uploader\title.ext" and subtitles as "C:\MyVideos\uploader\subs\title.ext"
$ yt-dlp -P "C:/MyVideos" -o "%(uploader)s/%(title)s.%(ext)s" -o "subtitle:%(uploader)s/subs/%(title)s.%(ext)s" BaW_jenozKc --write-subs

# Stream the video being downloaded to stdout
$ yt-dlp -o - BaW_jenozKc
```

## Test
`yt-dlp --print filename -o "test video.%(ext)s" BaW_jenozKc
test video.webm    # Literal name with correct extension`

## Authentication with netrc

[nrc github](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#authentication-with-netrc)

You may also want to configure automatic credentials storage for extractors that support authentication (by providing login and password with `--username` and `--password`) in order not to pass credentials as command line arguments on every yt-dlp execution and prevent tracking plain text passwords in the shell command history. You can achieve this using a [`.netrc` file](https://stackoverflow.com/tags/.netrc/info) on a per-extractor basis. For that, you will need to create a `.netrc` file in `--netrc-location` and restrict permissions to read/write by only you:

```
touch ${HOME}/.netrc
chmod a-rwx,u+rw ${HOME}/.netrc
```

After that, you can add credentials for an extractor in the following format, where _extractor_ is the name of the extractor in lowercase:

```
machine <extractor> login <username> password <password>
```

E.g.

```
machine youtube login myaccount@gmail.com password my_youtube_password
machine twitch login my_twitch_account_name password my_twitch_password
```

To activate authentication with the `.netrc` file you should pass `--netrc` to yt-dlp or place it in the [configuration file](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#configuration).



## installation 
|                                                                                            |                                                                                                                                           |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp)                 | Platform-independent [zipimport](https://docs.python.org/3/library/zipimport.html) binary. Needs Python (recommended for **Linux/BSD**)\| |
| \|[yt-dlp_macos](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos)\| | Universal MacOS (10.15+) standalone executable (recommended for **MacOS**)                                                                |

### [Homebrew](https://formulae.brew.sh/formula/yt-dlp)

https://github.com/yt-dlp/yt-dlp/wiki/Installation#homebrew

macOS or Linux users that are using Homebrew can also install it by:

```shell
brew install yt-dlp
```

To update, run:

```shell
brew upgrade yt-dlp
```

##  Update
You can use `yt-dlp -U` to update if you are using the [release binaries](https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#release-files)

## zipimport
https://docs.python.org/3/library/zipimport.html
his module adds the ability to import Python modules (`*.py`, `*.pyc`) and packages from ZIP-format archives. It is usually not needed to use the [`zipimport`](https://docs.python.org/3/library/zipimport.html#module-zipimport "zipimport: Support for importing Python modules from ZIP archives.") module explicitly; it is automatically used by the built-in [`import`](https://docs.python.org/3/reference/simple_stmts.html#import) mechanism for [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path "sys.path") items that are paths to ZIP archives.
