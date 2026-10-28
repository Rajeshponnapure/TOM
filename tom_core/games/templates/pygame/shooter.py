"""Space shooter — move left/right, hold Space to fire, stop the invaders reaching you. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.lives = g.get("lives", 3)
        self.ship = pygame.Rect(self.w // 2 - 22, self.h - 50, 44, 26)
        self.ship_speed = g.get("ship_speed", 7)
        self.enemy_speed = g.get("enemy_speed", 1.6)
        self.spawn_every = g.get("spawn_every", 55)
        self.bullets = []                               # rects moving up
        self.enemies = []                               # [x, y(float), speed]
        self.cooldown = 0
        self.spawn = 0

    def step(self, controls):
        if controls.held("left"):
            self.ship.x -= self.ship_speed
        if controls.held("right"):
            self.ship.x += self.ship_speed
        self.ship.clamp_ip(pygame.Rect(0, 0, self.w, self.h))
        self.cooldown -= 1
        if controls.held("action") and self.cooldown <= 0:
            self.bullets.append(pygame.Rect(self.ship.centerx - 3, self.ship.top - 12, 6, 12))
            self.cooldown = 9
        for b in self.bullets:
            b.y -= 11
        self.bullets = [b for b in self.bullets if b.bottom > 44]
        self.spawn -= 1
        if self.spawn <= 0:
            self.spawn = max(18, self.spawn_every - self.score)
            speed = self.enemy_speed + min(2.5, self.score * 0.05) + self.rng.random() * 0.8
            self.enemies.append([self.rng.randint(10, self.w - 46), 46.0, speed])
        survivors = []
        for enemy in self.enemies:
            enemy[1] += enemy[2]
            rect = pygame.Rect(int(enemy[0]), int(enemy[1]), 36, 24)
            shot = rect.collidelist(self.bullets)
            if shot >= 0:
                self.bullets.pop(shot)
                self.score += 1
                continue
            if rect.colliderect(self.ship):
                self.end()
                return
            if rect.top > self.h:
                self.lives -= 1
                if self.lives <= 0:
                    self.end()
                    return
                continue
            survivors.append(enemy)
        self.enemies = survivors

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        for b in self.bullets:
            pygame.draw.rect(screen, color(self.cfg, "player_accent"), b)
        for x, y, _ in self.enemies:
            pygame.draw.rect(screen, color(self.cfg, "hazard"), pygame.Rect(int(x), int(y), 36, 24))
        pygame.draw.rect(screen, color(self.cfg, "player"), self.ship)
        for i in range(self.lives):
            pygame.draw.rect(screen, color(self.cfg, "player_accent"), pygame.Rect(self.w - 30 - i * 24, 14, 16, 10))


if __name__ == "__main__":
    run(Game)
