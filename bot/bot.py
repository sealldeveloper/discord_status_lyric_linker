import linecache
import os
import platform
import subprocess
import sys
import time

import fpstimer
import grequests
import requests
import rich
import spotipy
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
API_TOKEN = os.environ.get("DISCORD_AUTH")  # https://discordhelp.net/discord-token
SPOTIFY_ID = os.environ.get("SPOTIFY_ID")
SPOTIFY_SECRET = os.environ.get("SPOTIFY_SECRET")
SPOTIFY_REDIRECT = os.environ.get("SPOTIFY_REDIRECT")
CUSTOM_STATUS = os.environ.get("STATUS")
NITRO = os.environ.get("NITRO")

if NITRO == "TRUE":
    CUSTOM_STATUS_EMOJI_NAME = os.environ.get("STATUS_EMOJI_NAME")
    CUSTOM_STATUS_EMOJI_ID = os.environ.get("STATUS_EMOJI_ID")

else:
    CUSTOM_STATUS_EMOJI_NAME = os.environ.get("STATUS_EMOJI_NAME")

SCOPE = "user-read-currently-playing"

LYRIC_UPDATE_RATE_PER_SECOND = 10  # Rate at which the program updates the number of milliseconds passed to change lyrics.
SECONDS_TO_SPOTIFY_RESYNC = 10  # Rate at which Spotify is polled for currently playing song and time. Low numbers will be more consistent but may result in ratelimiting.

TIMER = fpstimer.FPSTimer(LYRIC_UPDATE_RATE_PER_SECOND)

last_line = ""


class StatusScreen:  # working on, currently dead code
    def __init__(self):
        self.console = rich.console.Console(color_system="auto")

    def print_if_different(self, text):
        global last_line
        if text != last_line:
            self.console.print(text)
            last_line = text


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print(f'EXCEPTION IN ({filename}, LINE {lineno} "{line.strip()}"): {exc_obj}')


def grequest_if_different(text, status):
    global last_line
    if text != last_line:
        print(status)
        send_grequest(text)
        last_line = text


def request_if_different(text, status):
    global last_line
    if text != last_line:
        print(status)
        send_request(text)
        last_line = text


def send_grequest(text):
    if NITRO == "TRUE":
        req = grequests.patch(
            url="https://discord.com/api/v6/users/@me/settings",
            headers={"authorization": API_TOKEN},
            json={
                "custom_status": {
                    "text": text,
                    "emoji_name": CUSTOM_STATUS_EMOJI_NAME,
                    "emoji_id": CUSTOM_STATUS_EMOJI_ID,
                }
            },
            timeout=10,
        )
    else:
        req = grequests.patch(
            url="https://discord.com/api/v6/users/@me/settings",
            headers={"authorization": API_TOKEN},
            json={
                "custom_status": {
                    "text": text,
                    "emoji_name": CUSTOM_STATUS_EMOJI_NAME,
                }
            },
            timeout=10,
        )
    grequests.send(req, grequests.Pool(1))


def send_request(self, text):
    if NITRO == "TRUE":
        requests.patch(
            url="https://discord.com/api/v6/users/@me/settings",
            headers={"authorization": API_TOKEN},
            json={
                "custom_status": {
                    "text": text,
                    "emoji_name": CUSTOM_STATUS_EMOJI_NAME,
                    "emoji_id": CUSTOM_STATUS_EMOJI_ID,
                }
            },
            timeout=10,
        )
    else:
        requests.patch(
            url="https://discord.com/api/v6/users/@me/settings",
            headers={"authorization": API_TOKEN},
            json={
                "custom_status": {
                    "text": text,
                    "emoji_name": CUSTOM_STATUS_EMOJI_NAME,
                }
            },
            timeout=10,
        )


