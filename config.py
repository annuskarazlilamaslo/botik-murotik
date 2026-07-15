import os

from dotenv import load_dotenv

load_dotenv()

YANDEX_DISK_MUSIC_PATH = "disk:/music"
YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/resources"
YANDEX_DISK_API_DOMAIN = "cloud-api.yandex.net"
YANDEX_DISK_API_LIMIT = 200

USER_FOLDERS_FILE = "user_folders.json"
MAX_TRACKS_PER_USER = 50

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
YANDEX_MUSIC_PATH = os.getenv("YANDEX_MUSIC_PATH")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
MUSIC_DIR = os.getenv("MUSIC_DIR")

ADMIN_IDS = {
    int(id_str.strip())
    for id_str in os.getenv("ADMIN_IDS", "").split(",")
    if id_str.strip()
}

if os.name == "nt":
    FFMPEG_PATH = "./ffmpeg.exe"
else:
    FFMPEG_PATH = "ffmpeg"
