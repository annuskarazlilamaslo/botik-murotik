import requests
import config
import aiohttp


DISK_RESOURCES_URL = "https://cloud-api.yandex.net/v1/disk/resources"


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

        files = response.json().get("_embedded", {}).get("items", [])

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
                inner_files = inner_files = inner_response.json().get("_embedded", {}).get("items", [])
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

    return response.json().get("href")


async def ensure_user_folder(username):
    """Асинхронно проверяет и создает папку, выводя все ответы Яндекса"""

    folder_path = f"disk:/music/{username}"
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}

    print(f"\n--- [DEBUG] Проверяю папку {folder_path} ---")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params={"path": folder_path}, timeout=5) as check_resp:
            print(f"[DEBUG] Статус проверки папки: {check_resp.status}")
            if check_resp.status == 200:
                return folder_path

            check_text = await check_resp.text()
            print(f"[DEBUG] Ответ при проверке: {check_text}")

        print(f"[DEBUG] Пробую создать папку...")
        async with session.put(url, headers=headers, params={"path": folder_path}, timeout=5) as create_resp:
            create_text = await create_resp.text()
            print(f"[DEBUG] Статус создания: {create_resp.status}")
            print(f"[DEBUG] Ответ Яндекса при создании: {create_text}")

            if create_resp.status in (201, 409):
                return folder_path
            else:
                return "disk:/music"


async def upload_track_to_cloud(discord_file_url, filename, username):
    """Асинхронно загружает трек и выводит полную ошибку при сбое"""

    cloud_folder = await ensure_user_folder(username)
    cloud_file_path = f"{cloud_folder}/{filename}"

    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = {"path": cloud_file_path, "url": discord_file_url, "overwrite": "true"}

    print(f"\n--- [DEBUG] Отправка файла {filename} в {cloud_file_path} ---")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(upload_url, headers=headers, params=params, timeout=15) as response:
                print(f"[DEBUG] Статус загрузки: {response.status}")
                response_text = await response.text()
                print(f"[DEBUG] Ответ Яндекса при загрузке: {response_text}")

                if response.status in (200, 202):
                    return True, cloud_file_path
                else:
                    return False, f"Яндекс вернул код {response.status}: {response_text}"

    except Exception as e:
        print(f"[DEBUG] Критическая ошибка функции: {str(e)}")
        return False, str(e)
    
 
async def delete_from_cloud(path: str, permanently: bool = True) -> tuple[bool, str]:
    """
    Удаляет файл или папку (со всем содержимым) по указанному пути на Диске.
    permanently=True -> удаляет насовсем, минуя корзину.
    permanently=False -> отправляет в корзину (можно восстановить вручную).
    """
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = {"path": path, "permanently": str(permanently).lower()}
 
    async with aiohttp.ClientSession() as session:
        async with session.delete(DISK_RESOURCES_URL, headers=headers, params=params, timeout=10) as resp:
            text = await resp.text()
            print(f"[DEBUG] Удаление {path}: статус {resp.status}, ответ: {text}")
 
            if resp.status in (202, 204):
                return True, "Удалено"
            elif resp.status == 404:
                return False, "Не найдено на Диске"
            else:
                return False, f"Яндекс вернул код {resp.status}: {text}"
 
 
async def list_folder_contents(folder_path: str) -> tuple[bool, list]:
    """
    Возвращает список файлов в папке пользователя (для показа админу перед удалением).
    """
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = {"path": folder_path, "limit": 100}
 
    async with aiohttp.ClientSession() as session:
        async with session.get(DISK_RESOURCES_URL, headers=headers, params=params, timeout=10) as resp:
            if resp.status != 200:
                return False, []
 
            data = await resp.json()
            items = data.get("_embedded", {}).get("items", [])
            filenames = [item["name"] for item in items if item["type"] == "file"]
            return True, filenames