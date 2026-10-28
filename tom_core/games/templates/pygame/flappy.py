"""Flappy — flap through the gaps between the pillars. Space / Up to flap. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run

GROUND = 40


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.gravity = g.get("gravity", 0.42)
        self.flap = g.get("flap", -7.4)
        self.gap = g.get("gap", 175)
        self.speed = g.get("speed", 3.2)
        self.spacing = g.get("spacing", 270)
        self.bird = pygame.Rect(self.w // 4, self.h // 2 - 40, 30, 24)
        self.y = float(self.bird.y)
        self.vy = self.flap
        self.pipes = []                                  # [x, gap_top, scored]
        self.next_x = float(self.w + 40)

    def step(self, controls):
        if controls.tapped("action") or controls.tapped("up"):
            self.vy = self.flap
        self.vy = min(self.vy + self.gravity, 10.0)
        self.y += self.vy
        self.bird.y = int(self.y)
        if self.y < 44:
            self.y, self.vy = 44.0, 0.0
        self.next_x -= self.speed
        if self.next_x <= self.w:
            top = self.rng.randint(90, self.h - GROUND - self.gap - 40)
            self.pipes.append([self.next_x, top, False])
            self.next_x += self.spacing
        for pipe in self.pipes:
            pipe[0] -= self.speed
            if not pipe[2] and pipe[0] + 70 < self.bird.left:
                pipe[2] = True
                self.score += 1
        self.pipes = [p for p in self.pipes if p[0] > -80]
        if self.bird.bottom >= self.h - GROUND or any(self.bird.colliderect(r) for r in self.pipe_rects()):
            self.end()

    def pipe_rects(self):
        for x, top, _ in self.pipes:
            yield pygame.Rect(int(x), 0, 70, top)
            yield pygame.Rect(int(x), top + self.gap, 70, self.h - GROUND - top - self.gap)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        for rect in self.pipe_rects():
            pygame.draw.rect(screen, color(self.cfg, "hazard"), rect)
        pygame.draw.rect(screen, color(self.cfg, "ground"), pygame.Rect(0, self.h - GROUND, self.w, GROUND))
        pygame.draw.rect(screen, color(self.cfg, "player"), self.bird)


if __name__ == "__main__":
    run(Game)
