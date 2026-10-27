"""Procedural sound effects: every sound is synthesized at startup, no files needed.

To use real sounds instead, drop assets/sfx/<name>.ogg or .wav (see assets/sfx/README.txt);
a file overrides the generated sound of the same name. With no audio device the game
simply runs silent.
"""
from __future__ import annotations

import array
import math
import os
import random
import time
from typing import Callable

import pygame

SAMPLE_RATE = 22050
SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sfx")
PITCH_VARIANTS = (1.0, 0.92, 1.12)  # repeating sounds get slight pitch changes, like BTD6 pops
Samples = list[float]


# ------------------------------------------------------------------ synthesis
def tone(f0: float, f1: float | None = None, dur: float = 0.15, wave: str = "sine",
         vol: float = 0.6, decay: float = 2.5, noise: float = 0.0, tremolo: float = 0.0) -> Samples:
    """One note sweeping f0 -> f1 with a decaying envelope."""
    f1 = f0 if f1 is None else f1
    n = int(SAMPLE_RATE * dur)
    out: Samples = []
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += 2 * math.pi * (f0 + (f1 - f0) * t) / SAMPLE_RATE
        if wave == "sine":
            s = math.sin(phase)
        elif wave == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == "saw":
            s = (phase / math.pi) % 2 - 1
        else:  # triangle
            s = abs((phase / math.pi) % 2 - 1) * 2 - 1
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        env = (1 - t) ** decay * min(1.0, i / (SAMPLE_RATE * 0.004))
        if tremolo:
            env *= 0.6 + 0.4 * math.sin(2 * math.pi * tremolo * i / SAMPLE_RATE)
        out.append(s * env * vol)
    return out


def noise_burst(dur: float, vol: float = 0.4, decay: float = 2.5, smooth: float = 0.0) -> Samples:
    """White noise; `smooth` (0..0.95) low-passes it into a softer whoosh/thud."""
    n = int(SAMPLE_RATE * dur)
    out: Samples = []
    y = 0.0
    for i in range(n):
        x = random.uniform(-1, 1)
        y = y * smooth + x * (1 - smooth)
        out.append(y * vol * (1 - i / n) ** decay)
    return out


def silence(dur: float) -> Samples:
    return [0.0] * int(SAMPLE_RATE * dur)


def seq(*parts: Samples) -> Samples:
    return [s for p in parts for s in p]


def mix(*parts: Samples) -> Samples:
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


# name -> (builder(pitch), variants, min seconds between plays, volume)
def _arp(notes, wave="square", dur=0.07, last=0.2, vol=0.3) -> Samples:
    parts = [tone(f, f, dur, wave, vol, 1.2) for f in notes[:-1]]
    return seq(*parts, tone(notes[-1], notes[-1], last, wave, vol, 2.0))


