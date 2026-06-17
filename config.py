import os
from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
YANDEX_MUSIC_PATH = os.getenv("YANDEX_MUSIC_PATH")
FFMPEG_PATH = os.getenv("FFMPEG_PATH")
MUSIC_DIR = os.getenv("MUSIC_DIR")