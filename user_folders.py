import json
import os

USER_FOLDERS_FILE = "user_folders.json"


def load_user_folders():
    if os.path.exists(USER_FOLDERS_FILE):
        with open(USER_FOLDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_user_folders(data):
    with open(USER_FOLDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_folder_name(discord_id):
    """Возвращает имя папки пользователя или None, если не задано"""

    folders = load_user_folders()
    return folders.get(str(discord_id))


def set_folder_name(discord_id, name: str) -> tuple[bool, str]:
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


def admin_set_folder_name(discord_id, name: str) -> tuple[bool, str]:
    """
    Принудительно назначает/меняет имя папки пользователю (для админов).
    В отличие от set_folder_name, перезаписывает существующую привязку.
    Всё равно проверяет, что имя не занято другим пользователем.
    """
    folders = load_user_folders()
    user_id = str(discord_id)

    for uid, folder in folders.items():
        if folder == name and uid != user_id:
            return False, f"Имя `{name}` уже занято другим пользователем (ID: {uid})."

    old_name = folders.get(user_id)
    folders[user_id] = name
    save_user_folders(folders)

    if old_name:
        return True, f"Папка изменена: `{old_name}` -> `{name}`"
    return True, f"Папка назначена: `{name}`"


def remove_folder_binding(discord_id) -> tuple[bool, str]:
    """Удаляет привязку пользователя (для админов)."""
    folders = load_user_folders()
    user_id = str(discord_id)

    if user_id not in folders:
        return False, "У этого пользователя нет привязанной папки."

    old_name = folders.pop(user_id)
    save_user_folders(folders)
    return True, f"Привязка удалена (была папка `{old_name}`)."


def get_all_folders() -> dict:
    """Возвращает все привязки (для команды списка)."""
    return load_user_folders()
