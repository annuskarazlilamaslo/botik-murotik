from http import HTTPStatus

import aiohttp

import config
from playback_selection import is_folder_active


async def get_cloud_tracks():
    """Получает список треков из папки music"""

    print("⏳ [Cloud] Проверка актуального списка треков...")

    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    playlist = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                config.YANDEX_DISK_API_URL,
                headers=headers,
                params={
                    "path": config.YANDEX_DISK_MUSIC_PATH,
                    "limit": config.YANDEX_DISK_API_LIMIT
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                files = data.get("_embedded", {}).get("items", [])

            for file in files:
                if file.get("type") != "dir":
                    continue

                user_folder = file["path"]
                user_name = file["name"]

                if not is_folder_active(user_name):
                    continue

                async with session.get(
                    config.YANDEX_DISK_API_URL,
                    headers=headers,
                    params={
                        "path": user_folder,
                        "limit": config.YANDEX_DISK_API_LIMIT
                    },
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as inner_response:
                    if inner_response.status == HTTPStatus.OK:
                        inner_data = await inner_response.json()
                        inner_files = (
                            inner_data.get("_embedded", {}).get("items", [])
                        )
                        for inner_file in inner_files:
                            if (
                                inner_file.get("type") == "file"
                                and inner_file.get("media_type") == "audio"
                            ):
                                playlist.append(
                                    {
                                        "name": inner_file["name"],
                                        "path": inner_file["path"],
                                        "user": user_name,
                                    }
                                )
                    else:
                        print(
                            f"⚠ [Cloud] Не удалось получить "
                            f"содержимое папки {user_folder}: "
                            f"статус {inner_response.status}, треки пропущены"
                        )

        print(f"✅ [Cloud] Найдено треков: {len(playlist)}")

        return playlist

    except Exception as e:
        print(f"❌ [Cloud] Ошибка: {e}")
        return None


async def get_download_url(disk_path):
    """Получает временную ссылку для стриминга"""

    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{config.YANDEX_DISK_API_URL}/download",
            headers=headers,
            params={"path": disk_path},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("href")


async def ensure_user_folder(username):
    """Проверяет и создает папку, выводя все ответы Яндекса"""

    folder_path = f"{config.YANDEX_DISK_MUSIC_PATH}/{username}"
    url = config.YANDEX_DISK_API_URL
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}

    print(f"\n--- [DEBUG] Проверяю папку {folder_path} ---")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, headers=headers, params={"path": folder_path}, timeout=5
        ) as check_resp:
            print(f"[DEBUG] Статус проверки папки: {check_resp.status}")
            if check_resp.status == HTTPStatus.OK:
                return folder_path

            check_text = await check_resp.text()
            print(f"[DEBUG] Ответ при проверке: {check_text}")

        print(f"[DEBUG] Пробую создать папку...")

        async with session.put(
            url, headers=headers, params={"path": folder_path}, timeout=5
        ) as create_response:
            create_text = await create_response.text()

            print(f"[DEBUG] Статус создания: {create_response.status}")
            print(f"[DEBUG] Ответ Яндекса при создании: {create_text}")

            if create_response.status in (
                HTTPStatus.CREATED, HTTPStatus.CONFLICT
            ):
                return folder_path
            else:
                return config.YANDEX_DISK_MUSIC_PATH


async def upload_track_to_cloud(discord_file_url, filename, username):
    """Загружает трек и выводит полную ошибку при сбое"""

    cloud_folder = await ensure_user_folder(username)
    cloud_file_path = f"{cloud_folder}/{filename}"

    upload_url = f"{config.YANDEX_DISK_API_URL}/upload"
    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = (
        {"path": cloud_file_path, "url": discord_file_url, "overwrite": "true"}
    )

    print(f"\n--- [DEBUG] Отправка файла {filename} в {cloud_file_path} ---")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                upload_url, headers=headers, params=params, timeout=15
            ) as response:
                print(f"[DEBUG] Статус загрузки: {response.status}")
                response_text = await response.text()
                print(f"[DEBUG] Ответ Яндекса при загрузке: {response_text}")

                if response.status in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
                    return True, cloud_file_path
                else:
                    return (
                        False,
                        f"Яндекс вернул код {response.status}: {response_text}",
                    )

    except Exception as e:
        print(f"[DEBUG] Критическая ошибка функции: {str(e)}")
        return False, str(e)


async def delete_from_cloud(path, permanently=True):
    """
    Удаляет файл или папку (со всем содержимым) по указанному пути на Диске.
    permanently=True -> удаляет насовсем, минуя корзину.
    permanently=False -> отправляет в корзину (можно восстановить вручную).
    """

    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = {"path": path, "permanently": str(permanently).lower()}

    async with aiohttp.ClientSession() as session:
        async with session.delete(
            config.YANDEX_DISK_API_URL,
            headers=headers,
            params=params,
            timeout=10
        ) as response:
            text = await response.text()

            print(
                f"[DEBUG] Удаление {path}:"
                f" статус {response.status}, ответ: {text}"
            )

            if response.status in (HTTPStatus.ACCEPTED, HTTPStatus.NO_CONTENT):
                return True, "Удалено"
            elif response.status == HTTPStatus.NOT_FOUND:
                return False, "Не найдено на Диске"
            else:
                return False, f"Яндекс вернул код {response.status}: {text}"


async def list_folder_contents(folder_path):
    """
    Возвращает список файлов в папке пользователя
    (для показа админу перед удалением).
    """

    headers = {"Authorization": f"OAuth {config.YANDEX_DISK_TOKEN}"}
    params = {"path": folder_path, "limit": config.YANDEX_DISK_API_LIMIT}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            config.YANDEX_DISK_API_URL,
            headers=headers,
            params=params,
            timeout=10
        ) as response:
            if response.status != HTTPStatus.OK:
                return False, []

            data = await response.json()
            items = data.get("_embedded", {}).get("items", [])
            filenames = (
                [item["name"] for item in items if item["type"] == "file"]
            )
            return True, filenames
