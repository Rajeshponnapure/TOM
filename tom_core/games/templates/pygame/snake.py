"""Snake — eat the food, grow, don't hit the walls or yourself. Arrow keys / WASD. Made by TOM."""
import pygame

from tomgame import BaseGame, color, run

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
HUD = 44


class Game(BaseGame):
    def reset(self):
        g = self.cfg["game"]
        self.cols, self.rows = g.get("cols", 24), g.get("rows", 17)
        self.cell = min(self.w // self.cols, (self.h - HUD) // self.rows)
        self.x0 = (self.w - self.cell * self.cols) // 2
        self.y0 = HUD + (self.h - HUD - self.cell * self.rows) // 2
        self.move_every = max(1, int(g.get("move_every", 7)))
        cx, cy = self.cols // 2, self.rows // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.heading = (1, 0)
        self.turns = []
        self.tick = 0
        self.place_food()

    def place_food(self):
        free = [(x, y) for x in range(self.cols) for y in range(self.rows) if (x, y) not in self.body]
        self.food = self.rng.choice(free) if free else None

    def step(self, controls):
        for name, d in DIRS.items():
            if controls.tapped(name) or (controls.held(name) and not self.turns):
                last = self.turns[-1] if self.turns else self.heading
                if d != last and d != (-last[0], -last[1]) and len(self.turns) < 2:
                    self.turns.append(d)
        self.tick += 1
        if self.tick % self.move_every:
            return
        if self.turns:
            self.heading = self.turns.pop(0)
        hx, hy = self.body[0]
        head = (hx + self.heading[0], hy + self.heading[1])
        grow = head == self.food
        body = self.body if grow else self.body[:-1]
        if not (0 <= head[0] < self.cols and 0 <= head[1] < self.rows) or head in body:
            self.end()
            return
        self.body = [head] + body
        if grow:
            self.score += 1
            self.place_food()
            if self.food is None:
                self.end()

    def _cell_rect(self, x, y):
        return pygame.Rect(self.x0 + x * self.cell + 1, self.y0 + y * self.cell + 1, self.cell - 2, self.cell - 2)

    def draw(self, screen):
        screen.fill(color(self.cfg, "background"))
        board = pygame.Rect(self.x0 - 3, self.y0 - 3, self.cell * self.cols + 6, self.cell * self.rows + 6)
        pygame.draw.rect(screen, color(self.cfg, "accent"), board, 3)
        if self.food is not None:
            pygame.draw.rect(screen, color(self.cfg, "target"), self._cell_rect(*self.food))
        for i, (x, y) in enumerate(self.body):
            pygame.draw.rect(screen, color(self.cfg, "player" if i == 0 else "player_accent"), self._cell_rect(x, y))


if __name__ == "__main__":
    run(Game)
