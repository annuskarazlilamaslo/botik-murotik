import os
import random
from config import MUSIC_DIR

class MusicPlayer:
    def __init__(self):
        self.playlist = []
        self.current_index = 0
        self.loop_mode = True
        self.shuffle_mode = True

    def load_playlist(self):
        """Сканирует локальную папку и обновляет текущий плейлист"""
        found_files = []
        if not os.path.exists(MUSIC_DIR):
            return []
            
        for root, dirs, files in os.walk(MUSIC_DIR):
            for file in files:
                if file.lower().endswith((".mp3", ".wav", ".ogg")):
                    relative_path = os.path.relpath(os.path.join(root, file), MUSIC_DIR)
                    found_files.append(relative_path)
                    
        self.playlist = found_files
        
        if self.shuffle_mode:
            random.shuffle(self.playlist)
        else:
            self.playlist.sort()
            
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