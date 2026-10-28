"""Lane racer — dodge the traffic by switching lanes. Left/Right to change lane. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.lanes = max(3, int(g.get("lanes", 3)))
        self.road = pygame.Rect(self.w // 2 - self.lanes * 60, 44, self.lanes * 120, self.h - 44)
        self.speed = g.get("speed", 5.0)
        self.lane = self.lanes // 2
        self.car = pygame.Rect(0, self.h - 110, 52, 84)
        self.car.centerx = self.lane_x(self.lane)
        self.x = float(self.car.x)
        self.traffic = []                                # [lane, y(float), scored]
        self.gap = 40
        self.scroll = 0.0

    def lane_x(self, lane):
        return self.road.left + 60 + lane * 120

    def step(self, controls):
        if controls.tapped("left"):
            self.lane = max(0, self.lane - 1)
        if controls.tapped("right"):
            self.lane = min(self.lanes - 1, self.lane + 1)
        goal = self.lane_x(self.lane) - self.car.width / 2
        self.x += max(-12.0, min(12.0, goal - self.x))
        self.car.x = int(self.x)
        self.scroll = (self.scroll + self.speed) % 60
        self.gap -= 1
        if self.gap <= 0:
            blocked = self.rng.sample(range(self.lanes), self.rng.randint(1, self.lanes - 1))
            for lane in blocked:
                self.traffic.append([lane, -90.0, False])
            self.gap = max(28, int(260 / self.speed))
        for car in self.traffic:
            car[1] += self.speed
            if not car[2] and car[1] > self.car.bottom:
                car[2] = True
                self.score += 1
                self.speed = min(13.0, self.speed + 0.04)
        self.traffic = [c for c in self.traffic if c[1] < self.h + 10]
        if any(self.car.colliderect(r) for r in self.traffic_rects()):
            self.end()

    def traffic_rects(self):
        for lane, y, _ in self.traffic:
            yield pygame.Rect(self.lane_x(lane) - 26, int(y), 52, 84)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        pygame.draw.rect(screen, color(self.cfg, "ground"), self.road)
        for lane in range(1, self.lanes):
            x = self.road.left + lane * 120 - 2
            for y in range(int(self.scroll) - 60, self.h, 60):
                pygame.draw.rect(screen, color(self.cfg, "accent"), pygame.Rect(x, max(44, y), 4, 30))
        for rect in self.traffic_rects():
            pygame.draw.rect(screen, color(self.cfg, "hazard"), rect)
        pygame.draw.rect(screen, color(self.cfg, "player"), self.car)


if __name__ == "__main__":
    run(Game)
