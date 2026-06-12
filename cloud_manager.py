import os
import gdown
from config import GOOGLE_DRIVE_FOLDER_ID, MUSIC_DIR

def sync_music_from_cloud():
    """Скачивает новые треки из Google Диска. Работает автономно."""
    print("⏳ [Cloud] Проверка обновлений в облаке Google Drive...")

    if not os.path.exists(MUSIC_DIR):
        os.makedirs(MUSIC_DIR)

    url = f'https://google.com{GOOGLE_DRIVE_FOLDER_ID}'

    gdown.download_folder(url, output=MUSIC_DIR, quiet=True, use_cookies=False)
    print("✅ [Cloud] Синхронизация завершена успешно!")