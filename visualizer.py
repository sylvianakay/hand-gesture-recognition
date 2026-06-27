#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import time

import cv2 as cv
import numpy as np


class TechnoVisualizer:
    def __init__(self, width=960, height=540, window_name="Techno Visuals"):
        self.width = width
        self.height = height
        self.window_name = window_name
        self.start_time = time.time()
        self.drop_started_at = -999.0
        self.drop_duration = 0.55
        self.pinch_closed = False

    def render(self, hand_sign="", finger_gesture="", landmarks=None,
               is_playing=False, volume=0.0, track_name=""):
        elapsed = time.time() - self.start_time
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        pulse = self._pulse(elapsed, is_playing)
        pinch = self._pinch_amount(landmarks)
        self._update_drop_trigger(pinch, elapsed)
        drop = self._drop_strength(elapsed)
        hand_position = self._hand_position(landmarks)
        self._draw_white_contours(frame, elapsed, pulse, volume, pinch,
                                  hand_position, drop)
        self._draw_drop_flash(frame, elapsed, hand_position, drop)
        self._draw_hand_reactor(frame, hand_position, pulse, pinch, drop)
        self._draw_status(frame, hand_sign, finger_gesture, is_playing, volume,
                          track_name, pinch)

        cv.imshow(self.window_name, frame)

    def _pulse(self, elapsed, is_playing):
        speed = 5.0 if is_playing else 1.5
        base = (math.sin(elapsed * speed) + 1.0) / 2.0
        return 0.25 + base * (0.75 if is_playing else 0.25)

    def _update_drop_trigger(self, pinch, elapsed):
        if pinch > 0.72 and not self.pinch_closed:
            self.drop_started_at = elapsed
            self.pinch_closed = True
            print("Drop flash")
        elif pinch < 0.45:
            self.pinch_closed = False

    def _drop_strength(self, elapsed):
        age = elapsed - self.drop_started_at
        if age < 0 or age > self.drop_duration:
            return 0.0

        return (1.0 - age / self.drop_duration) ** 2

    def _pinch_amount(self, landmarks):
        if not landmarks or len(landmarks) <= 8:
            return 0.0

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        wrist = landmarks[0]
        middle_base = landmarks[9]

        pinch_distance = math.dist(thumb_tip, index_tip)
        hand_scale = max(math.dist(wrist, middle_base), 1.0)
        normalized_distance = pinch_distance / hand_scale

        # 1.0 means thumb and index are close together, 0.0 means open.
        return max(0.0, min(1.0, 1.0 - normalized_distance / 1.15))

    def _hand_position(self, landmarks):
        if not landmarks:
            return None

        index_tip = landmarks[8]
        return index_tip[0], index_tip[1]

    def _draw_white_contours(self, frame, elapsed, pulse, volume, pinch,
                             hand_position, drop):
        line_count = 54
        point_count = 170
        spacing = self.width / (line_count + 1)
        hand_x = self.width * 0.5
        hand_y = self.height * 0.5
        if hand_position is not None:
            hand_x, hand_y = hand_position

        has_hand = hand_position is not None
        motion = 0.35 + volume * 0.9
        bend_strength = (10 + pinch * 65) if has_hand else 0
        hand_pull = 260 + pinch * 360
        field_width = 0.18 + pinch * 0.12

        for line_index in range(line_count):
            base_x = spacing * (line_index + 1)
            points = []

            for point_index in range(point_count):
                y = (point_index / (point_count - 1)) * self.height
                wave_a = 0
                wave_b = 0
                if has_hand:
                    wave_a = math.sin(y * 0.018 + elapsed * motion +
                                      line_index * 0.22)
                    wave_b = math.sin(y * 0.041 - elapsed * 0.45 +
                                      line_index * 0.17)

                distance_x = (base_x - hand_x) / max(self.width, 1)
                distance_y = (y - hand_y) / max(self.height, 1)
                influence = math.exp(-((distance_x / field_width) ** 2 +
                                       (distance_y / 0.34) ** 2))
                pull_to_hand = (hand_x - base_x) / max(self.width, 1)
                vertical_ripple = math.sin(distance_y * math.pi * 6 -
                                           elapsed * 2.6)
                pressure_wave = math.sin((distance_x + distance_y) * math.pi * 9 +
                                         elapsed * 3.2)

                hand_bend = 0
                if has_hand:
                    attraction = pull_to_hand * hand_pull * 2.4
                    ripple = (vertical_ripple * 35 + pressure_wave * 20) * (
                        0.25 + pinch)
                    hand_bend = influence * (attraction + ripple)

                x = (base_x + wave_a * bend_strength +
                     wave_b * bend_strength * 0.45 + hand_bend)
                points.append((int(x), int(y)))

            brightness = min(255, 92 + int(pulse * 42) + int(pinch * 85) +
                             int(drop * 120))
            if drop > 0:
                color = self._drop_line_color(line_index, drop, brightness)
            else:
                color = (brightness, brightness, brightness)
            cv.polylines(frame, [np.array(points, dtype=np.int32)], False,
                         color, 1, cv.LINE_AA)

    def _drop_line_color(self, line_index, drop, brightness):
        phase = line_index * 0.45
        blue = min(255, int(brightness + 80 * drop))
        green = min(255, int(80 * drop + 70 * (math.sin(phase) + 1)))
        red = min(255, int(180 * drop + 75 * (math.sin(phase + 2.1) + 1)))
        return blue, green, red

    def _draw_drop_flash(self, frame, elapsed, hand_position, drop):
        if drop <= 0:
            return

        overlay = np.zeros_like(frame)
        center = (self.width // 2, self.height // 2)
        if hand_position is not None:
            center = (int(hand_position[0]), int(hand_position[1]))

        radius = int(35 + drop * 360)
        colors = [(255, 80, 80), (120, 255, 255), (255, 80, 220),
                  (80, 255, 120)]
        for index, color in enumerate(colors):
            angle = elapsed * 9 + index * math.tau / len(colors)
            end_x = int(center[0] + math.cos(angle) * self.width)
            end_y = int(center[1] + math.sin(angle) * self.height)
            cv.line(overlay, center, (end_x, end_y), color, 2, cv.LINE_AA)

        cv.circle(overlay, center, radius, (255, 255, 255), 2, cv.LINE_AA)
        cv.circle(overlay, center, max(2, radius // 3), (255, 80, 220), 1,
                  cv.LINE_AA)

        alpha = min(0.85, 0.22 + drop * 0.55)
        cv.addWeighted(overlay, alpha, frame, 1.0, 0, frame)

    def _draw_hand_reactor(self, frame, hand_position, pulse, pinch, drop):
        if hand_position is None:
            return

        x, y = int(hand_position[0]), int(hand_position[1])
        radius = int(6 + pulse * 5 + pinch * 10)
        color = (255, 255, 255) if drop <= 0 else (255, 100, 255)
        cv.circle(frame, (x, y), radius + int(drop * 24), color, 1, cv.LINE_AA)

    def _draw_status(self, frame, hand_sign, finger_gesture, is_playing, volume,
                     track_name, pinch):
        status = "PLAYING" if is_playing else "PAUSED"
        cv.putText(frame, status, (24, 36), cv.FONT_HERSHEY_SIMPLEX, 0.8,
                   (255, 255, 255), 1, cv.LINE_AA)
        cv.putText(frame, f"HAND: {hand_sign or '-'}", (24, 70),
                   cv.FONT_HERSHEY_SIMPLEX, 0.55, (255, 160, 40), 1,
                   cv.LINE_AA)
        cv.putText(frame, f"MOVE: {finger_gesture or '-'}", (24, 98),
                   cv.FONT_HERSHEY_SIMPLEX, 0.55, (180, 110, 255), 1,
                   cv.LINE_AA)
        cv.putText(frame, f"VOL: {int(volume * 100)}%", (24, 126),
                   cv.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1,
                   cv.LINE_AA)
        cv.putText(frame, f"TRACK: {self._shorten(track_name or '-')}",
                   (24, 148), cv.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 210),
                   1, cv.LINE_AA)
        cv.putText(frame, f"PINCH: {int(pinch * 100)}%", (24, 170),
                   cv.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 255), 1,
                   cv.LINE_AA)

    def _shorten(self, text, max_length=56):
        if len(text) <= max_length:
            return text

        return text[:max_length - 3] + "..."
