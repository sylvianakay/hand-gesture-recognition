#!/usr/bin/env python
# -*- coding: utf-8 -*-
import queue
import threading
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth


class SpotifyController:
    def __init__(self):
        scope = (
            "user-read-playback-state "
            "user-read-currently-playing "
            "user-modify-playback-state"
        )
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(scope=scope, open_browser=True)
        )
        self.volume = 0.7
        self._is_playing = False
        self._is_paused = True
        self._current_track_name = ""
        self._last_state_refresh = 0
        self._last_volume_update = 0
        self._last_sent_volume = None
        self._last_error = {}
        self._commands = queue.Queue()
        self._lock = threading.Lock()
        self._running = True

        self._refresh_state(force=True)
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    @property
    def is_playing(self):
        with self._lock:
            return self._is_playing

    @property
    def is_paused(self):
        with self._lock:
            return self._is_paused

    @property
    def current_track_name(self):
        with self._lock:
            return self._current_track_name

    def play(self):
        with self._lock:
            if self._is_playing:
                return
            self._is_playing = True
            self._is_paused = False
        self._enqueue("play")

    def pause(self):
        with self._lock:
            if self._is_paused:
                return
            self._is_playing = False
            self._is_paused = True
        self._enqueue("pause")

    def next_track(self):
        self._enqueue("next")

    def previous_track(self):
        self._enqueue("previous")

    def set_volume(self, volume):
        volume = max(0.0, min(1.0, volume))
        now = time.time()
        volume_percent = int(volume * 100)

        if self._last_sent_volume is not None:
            if abs(volume_percent - self._last_sent_volume) < 8:
                with self._lock:
                    self.volume = volume
                return

        if now - self._last_volume_update < 1.5:
            with self._lock:
                self.volume = volume
            return

        with self._lock:
            self.volume = volume
        self._last_sent_volume = volume_percent
        self._last_volume_update = now
        self._enqueue("volume", volume_percent)

    def stop(self):
        self._running = False

    def _enqueue(self, command, value=None):
        while self._commands.qsize() > 4:
            try:
                self._commands.get_nowait()
            except queue.Empty:
                break
        self._commands.put((command, value))

    def _run_worker(self):
        next_refresh = time.time() + 2.0
        while self._running:
            timeout = max(0.1, next_refresh - time.time())
            try:
                command, value = self._commands.get(timeout=timeout)
                self._execute_command(command, value)
            except queue.Empty:
                self._refresh_state(force=True)
                next_refresh = time.time() + 2.5

    def _execute_command(self, command, value):
        try:
            if command == "play":
                self.spotify.start_playback()
                print("Spotify resumed")
            elif command == "pause":
                self.spotify.pause_playback()
                print("Spotify paused")
            elif command == "next":
                self.spotify.next_track()
                time.sleep(0.15)
                self._refresh_state(force=True)
                print(f"Spotify next: {self.current_track_name}")
            elif command == "previous":
                self.spotify.previous_track()
                time.sleep(0.15)
                self._refresh_state(force=True)
                print(f"Spotify previous: {self.current_track_name}")
            elif command == "volume":
                self.spotify.volume(value)
        except spotipy.SpotifyException as error:
            self._print_spotify_error(command, error)

    def _refresh_state(self, force=False):
        now = time.time()
        if not force and now - self._last_state_refresh < 2.0:
            return

        self._last_state_refresh = now
        try:
            playback = self.spotify.current_playback()
        except spotipy.SpotifyException as error:
            self._print_spotify_error("read playback state", error)
            return

        if not playback:
            with self._lock:
                self._is_playing = False
                self._is_paused = True
                self._current_track_name = "No active Spotify device"
            return

        device = playback.get("device") or {}
        item = playback.get("item") or {}
        artists = ", ".join(artist["name"] for artist in item.get("artists", []))
        track = item.get("name", "")
        track_name = f"{artists} - {track}" if artists else track

        with self._lock:
            self._is_playing = bool(playback.get("is_playing"))
            self._is_paused = not self._is_playing
            self._current_track_name = track_name
            if device.get("volume_percent") is not None:
                self.volume = device["volume_percent"] / 100

    def _print_spotify_error(self, action, error):
        now = time.time()
        if now - self._last_error.get(action, 0) < 5.0:
            return

        self._last_error[action] = now
        print(f"Spotify could not {action}: {error.http_status} {error.msg}")
