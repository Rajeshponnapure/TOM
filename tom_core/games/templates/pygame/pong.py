"""Pong — beat the computer paddle. Up/Down (or W/S) to move. First to miss three loses. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.lives = g.get("lives", 3)
        self.speed = g.get("ball_speed", 6.0)
        self.ai_speed = g.get("ai_speed", 5.0)
        self.me = pygame.Rect(24, self.h // 2 - 50, 14, 100)
        self.cpu = pygame.Rect(self.w - 38, self.h // 2 - 50, 14, 100)
        self.serve(1)

    def serve(self, direction):
        self.ball = [self.w / 2 - 7, self.h / 2 - 7]
        self.vel = [self.speed * direction, self.speed * self.rng.uniform(-0.6, 0.6)]

    def step(self, controls):
        if controls.held("up"):
            self.me.y -= 8
        if controls.held("down"):
            self.me.y += 8
        arena = pygame.Rect(0, 44, self.w, self.h - 44)
        self.me.clamp_ip(arena)
        target = self.ball[1] + 7 if self.vel[0] > 0 else self.h / 2
        if abs(target - self.cpu.centery) > 6:
            self.cpu.y += int(self.ai_speed if target > self.cpu.centery else -self.ai_speed)
        self.cpu.clamp_ip(arena)
        self.ball[0] += self.vel[0]
        self.ball[1] += self.vel[1]
        rect = pygame.Rect(int(self.ball[0]), int(self.ball[1]), 14, 14)
        if rect.top <= 44 or rect.bottom >= self.h:
            self.vel[1] = abs(self.vel[1]) if rect.top <= 44 else -abs(self.vel[1])
        for paddle, sign in ((self.me, 1), (self.cpu, -1)):
            if rect.colliderect(paddle) and self.vel[0] * sign < 0:
                offset = (rect.centery - paddle.centery) / (paddle.height / 2)
                speed = min(13.0, abs(self.vel[0]) + 0.35)
                self.vel = [speed * sign, speed * 0.75 * max(-1.0, min(1.0, offset))]
        if rect.left > self.w:
            self.score += 1
            self.serve(-1)
        elif rect.right < 0:
            self.lives -= 1
            if self.lives <= 0:
                self.end()
            else:
                self.serve(1)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        for y in range(54, self.h, 30):
            pygame.draw.rect(screen, color(self.cfg, "accent"), pygame.Rect(self.w // 2 - 2, y, 4, 14))
        pygame.draw.rect(screen, color(self.cfg, "player"), self.me)
        pygame.draw.rect(screen, color(self.cfg, "hazard"), self.cpu)
        pygame.draw.rect(screen, color(self.cfg, "target"), pygame.Rect(int(self.ball[0]), int(self.ball[1]), 14, 14))
        for i in range(self.lives):
            pygame.draw.rect(screen, color(self.cfg, "player_accent"), pygame.Rect(self.w - 30 - i * 24, 14, 16, 10))


if __name__ == "__main__":
    run(Game)
