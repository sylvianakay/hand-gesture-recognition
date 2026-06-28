#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from collections import deque


class GestureController:
    def __init__(self, music_player, action_cooldown=1.0):
        self.music_player = music_player
        self.action_cooldown = action_cooldown
        self.last_action = {}
        self.index_tip_history = deque(maxlen=10)

    def handle(self, hand_sign, finger_gesture, landmarks, image_width,
               image_height, point_history=None):
        if len(landmarks) > 8:
            self.index_tip_history.append(landmarks[8])

        if hand_sign == "Close":
            if self._can_run("pause"):
                self.music_player.pause()
            return

        if hand_sign == "Open" and self._can_run("play"):
            self.music_player.play()

        if hand_sign == "Pointer":
            if finger_gesture == "Clockwise" and self._can_run("next"):
                self.music_player.next_track()
            elif (finger_gesture == "Counter Clockwise"
                  and self._can_run("previous")):
                self.music_player.previous_track()

        if landmarks:
            wrist_y = landmarks[0][1]
            volume = 1.0 - (wrist_y / image_height)
            self.music_player.set_volume(volume)

    def reset_tracking(self):
        self.index_tip_history.clear()

    def _can_run(self, action):
        now = time.time()
        if now - self.last_action.get(action, 0) < self.action_cooldown:
            return False

        self.last_action[action] = now
        return True

    def _clear_swipe_history(self, point_history):
        self.index_tip_history.clear()
        if point_history is not None:
            point_history.clear()

    def _is_pointing_hand(self, landmarks):
        if len(landmarks) <= 20:
            return False

        index_extended = landmarks[8][1] < landmarks[6][1]
        middle_folded = landmarks[12][1] > landmarks[10][1]
        ring_folded = landmarks[16][1] > landmarks[14][1]
        pinky_folded = landmarks[20][1] > landmarks[18][1]
        return index_extended and middle_folded and ring_folded and pinky_folded