SOUNDS: dict[str, tuple[Callable[[float], Samples], int, float, float]] = {
    "shoot_jalu": (lambda p: mix(tone(900 * p, 350 * p, 0.09, "square", 0.25, 3), noise_burst(0.05, 0.12, 3, 0.3)), 3, 0.04, 0.5),
    "shoot_romli": (lambda p: seq(tone(1400 * p, 1400 * p, 0.03, "square", 0.2, 1), tone(1000 * p, 1000 * p, 0.05, "square", 0.2, 2)), 3, 0.05, 0.5),
    "shoot_zizi": (lambda p: mix(tone(660 * p, 660 * p, 0.35, "sine", 0.35, 3), tone(990 * p, 990 * p, 0.3, "sine", 0.2, 3)), 3, 0.08, 0.5),
    "hit": (lambda p: mix(noise_burst(0.05, 0.35, 3, 0.4), tone(220 * p, 120 * p, 0.06, "sine", 0.5, 3)), 3, 0.05, 0.5),
    "pop": (lambda p: mix(tone(350 * p, 900 * p, 0.1, "sine", 0.6, 2.2), noise_burst(0.03, 0.15, 3)), 3, 0.035, 0.7),
    "coin": (lambda p: seq(tone(1300, 1300, 0.05, "square", 0.18, 1.5), tone(1750, 1750, 0.09, "square", 0.18, 2)), 1, 0.09, 0.5),
    "place": (lambda p: mix(tone(180, 70, 0.14, "sine", 0.7, 2.5), noise_burst(0.04, 0.3, 3, 0.3)), 1, 0.05, 0.8),
    "upgrade": (lambda p: _arp([523, 659, 784, 1047]), 1, 0.1, 0.7),
    "sell": (lambda p: seq(tone(880, 880, 0.07, "square", 0.25, 1), tone(660, 660, 0.07, "square", 0.25, 1), tone(440, 440, 0.12, "square", 0.25, 2)), 1, 0.1, 0.6),
    "error": (lambda p: tone(140, 110, 0.18, "saw", 0.4, 1.2), 1, 0.15, 0.6),
    "click": (lambda p: tone(1200, 900, 0.025, "square", 0.2, 2), 1, 0.03, 0.5),
    "wave_start": (lambda p: seq(tone(220, 220, 0.2, "saw", 0.3, 0.8), tone(330, 330, 0.45, "saw", 0.3, 1.0)), 1, 0.5, 0.7),
    "wave_clear": (lambda p: _arp([523, 659, 784, 1047, 1319], "sine", 0.09, 0.3, 0.35), 1, 0.5, 0.7),
    "boss": (lambda p: mix(tone(70, 45, 0.9, "saw", 0.5, 1.0, tremolo=14), noise_burst(0.9, 0.15, 1.5, 0.1)), 1, 1.0, 0.9),
    "boss_die": (lambda p: mix(noise_burst(0.8, 0.7, 1.8, 0.12), tone(120, 30, 0.8, "sine", 0.6, 1.5)), 1, 0.5, 1.0),
    "thunder": (lambda p: mix(noise_burst(0.5, 0.9, 1.6, 0.6), tone(90, 30, 0.5, "sine", 0.9, 1.5), tone(1800, 200, 0.12, "saw", 0.4, 3)), 1, 0.1, 1.0),
    "loom": (lambda p: seq(tone(300, 900, 0.18, "sine", 0.4, 1.2), tone(900, 200, 0.3, "triangle", 0.4, 2, tremolo=14)), 1, 0.1, 0.8),
    "nap": (lambda p: mix(tone(330, 160, 0.6, "sine", 0.5, 1.2, tremolo=5), tone(165, 80, 0.6, "triangle", 0.4, 1.5)), 1, 0.1, 0.8),
    "graph_fire": (lambda p: mix(tone(300, 1400, 0.22, "saw", 0.3, 1.8), tone(600, 1800, 0.2, "sine", 0.3, 1.5)), 1, 0.05, 0.8),
    "shape_sq": (lambda p: tone(210 * p, 150 * p, 0.09, "square", 0.4, 3), 3, 0.05, 0.7),
    "shape_tri": (lambda p: tone(700 * p, 1100 * p, 0.08, "saw", 0.3, 3), 3, 0.05, 0.7),
    "shape_circ": (lambda p: tone(520 * p, 340 * p, 0.13, "sine", 0.5, 2.5), 3, 0.05, 0.7),
    "collide_wind": (lambda p: tone(180, 1400, 0.11, "sine", 0.4, 1.0), 1, 0.05, 0.8),
    "collide": (lambda p: mix(tone(150, 38, 0.34, "sine", 0.9, 2.2), noise_burst(0.22, 0.6, 2.0, 0.7), tone(392, 392, 0.16, "square", 0.2, 3), tone(494, 494, 0.16, "triangle", 0.25, 3), tone(587, 587, 0.16, "sine", 0.3, 3)), 1, 0.08, 1.0),
    "cube": (lambda p: mix(noise_burst(0.1, 0.6, 1.5, 0.8), tone(95, 55, 0.16, "sine", 0.7, 2), tone(1800, 1800, 0.02, "square", 0.15, 1)), 1, 0.1, 0.9),
    "pyramid": (lambda p: seq(tone(262, 262, 0.07, "triangle", 0.4, 2), tone(330, 330, 0.07, "triangle", 0.4, 2), tone(392, 392, 0.07, "triangle", 0.4, 2), tone(523, 523, 0.3, "triangle", 0.4, 1.5, tremolo=12)), 1, 0.1, 0.8),
    "sphere": (lambda p: mix(tone(300, 900, 0.2, "sine", 0.4, 1.5), tone(440, 440, 0.5, "sine", 0.25, 1.2), tone(443, 443, 0.5, "sine", 0.25, 1.2)), 1, 0.1, 0.8),
    "crack": (lambda p: mix(noise_burst(0.22, 0.6, 2.2, 0.35), tone(160, 70, 0.2, "saw", 0.4, 2.5)), 1, 0.05, 0.9),
    "leak": (lambda p: mix(tone(420, 140, 0.3, "saw", 0.4, 1.5), noise_burst(0.2, 0.2, 2, 0.2)), 1, 0.12, 0.8),
    "zap": (lambda p: mix(noise_burst(0.12, 0.3, 2.5, 0.7), tone(1800, 300, 0.12, "square", 0.25, 2.5)), 1, 0.08, 0.6),
    "whoosh": (lambda p: noise_burst(0.25, 0.5, 1.2, 0.85), 1, 0.1, 0.6),
    "sleep": (lambda p: seq(tone(500, 450, 0.12, "sine", 0.3, 2), tone(400, 350, 0.18, "sine", 0.3, 2)), 1, 0.15, 0.5),
    "knowledge": (lambda p: tone(1500, 1500, 0.04, "sine", 0.18, 2), 1, 0.25, 0.4),
    "stack": (lambda p: mix(tone(1200, 1200, 0.2, "sine", 0.3, 2.5), tone(1800, 1800, 0.15, "sine", 0.15, 2.5)), 1, 0.15, 0.6),
    "warning": (lambda p: seq(tone(600, 600, 0.12, "square", 0.3, 1), silence(0.05), tone(600, 600, 0.12, "square", 0.3, 1)), 1, 0.5, 0.7),
    "tick": (lambda p: tone(1000, 1000, 0.03, "sine", 0.25, 1), 1, 0.2, 0.5),
    "income": (lambda p: seq(noise_burst(0.03, 0.3, 2, 0.3), mix(tone(2093, 2093, 0.4, "sine", 0.3, 3), tone(3136, 3136, 0.3, "sine", 0.15, 3))), 1, 0.2, 0.7),
    "wave_money": (lambda p: seq(*[seq(tone(f, f, 0.05, "square", 0.18, 1.5), silence(0.02)) for f in (1047, 1175, 1319, 1568, 1760, 2093)]), 1, 0.5, 0.6),
    "hover": (lambda p: tone(1800, 1800, 0.015, "sine", 0.12, 1), 1, 0.06, 0.3),
    "select": (lambda p: tone(700, 1000, 0.05, "sine", 0.3, 2), 1, 0.05, 0.5),
    "win": (lambda p: seq(*[tone(523, 523, 0.12, "square", 0.3, 1)] * 3, tone(659, 659, 0.4, "square", 0.3, 1.5)), 1, 1.0, 0.8),
    "lose": (lambda p: seq(tone(392, 392, 0.2, "saw", 0.3, 1), tone(370, 370, 0.2, "saw", 0.3, 1), tone(349, 349, 0.2, "saw", 0.3, 1), tone(330, 330, 0.6, "saw", 0.3, 1.5)), 1, 1.0, 0.8),
}


