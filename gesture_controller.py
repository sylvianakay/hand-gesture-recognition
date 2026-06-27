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

        can_swipe_tracks = self._is_pointing_hand(landmarks)
        swipe_direction = None
        if can_swipe_tracks:
            swipe_direction = self._detect_swipe(image_width, image_height)

        if swipe_direction == "right" and self._can_run("next"):
            self.music_player.next_track()
            self._clear_swipe_history(point_history)
            print("Swipe right: next track")
            return

        if swipe_direction == "left" and self._can_run("previous"):
            self.music_player.previous_track()
            self._clear_swipe_history(point_history)
            print("Swipe left: previous track")
            return

        is_swiping = can_swipe_tracks and self._is_horizontal_motion(image_width)
        if not is_swiping and hand_sign == "Open" and self._can_run("play"):
            self.music_player.play()
        elif not is_swiping and hand_sign == "Close" and self._can_run("pause"):
            self.music_player.pause()

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

    def _detect_swipe(self, image_width, image_height):
        valid_points = [
            point for point in self.index_tip_history
            if point[0] != 0 or point[1] != 0
        ]
        if len(valid_points) < 6:
            return None

        recent_points = valid_points[-6:]
        start_x, start_y = recent_points[0]
        end_x, end_y = recent_points[-1]
        dx = end_x - start_x
        dy = end_y - start_y

        swipe_threshold = image_width * 0.08
        vertical_limit = image_height * 0.40

        if abs(dx) < swipe_threshold or abs(dy) > vertical_limit:
            return None

        return "right" if dx > 0 else "left"

    def _is_pointing_hand(self, landmarks):
        if len(landmarks) <= 20:
            return False

        index_extended = landmarks[8][1] < landmarks[6][1]
        middle_folded = landmarks[12][1] > landmarks[10][1]
        ring_folded = landmarks[16][1] > landmarks[14][1]
        pinky_folded = landmarks[20][1] > landmarks[18][1]
        return index_extended and middle_folded and ring_folded and pinky_folded

    def _is_horizontal_motion(self, image_width):
        if len(self.index_tip_history) < 4:
            return False

        recent_points = list(self.index_tip_history)[-4:]
        dx = recent_points[-1][0] - recent_points[0][0]
        return abs(dx) > image_width * 0.035
