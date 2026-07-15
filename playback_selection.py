"""
Этот модуль помогает админу временно фильтровать
музыку из папок конкретных пользователей.
Выбор сбрасывается на 'играть всё' при каждом перезапуске бота.
"""

_selected_folders = None


def select_folders(folder_names):
    """Устанавливает список папок, треки из которых будут в плейлисте."""

    global _selected_folders
    _selected_folders = set(folder_names)


def select_all_folders():
    """Сбрасывает выбор - снова играют все папки."""

    global _selected_folders
    _selected_folders = None


def get_selected_folders():
    """Возвращает текущий выбор (None значит 'все папки')."""

    return _selected_folders


def is_folder_active(folder_name):
    """Проверяет, должна ли эта папка участвовать в текущем плейлисте."""

    if _selected_folders is None:
        return True
    return folder_name in _selected_folders
