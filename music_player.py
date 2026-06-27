#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

import pygame


class MusicPlayer:
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg"}

    def __init__(self, tracks_dir="tracks", volume=0.7):
        self.tracks_dir = Path(tracks_dir)
        self.tracks_dir.mkdir(exist_ok=True)
        self.tracks = self._load_tracks()
        self.current_track_index = 0
        self.volume = volume
        self.is_paused = False
        self.is_playing = False
        self.has_warned_no_tracks = False

        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)

    def _load_tracks(self):
        if not self.tracks_dir.exists():
            return []

        return sorted(
            path for path in self.tracks_dir.iterdir()
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def refresh_tracks(self):
        self.tracks = self._load_tracks()
        if self.current_track_index >= len(self.tracks):
            self.current_track_index = 0
        if self.tracks:
            self.has_warned_no_tracks = False

    def _has_tracks(self):
        self.refresh_tracks()
        if self.tracks:
            return True

        if not self.has_warned_no_tracks:
            print("No tracks found. Add .mp3, .wav, or .ogg files to tracks/.")
            self.has_warned_no_tracks = True
        return False

    def _play_current_track(self):
        current_track = self.tracks[self.current_track_index]
        pygame.mixer.music.load(str(current_track))
        pygame.mixer.music.play()
        self.is_playing = True
        self.is_paused = False
        print(f"Playing: {current_track.name}")

    def play(self):
        if not self._has_tracks():
            return

        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            print("Music resumed")
            return

        if self.is_playing:
            return

        self._play_current_track()

    def pause(self):
        if not self.is_playing or self.is_paused:
            return

        pygame.mixer.music.pause()
        self.is_paused = True
        print("Music paused")

    def next_track(self):
        if not self._has_tracks():
            return

        self.current_track_index = (self.current_track_index + 1) % len(self.tracks)
        self._play_current_track()

    def previous_track(self):
        if not self._has_tracks():
            return

        self.current_track_index = (self.current_track_index - 1) % len(self.tracks)
        self._play_current_track()

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)

    def change_volume(self, amount):
        self.set_volume(self.volume + amount)
        print(f"Volume: {int(self.volume * 100)}%")

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