def clear():  # working on, currently dead code
    if platform.system() == "Windows":
        if platform.release() in {"10", "11"}:
            subprocess.run(
                "", shell=True, check=True
            )  # Needed to fix a bug regarding Windows 10; not sure about Windows 11
            print("\033c", end="")
        else:
            subprocess.run(["cls"], check=True)
    else:  # Linux and Mac
        print("\033c", end="")


def status_screen():  # working on, currently dead code
    console = rich.console.Console(color_system="auto")
    console.print(
        "┌─────"
        "[link=https://www.willmcgugan.com]discord-status-lyric-linker[/link]"
        "─────┐"
    )


def main(last_played_song, last_played_line, song, lyrics, rlyrics):
    start = time.time()

    # IF NO SONG IS PLAYING
    if not song:
        if last_played_line == "NO SONG":
            TIMER.sleep()
            return "", "NO SONG"
        request_if_different(
            CUSTOM_STATUS,
            "DISCORD: NOT CURRENTLY LISTENING UPDATE",
        )
        TIMER.sleep()
        return "", "NO SONG"

    current_time = song["progress_ms"]
    song_length = song["item"]["duration_ms"]
    song_name = song["item"]["external_ids"]["isrc"]
    # artist_name = song["item"]["artists"][0]["name"]
    # formatted_currently_playing = f"{song_name} -- {artist_name}"

    # IF THERE ARE NO LYRICS
    if lyrics["error"] is True or lyrics["syncType"] == "UNSYNCED":
        # RESERVE LYRICS
        if rlyrics is not False and 'lines' in rlyrics:
            next_line = get_next_line(rlyrics, current_time, song_length)
            if next_line == "♪" and CUSTOM_STATUS_EMOJI_NAME != "":
                grequest_if_different("", "")
            elif (
                last_played_line != next_line
            ):  # no need to update if the line hasn't changed.
                grequest_if_different(next_line, "DISCORD: NEW LYRIC LINE (RESERVE)")
                last_played_line = next_line
        # If we've already been here (and it's the same song), don't bother changing again, just return.
        else:
            if last_played_line == "NO LYRICS" and song_name == last_played_song:
                TIMER.sleep()
                return song_name, last_played_line
            grequest_if_different(
                CUSTOM_STATUS,
                "DISCORD: NO SYNCED LYRICS",
            )
            last_played_line = "NO LYRICS"
            TIMER.sleep()
            return song_name, last_played_line

    # IF THERE ARE LYRICS
    else:
        next_line = get_next_line(lyrics, current_time, song_length)
        if next_line == "♪" and CUSTOM_STATUS_EMOJI_NAME != "":
            grequest_if_different("", "")
        elif (
            last_played_line != next_line
        ):  # no need to update if the line hasn't changed.
            grequest_if_different(next_line, "DISCORD: NEW LYRIC LINE")
            last_played_line = next_line
    TIMER.sleep()
    end = time.time()
    milliseconds = (end - start) * 1000
    song["progress_ms"] += milliseconds
    return song_name, last_played_line


def get_next_line(lyrics, current_time, song_length):
    try:
        min_time = 100000000
        next_line = ""
        if 'lines' in lyrics.keys():
            for line in lyrics["lines"]:
                    milliseconds_past_line = current_time - round(float(line["startTimeMs"]))
                    if milliseconds_past_line < min_time and milliseconds_past_line > 0:
                        min_time = milliseconds_past_line
                        next_line = line["words"]
            first_lyric=round(float(lyrics["lines"][0]['startTimeMs']))
            if current_time <= first_lyric:
                next_line = "♪"
            if 'endTimeMs' in lyrics["lines"][len(lyrics)-1].keys():
                last_lyric=round(float(lyrics["lines"][len(lyrics)-1]['endTimeMs']))
                print(last_lyric,current_time)
                if last_lyric != 0.0 and current_time > last_lyric:
                    next_line = "♪"
        return next_line
    except:
        PrintException()


