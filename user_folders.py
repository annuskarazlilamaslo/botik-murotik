import json
import os

import config


def load_user_folders():
    """Загружает привязанные папки пользователей из файла JSON."""

    if os.path.exists(config.USER_FOLDERS_FILE):
        with open(config.USER_FOLDERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def save_user_folders(data):
    """
    Если файла нет, создаёт его.
    Сохраняет привязанные папки пользователей в JSON.
    """
    
    with open(config.USER_FOLDERS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_folder_name(discord_id):
    """Возвращает имя папки пользователя или None, если не задано"""

    folders = load_user_folders()
    return folders.get(str(discord_id))


def set_folder_name(discord_id, name):
    """
    Пытается назначить имя папки пользователю.
    Возвращает (успех: bool, сообщение: str).
    """

    folders = load_user_folders()
    user_id = str(discord_id)

    if user_id in folders:
        return False, f"У тебя уже есть папка `{folders[user_id]}`."

    if name in folders.values():
        return False, f"Имя `{name}` уже занято другим пользователем."

    folders[user_id] = name
    save_user_folders(folders)
    return True, f"Папка `{name}` назначена."


def admin_set_folder_name(discord_id, name):
    """
    Принудительно назначает/меняет имя папки пользователю (для админов).
    В отличие от set_folder_name, перезаписывает существующую привязку папки.
    Всё равно проверяет, что имя не занято другим пользователем.
    """

    folders = load_user_folders()
    user_id = str(discord_id)

    for uid, folder in folders.items():
        if folder == name and uid != user_id:
            return False, (
                f"Имя `{name}` уже занято "
                f"другим пользователем (ID: {uid})."
            )

    old_name = folders.get(user_id)
    folders[user_id] = name
    save_user_folders(folders)

    if old_name:
        return True, f"Папка изменена: `{old_name}` -> `{name}`"
    return True, f"Папка назначена: `{name}`"


def remove_folder_binding(discord_id):
    """Удаляет привязку папки пользователя (для админов)."""

    folders = load_user_folders()
    user_id = str(discord_id)

    if user_id not in folders:
        return False, "У этого пользователя нет привязанной папки."

    old_name = folders.pop(user_id)
    save_user_folders(folders)
    return True, f"Привязка папки удалена (была папка `{old_name}`)."


def get_all_folders():
    """Читает и возвращает весь список пользователей и их папок из файла."""

    return load_user_folders()
