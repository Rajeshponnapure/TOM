"""Platformer — run and jump across the platforms collecting coins; avoid the patrolling enemies.
Left/Right to move, Space / Up to jump. Collect every coin for a new level. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run

GROUND = 40


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.run_speed = g.get("run_speed", 5)
        self.jump = g.get("jump", -14.0)
        self.gravity = g.get("gravity", 0.7)
        self.enemy_count = g.get("enemies", 2)
        self.player = pygame.Rect(40, self.h - GROUND - 44, 30, 44)
        self.pos = [float(self.player.x), float(self.player.y)]
        self.vy = 0.0
        self.level = 0
        self.new_level()

    def new_level(self):
        self.level += 1
        floor = self.h - GROUND
        self.platforms = [pygame.Rect(0, floor, self.w, GROUND)]
        rows = [floor - 110, floor - 220, floor - 330]
        for i, y in enumerate(rows):
            for _ in range(2):
                width = self.rng.randint(130, 200)
                x = self.rng.randint(20, self.w - width - 20)
                self.platforms.append(pygame.Rect(x, y - (i % 2) * 10, width, 14))
        self.coins = []
        for plat in self.platforms[1:]:
            self.coins.append(pygame.Rect(plat.centerx - 8, plat.top - 30, 16, 16))
        for _ in range(3):
            self.coins.append(pygame.Rect(self.rng.randint(120, self.w - 40), floor - 30, 16, 16))
        self.enemies = []                                # [rect, platform, direction]
        for i in range(self.enemy_count + self.level // 3):
            plat = self.platforms[1 + i % (len(self.platforms) - 1)]
            rect = pygame.Rect(plat.left + 4, plat.top - 22, 22, 22)
            self.enemies.append([rect, plat, 1])
        self.grace = 60

    def step(self, controls):
        dx = 0
        if controls.held("left"):
            dx -= self.run_speed
        if controls.held("right"):
            dx += self.run_speed
        on_ground = self._standing()
        if on_ground and (controls.held("action") or controls.held("up")):
            self.vy = self.jump
        self.vy = min(self.vy + self.gravity, 14.0)
        self.pos[0] = max(0.0, min(float(self.w - self.player.width), self.pos[0] + dx))
        self.player.x = int(self.pos[0])
        prev_bottom = self.player.bottom
        self.pos[1] += self.vy
        self.player.y = int(self.pos[1])
        if self.vy >= 0:
            for plat in self.platforms:
                if self.player.colliderect(plat) and prev_bottom <= plat.top + 2:
                    self.player.bottom = plat.top
                    self.pos[1] = float(self.player.y)
                    self.vy = 0.0
                    break
        if self.player.top < 44:
            self.player.top = 44
            self.pos[1] = float(self.player.y)
            self.vy = max(self.vy, 0.0)
        got = [c for c in self.coins if self.player.colliderect(c)]
        for coin in got:
            self.coins.remove(coin)
            self.score += 1
        if not self.coins:
            self.new_level()
        for enemy in self.enemies:
            rect, plat, direction = enemy
            rect.x += direction * (1 + self.level // 4)
            if rect.left <= plat.left or rect.right >= plat.right:
                enemy[2] = -direction
            if self.grace <= 0 and self.player.colliderect(rect):
                self.end()
                return
        self.grace -= 1

    def _standing(self):
        feet = pygame.Rect(self.player.x, self.player.bottom, self.player.width, 2)
        return self.vy >= 0 and any(feet.colliderect(p) for p in self.platforms)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        for plat in self.platforms:
            pygame.draw.rect(screen, color(self.cfg, "ground"), plat)
        for coin in self.coins:
            pygame.draw.rect(screen, color(self.cfg, "target"), coin)
        for rect, _, _ in self.enemies:
            pygame.draw.rect(screen, color(self.cfg, "hazard"), rect)
        pygame.draw.rect(screen, color(self.cfg, "player"), self.player)


if __name__ == "__main__":
    run(Game)
