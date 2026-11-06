"""Enemy: walks the path by `distance`; supports slow, stun, push-back and spawn-on-death."""
from __future__ import annotations

import random

import pygame

from data.enemies import ENEMIES, NORMAL_SPEED
from data.settings import BOSS_SLOW_FACTOR, COLORS, SLOW_FLOOR
from game import gfx, sprites_proc
from game.assets import sprite
from game.utils import Path, Vec, draw_outlined

WALK_FRAMES_PER_PX = 0.11  # animation speed: frames advance with distance walked


class Enemy:
    def __init__(self, kind: str, path: Path, gives_money: bool = True,
                 hp_mult: float = 1.0, speed_mult: float = 1.0, bounty_mult: float = 1.0) -> None:
        d = ENEMIES[kind]
        self.kind = kind
        self.name: str = d["name"]
        self.path = path
        self.hp_mult, self.speed_mult, self.bounty_mult = hp_mult, speed_mult, bounty_mult  # children inherit these
        self.max_hp = float(d["hp"]) * hp_mult
        self.hp = self.max_hp
        self.base_speed = float(d["speed"]) * speed_mult
        self.stash_damage: int = d["stash_damage"]
        self.bounty: int = max(1, round(d["money"] * bounty_mult))
        self.radius: int = d["radius"]
        self.color = d["color"]
        self.is_boss: bool = d["is_boss"]
        self.spawns: tuple[str, int] | None = d.get("spawns")  # (kind, count) released on death
        self.gives_money = gives_money
        self.armor: int = d.get("armor", 0)  # hits left before the armor breaks
        self.max_armor: int = self.armor
        self.is_fast: bool = d.get("fast", False)
        self.mini: bool = d.get("mini", False)
        self.steal: int = round(d.get("steal", 0) * bounty_mult)  # money stolen if it leaks
        self.decel: tuple[float, float] | None = d.get("decel")
        self.age = 0.0
        # Bima / ability state
        self.shape_mask = 0          # shape stack slots: bit 0 square, 1 triangle, 2 circle
        self.collision_ready = 0.0   # game time when the next shape collision may trigger
        self.vuln, self.vuln_timer = 0.0, 0.0   # square: takes extra damage
        self.last_shot = 0           # id of the last curve shot that hit it (one hit per shot)
        self.blocked = False         # held back by a cube
        self.cube_immune = self.stall = self.thorn_t = 0.0
        self.trap_immune = self.bubble = 0.0
        self.normalize_timer = 0.0  # >0: a fast enemy walks at normal speed (Speed Against Time)
        self.armor_flash = 0.0
        self.hp_ghost = self.max_hp   # lags behind hp: shows recent damage on the health bar
        self.trail: list[list] = []   # Speedster afterimages: [x, y, frame, facing_left, age]
        self.distance = 0.0  # used for "first" targeting and push-back
        self.pos: Vec = path.position_at(0)
        self.slow_strength = 0.0
        self.slow_timer = 0.0
        self.stun_timer = 0.0  # >0: stopped (sleep effect)
        self.hit_flash = 0.0   # visual: body flashes white when hit
        self.facing_left = False  # visual: sprites flip when walking left
        self.anim_offset = random.uniform(0, 8)
        self.reached_end = False

    @property
    def armor_stage(self) -> int:
        """2 = full armor, 1 = damaged (half or less left), 0 = none."""
        if self.armor <= 0:
            return 0
        return 2 if self.armor > self.max_armor / 2 else 1

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.reached_end

    @property
    def speed(self) -> float:
        if self.stun_timer > 0 or self.blocked:
            return 0.0
        speed = self.base_speed
        if self.decel:  # Speedster: starts very fast, slows down the longer it runs
            boost, seconds = self.decel
            speed *= 1.0 + boost * max(0.0, 1.0 - self.age / seconds)
        if self.normalize_timer > 0 and self.is_fast:
            speed = min(speed, NORMAL_SPEED * self.speed_mult)
        return speed * max(SLOW_FLOOR, 1.0 - self.slow_strength)

    def apply_slow(self, strength: float, duration: float) -> None:
        """Strongest slow wins; bosses take half the effect."""
        if self.is_boss:
            strength *= BOSS_SLOW_FACTOR
        if self.slow_timer <= 0 or strength >= self.slow_strength:
            self.slow_strength = strength
            self.slow_timer = duration

    def stun(self, duration: float) -> None:
        """Stop for `duration` seconds. Bosses are immune."""
        if not self.is_boss:
            self.stun_timer = max(self.stun_timer, duration)

    def push_back(self, distance: float) -> None:
        """Shove back along the path. Bosses are immune."""
        if not self.is_boss:
            self.distance = max(0.0, self.distance - distance)
            self.pos = self.path.position_at(self.distance)

    def break_armor(self, hits: int) -> bool:
        """Armor soaks hits instead of HP. Returns True when this hit broke the last of it."""
        self.armor = max(0, self.armor - hits)
        self.armor_flash = 0.12
        return self.armor == 0

    def take_damage(self, amount: float) -> None:
        self.hp -= amount
        self.hit_flash = 0.1

    def update(self, dt: float) -> None:
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_strength = 0.0
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.armor_flash = max(0.0, self.armor_flash - dt)
        if self.hp_ghost > self.hp:
            self.hp_ghost = max(self.hp, self.hp_ghost - self.max_hp * dt * 0.9)
        for t in self.trail:
            t[4] += dt
        if self.trail and self.trail[0][4] > 0.4:
            self.trail = [t for t in self.trail if t[4] <= 0.4]
        self.age += dt
        self.vuln_timer = max(0.0, self.vuln_timer - dt)
        self.bubble = max(0.0, self.bubble - dt)
        self.normalize_timer = max(0.0, self.normalize_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer -= dt
        self.distance += self.speed * dt
        if self.distance >= self.path.length:
            self.reached_end = True
        new_pos = self.path.position_at(self.distance)
        if abs(new_pos.x - self.pos.x) > 1e-6:
            self.facing_left = new_pos.x < self.pos.x
        self.pos = new_pos
        if self.decel and self.speed > self.base_speed * 1.25 and (not self.trail or self.trail[-1][0:2] == [] or Vec(self.trail[-1][0], self.trail[-1][1]).distance_to(new_pos) > 10):
            self.trail.append([new_pos.x, new_pos.y, int(self.distance * WALK_FRAMES_PER_PX + self.anim_offset), self.facing_left, 0.0])

    # ----------------------------------------------------------------- draw
    def draw_shadow(self, surface: pygame.Surface) -> None:
        r = self.radius
        if self.kind in sprites_proc.TROJAN_KINDS:  # the cart's wheels stand ON the road: shadow under them
            gfx.blit_shadow(surface, (self.pos.x + r * 0.1, self.pos.y + r * 0.1), r * 2.5, r * 0.6, 110)
        else:
            gfx.blit_shadow(surface, (self.pos.x + r * 0.35, self.pos.y + r * 0.78), r * 2.0, r * 0.85, 100)
        if self.is_boss:  # pulsing glow on the ground
            import math
            pulse = 1.0 + 0.12 * math.sin(pygame.time.get_ticks() / 150)
            g = gfx.glow(int(r * 2.1 * pulse), (255, 70, 60) if self.kind == "boss" else (255, 190, 60), 150)
            surface.blit(g, g.get_rect(center=(int(self.pos.x), int(self.pos.y + r * 0.2))))

    def draw(self, surface: pygame.Surface) -> None:
        r = self.radius
        x, y = int(self.pos.x), int(self.pos.y)
        lift = int(round(sprites_proc.trojan_lift(r))) if self.kind in sprites_proc.TROJAN_KINDS else 0
        y -= lift  # Trojans: raise the body so the wheels (not the body centre) touch the path
        frame = 0 if self.stun_timer > 0 else int(self.distance * WALK_FRAMES_PER_PX + self.anim_offset)
        for tx, ty, tf, tl, age in self.trail:  # speed afterimages, fading cyan
            ghost = sprites_proc.enemy_sprite(self.kind, r, self.color, tf, tl, False, 0, True)
            a = int(150 * (1 - age / 0.4))
            if a > 8:
                ghost = ghost.copy()
                ghost.set_alpha(a)
                surface.blit(ghost, ghost.get_rect(center=(int(tx), int(ty) - lift)))
        img = sprite(f"enemies/{self.kind}", 2 * r + 8)  # optional PNG override (faces right)
        if img is not None:
            if lift:  # a PNG override is centred on the position like every other enemy
                y += lift
                lift = 0
            if self.facing_left:
                img = pygame.transform.flip(img, True, False)
            if self.hit_flash > 0:
                img = img.copy()
                img.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            img = sprites_proc.enemy_sprite(self.kind, r, self.color, frame, self.facing_left,
                                            self.hit_flash > 0 or self.armor_flash > 0, self.armor_stage)
        surface.blit(img, img.get_rect(center=(x, y)))
        if self.slow_timer > 0:
            ring = gfx.glow(int(r * 1.5), (120, 190, 255), 140)
            surface.blit(ring, ring.get_rect(center=(x, y)))
        if self.bubble > 0:  # trapped in a sphere
            rad = r + 12
            bub = gfx.glow(int(rad * 1.5), (130, 225, 255), 110)
            surface.blit(bub, bub.get_rect(center=(x, y)))
            pygame.draw.circle(surface, (170, 235, 255), (x, y), rad, 2)
            pygame.draw.circle(surface, (255, 255, 255), (x - rad // 3, y - rad // 3), max(2, rad // 6))
        if self.vuln_timer > 0:  # square mark: takes more damage
            pygame.draw.rect(surface, (255, 160, 60), (x - 5, y - r - 18, 10, 10), 2)
        if self.stun_timer > 0:
            draw_outlined(surface, "z", (x + r, y - r - 12), 22, (255, 255, 255), center=True)
        show = (not self.is_boss) and (self.mini or self.hp < self.max_hp)  # bosses use the big bar at the top
        if show:
            w = max(24, r * 2 + 4) + (10 if self.mini else 0)
            bar = pygame.Rect(0, 0, w, 7 if self.mini else 5)
            bar.midbottom = (x, y - int(r * 1.35) - 2)
            gfx.hp_bar(surface, bar, self.hp / self.max_hp, self.hp_ghost / self.max_hp, gold=self.mini)
        mask = getattr(self, "shape_mask", 0)  # Bima's shape stacks: three slots above the bar
        if mask:
            icons = sprites_proc.stack_icons(mask)
            surface.blit(icons, icons.get_rect(midbottom=(x, y - int(r * 1.35) - (14 if show else 4))))
