"""Endless runner — jump over the obstacles; it speeds up as you go. Space / Up to jump. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run

GROUND = 80


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.speed = g.get("speed", 6.0)
        self.jump = g.get("jump", -15.5)
        self.gravity = g.get("gravity", 0.8)
        self.floor = self.h - GROUND
        self.player = pygame.Rect(110, self.floor - 48, 34, 48)
        self.y = float(self.player.y)
        self.vy = 0.0
        self.obstacles = []                              # [x(float), w, h, scored]
        self.gap = 60

    def step(self, controls):
        on_ground = self.player.bottom >= self.floor
        if on_ground and (controls.held("action") or controls.held("up")):
            self.vy = self.jump
        self.vy += self.gravity
        self.y = min(self.y + self.vy, float(self.floor - self.player.height))
        if self.y >= self.floor - self.player.height:
            self.vy = 0.0
        self.player.y = int(self.y)
        self.gap -= 1
        if self.gap <= 0:
            self.obstacles.append([float(self.w), self.rng.randint(22, 40), self.rng.randint(30, 66), False])
            self.gap = self.rng.randint(55, 110) + int(120 / max(1.0, self.speed / 6.0))
        for ob in self.obstacles:
            ob[0] -= self.speed
            if not ob[3] and ob[0] + ob[1] < self.player.left:
                ob[3] = True
                self.score += 1
                self.speed = min(14.0, self.speed + 0.08)
        self.obstacles = [o for o in self.obstacles if o[0] > -60]
        if any(self.player.colliderect(r) for r in self.obstacle_rects()):
            self.end()

    def obstacle_rects(self):
        for x, w, h, _ in self.obstacles:
            yield pygame.Rect(int(x), self.floor - h, w, h)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        pygame.draw.rect(screen, color(self.cfg, "ground"), pygame.Rect(0, self.floor, self.w, GROUND))
        for rect in self.obstacle_rects():
            pygame.draw.rect(screen, color(self.cfg, "hazard"), rect)
        pygame.draw.rect(screen, color(self.cfg, "player"), self.player)


if __name__ == "__main__":
    run(Game)