def on_new_song(sp,last_played):
    print("SPOTIFY: LISTENING REQUEST MADE")
    current_song = sp.current_user_playing_track()
    if current_song is not None:
        isrc = current_song["item"]["external_ids"]["isrc"]
        if isrc != last_played or last_played == "":
            print("FETCHING LYRICS, NEW SONG")
            track_id = current_song["item"]["uri"].split(":")[-1]
            current_lyrics = get_lyrics(track_id)
            reserve_lyrics = get_reserve_lyrics(isrc)
            return current_song, reserve_lyrics, current_lyrics, isrc
        else:
            return current_song, False, False, isrc
    else:
        return False, False, False, False



def get_lyrics(track_id):
    return requests.get(
        f"https://spotify-lyric-api.herokuapp.com/?trackid={track_id}", timeout=10
    ).json()

def get_reserve_lyrics(isrc):
    r = requests.get(
            f'https://beautiful-lyrics.socalifornian.live/lyrics/{isrc}', timeout=10
        )
    if(r.status_code != 200):
        return False
    try:
        rjson=r.json()
    except:
        return False
    html=BeautifulSoup(rjson["Content"],'html.parser')
    data={"error":False,"syncType":"LINE_SYNCED","lines":[]}
    lines=html.find_all("p")
    try:
        for l in lines:
            line=BeautifulSoup(str(l), 'html.parser')
            if line.p.has_attr('begin'):
                begin=timestamp_to_ms(line.p['begin'])
                end=timestamp_to_ms(line.p['end'])
                linedata={"startTimeMs":f"{begin}","words":f"{line.p.text}","syllables":[],"endTimeMs":f"{end}"}
                data["lines"].append(linedata)
    except:
        PrintException()
    if len(data['lines']) == 0:
        return False
    return data

def timestamp_to_ms(time):
    if ':' in time:
        time = time.split(':')
        if len(time) == 2:
            mins = int(time[0])
            seconds = mins*60+float(time[1])
            ms = round(seconds*1000)
        if len(time) == 3:
            hours = int(time[0])
            mins = int(time[1])
            seconds = hours*60*24+mins*60+float(time[2])
            ms = round(seconds*1000)
        return ms
    else:
        seconds = float(time)
        ms = round(seconds*1000)
def get_spotipy():
    print("SPOTIFY: RETRIVING/REFRESHING TOKEN")
    auth = SpotifyOAuth(SPOTIFY_ID, SPOTIFY_SECRET, SPOTIFY_REDIRECT, scope=SCOPE)
    if ".cache" in os.listdir("./"):
        TOKEN = auth.get_cached_token()["access_token"]
    else:
        TOKEN = auth.get_access_token(as_dict=False)
    sp = spotipy.Spotify(TOKEN)
    return sp, auth


if __name__ == "__main__":
    song_last_played = ""
    line_last_played = ""
    lyrics = {}
    rlyrics = {}
    main_loops = 0
    sp, auth = get_spotipy()
    while True:
        try:
            if (
                main_loops % (LYRIC_UPDATE_RATE_PER_SECOND * SECONDS_TO_SPOTIFY_RESYNC)
                == 0
            ):  # we don't need to poll Spotify for the song contantly, once every 10 sec should work.
                song, l, rl, isrc = on_new_song(sp, song_last_played)
                if song is False:
                    grequest_if_different(
                    CUSTOM_STATUS,
                    "SPOTIFY: NOTHING PLAYING",
                    )
                    last_played_line = "NO LYRICS"
                if l is not False:
                    lyrics=l
                if rl is not False:
                    rlyrics=rl
                if 'is_playing' in song.keys():
                    if song["is_playing"] is False:
                        song = None
                        grequest_if_different(
                        CUSTOM_STATUS,
                        "SPOTIFY: CURRENTLY PAUSED",
                        )
                        last_played_line = "NO LYRICS"
            song_last_played, last_played_line = main(
                isrc, line_last_played, song, lyrics, rlyrics
            )
            main_loops += 1
        except Exception as e:
            PrintException()
            print(e)
            sp, auth = get_spotipy()
            time.sleep(3)
