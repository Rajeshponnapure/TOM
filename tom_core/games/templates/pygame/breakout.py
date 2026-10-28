"""Breakout — keep the ball in play with the paddle and clear the bricks. Left/Right to move, Space to
launch. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.lives = g.get("lives", 3)
        self.paddle = pygame.Rect(self.w // 2 - 55, self.h - 46, 110, 14)
        self.paddle_speed = g.get("paddle_speed", 9)
        self.ball_speed = g.get("ball_speed", 6.0)
        self.build_wall()
        self.serve()

    def build_wall(self):
        cols, rows = 10, self.cfg["game"].get("brick_rows", 5)
        bw = (self.w - 40) // cols
        self.bricks = [pygame.Rect(20 + c * bw + 2, 60 + r * 26, bw - 4, 20) for r in range(rows) for c in range(cols)]

    def serve(self):
        self.stuck = True
        self.stuck_frames = 0
        self.ball = [float(self.paddle.centerx - 6), float(self.paddle.top - 14)]
        self.vel = [0.0, 0.0]

    def launch(self):
        self.stuck = False
        self.vel = [self.ball_speed * self.rng.choice((-0.6, 0.6)), -self.ball_speed]

    def step(self, controls):
        if controls.held("left"):
            self.paddle.x -= self.paddle_speed
        if controls.held("right"):
            self.paddle.x += self.paddle_speed
        self.paddle.clamp_ip(pygame.Rect(0, 0, self.w, self.h))
        if self.stuck:
            self.stuck_frames += 1
            self.ball = [float(self.paddle.centerx - 6), float(self.paddle.top - 14)]
            if controls.tapped("action") or controls.tapped("up") or self.stuck_frames > 90:
                self.launch()
            return
        self.ball[0] += self.vel[0]
        self.ball[1] += self.vel[1]
        rect = pygame.Rect(int(self.ball[0]), int(self.ball[1]), 12, 12)
        if rect.left <= 0 or rect.right >= self.w:
            self.vel[0] = abs(self.vel[0]) if rect.left <= 0 else -abs(self.vel[0])
        if rect.top <= 44:
            self.vel[1] = abs(self.vel[1])
        if rect.colliderect(self.paddle) and self.vel[1] > 0:
            offset = (rect.centerx - self.paddle.centerx) / (self.paddle.width / 2)
            self.vel[0] = self.ball_speed * max(-1.2, min(1.2, offset))
            self.vel[1] = -abs(self.vel[1])
        hit = rect.collidelist(self.bricks)
        if hit >= 0:
            brick = self.bricks.pop(hit)
            self.score += 10
            if abs(rect.centerx - brick.centerx) * brick.height > abs(rect.centery - brick.centery) * brick.width:
                self.vel[0] = -self.vel[0]
            else:
                self.vel[1] = -self.vel[1]
            if not self.bricks:
                self.ball_speed += 0.6
                self.build_wall()
                self.serve()
        if rect.top > self.h:
            self.lives -= 1
            if self.lives <= 0:
                self.end()
            else:
                self.serve()

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        for i, brick in enumerate(self.bricks):
            pygame.draw.rect(screen, color(self.cfg, "hazard" if (brick.y // 26) % 2 else "ground"), brick)
        pygame.draw.rect(screen, color(self.cfg, "player"), self.paddle)
        pygame.draw.rect(screen, color(self.cfg, "target"), pygame.Rect(int(self.ball[0]), int(self.ball[1]), 12, 12))
        for i in range(self.lives):
            pygame.draw.rect(screen, color(self.cfg, "player_accent"), pygame.Rect(self.w - 30 - i * 24, 14, 16, 10))


if __name__ == "__main__":
    run(Game)
