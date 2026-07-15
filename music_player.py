import random

from cloud_manager import get_cloud_tracks


class MusicPlayer:
    """Класс для управления плейлистом и режимами воспроизведения"""

    def __init__(self):
        self.playlist = []
        self.current_index = 0
        self.loop_mode = True
        self.shuffle_mode = True

    def _apply_order(self):
        """
        Применяет текущий режим (шаффл или сортировка)
        к уже загруженному плейлисту"""

        if self.shuffle_mode:
            random.shuffle(self.playlist)
        else:
            self.playlist.sort(key=lambda x: x["name"])

    async def load_playlist(self):
        """Запрашивает список файлов из Яндекс Диска и обновляет плейлист"""

        found_files = await get_cloud_tracks()

        if found_files is not None:
            self.playlist = found_files

            self._apply_order()

            print(f"✅ Плейлист обновлён ({len(self.playlist)} треков)")
        else:
            if self.playlist:
                print(
                    "⚠ Не удалось обновить список."
                    " Оставляю текущие треки в памяти"
                )
            else:
                print("❌ Не удалось загрузить плейлист: облако недоступно")

        return self.playlist

    def toggle_loop(self):
        """Переключает режим цикличности воспроизведения"""

        self.loop_mode = not self.loop_mode
        return self.loop_mode

    async def toggle_shuffle(self):
        """Переключает режим случайного воспроизведения"""

        self.shuffle_mode = not self.shuffle_mode
        self.current_index = 0
        self._apply_order()
        return self.shuffle_mode
