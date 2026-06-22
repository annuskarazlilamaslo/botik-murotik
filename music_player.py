
import random
from cloud_manager import get_cloud_tracks


class MusicPlayer:
    def __init__(self):
        self.playlist = []
        self.current_index = 0
        self.loop_mode = True
        self.shuffle_mode = True

    def load_playlist(self):
        """Запрашивает список файлов из Яндекс Диска и обновляет плейлист"""

        found_files = get_cloud_tracks()

        if found_files:
            self.playlist = found_files

            if self.shuffle_mode:
                random.shuffle(self.playlist)
            else:
                self.playlist.sort(key=lambda x: x["name"])

            print(f"✅ Плейлист обновлён ({len(self.playlist)} треков)")
        else:
            print("⚠ Использую предыдущий плейлист")
        return self.playlist
    
    def get_previous_index(self):
        """Высчитывает индекс предыдущего трека"""
        if not self.playlist:
            return 0
            
        new_index = self.current_index - 1
        
        if new_index < 0:
            new_index = len(self.playlist) - 1
            
        return new_index

    def toggle_loop(self):
        self.loop_mode = not self.loop_mode
        return self.loop_mode

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        self.current_index = 0
        self.load_playlist()
        return self.shuffle_mode