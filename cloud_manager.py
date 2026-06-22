import requests
import config


def get_cloud_tracks():
    """Получает список треков из папки music"""
    print("⏳ [Cloud] Проверка актуального списка треков...")
    
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    playlist = []
    
    try:
        response = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources",
            headers=headers,
            params={"path": "disk:/music"},
            timeout=10
        )
        
        response.raise_for_status()

        files = response.json()["_embedded"]["items"]

        for file in files:
            if file.get("type") != "dir":
                continue
            
            user_folder = file["path"]
            user_name = file["name"]
            
            inner_response = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources",
                headers=headers,
                params={"path": user_folder},
                timeout=10
            )
            if inner_response.status_code == 200:
                inner_files = inner_response.json()["_embedded"]["items"]
                for inner_file in inner_files:
                    if inner_file.get("type") == "file" and inner_file.get("media_type") == "audio":
                        playlist.append({
                            "name": inner_file["name"],
                            "path": inner_file["path"],
                            "user": user_name
                        })

        print(f"✅ [Cloud] Найдено треков: {len(playlist)}")

        return playlist

    except Exception as e:
        print(f"❌ [Cloud] Ошибка: {e}")
        return None
                

def get_download_url(disk_path):
    """Получает временную ссылку для стриминга"""

    headers = {
        "Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"
    }

    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/download",
        headers=headers,
        params={"path": disk_path},
        timeout=10,
    )

    response.raise_for_status()

    return response.json()["href"]


def ensure_user_folder(username):
    """Проверяет наличие папки пользователя на Диске. Если её нет — создаёт."""
    
    folder_path = f"{config.YANDEX_MUSIC_PATH}/{username}"
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    
    response = requests.get(url, headers=headers, params={"path": folder_path}, timeout=5)
    if response.status_code == 404:
        print(f"📁 [Cloud] Создаю новую личную папку для: {username}")
        requests.put(url, headers=headers, params={"path": folder_path}, timeout=5)
    
    return folder_path


def upload_track_to_cloud(discord_file_url, filename, username):
    """Скачивает файл из Discord и загружает его в личную папку на Яндекс Диск"""
    
    cloud_folder = ensure_user_folder(username)
    cloud_file_path = f"{cloud_folder}/{filename}"
    
    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    
    try:
        res = requests.get(upload_url, headers=headers, params={"path": cloud_file_path, "overwrite": "true"}, timeout=5)
        if res.status_code != 200:
            return False, f"Яндекс Диск отказал в загрузке (Код {res.status_code})"
            
        href = res.json().get("href")
        
        discord_res = requests.get(discord_file_url, stream=True, timeout=30)
        if discord_res.status_code == 200:
            put_res = requests.put(href, data=discord_res.raw, timeout=60)
            if put_res.status_code in [200, 201]:
                return True, cloud_file_path
                
        return False, "Не удалось передать файл в облако."
    except Exception as e:
        print(f"❌ [Cloud] Ошибка при загрузке файла: {e}")
        return False, str(e)