def _to_sound(samples: Samples, volume: float) -> pygame.mixer.Sound:
    data = array.array("h", [int(max(-1.0, min(1.0, s)) * 32767) for s in samples])
    snd = pygame.mixer.Sound(buffer=data.tobytes())
    snd.set_volume(volume)
    return snd


class Audio:
    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self.master = 0.7
        self._sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self._base_volume: dict[str, float] = {}
        self._last: dict[str, float] = {}
        try:
            pygame.mixer.quit()
            pygame.mixer.init(SAMPLE_RATE, -16, 1, 512, allowedchanges=0)
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            return  # no audio device: stay silent
        self.enabled = True
        for name, (builder, variants, _gap, vol) in SOUNDS.items():
            self._base_volume[name] = vol
            self._sounds[name] = self._load(name, builder, variants)

    def _load(self, name: str, builder, variants: int) -> list[pygame.mixer.Sound]:
        for ext in (".ogg", ".wav"):
            path = os.path.join(SFX_DIR, name + ext)
            if os.path.isfile(path):
                try:
                    return [pygame.mixer.Sound(path)]
                except pygame.error:
                    break  # unreadable file: fall back to the generated sound
        return [_to_sound(builder(p), 1.0) for p in PITCH_VARIANTS[:variants]]

    def play(self, name: str) -> None:
        if not self.enabled or self.muted or name not in self._sounds:
            return
        now = time.monotonic()
        if now - self._last.get(name, 0.0) < SOUNDS[name][2]:
            return  # rate limit: a swarm of hits must not turn into noise
        self._last[name] = now
        snd = random.choice(self._sounds[name])
        snd.set_volume(self._base_volume[name] * self.master)
        snd.play()
