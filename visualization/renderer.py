"""Pygame-based Renderer for drawing a single state scene.

The Renderer is intentionally stateless with respect to the search: it
only reads the view model dict passed to it and draws accordingly.
"""
from typing import Dict, Any, Optional, Tuple
import pygame

from .constants import (
    CELL_SIZE,
    WINDOW_PADDING,
    WHITE,
    BLACK,
    GRAY,
    BLUE,
    GREEN,
    ORANGE,
    RED,
    YELLOW,
)


class Renderer:
    """Draws the current state and auxiliary panels onto a pygame surface.

    The renderer does not interpret search internals — it draws the
    plain dictionaries produced by the ViewModel layer.
    """

    def __init__(self, screen: pygame.Surface, scenario: Dict[str, Any]):
        self.screen = screen
        self.scenario = scenario
        self.cols = scenario.get("grid", {}).get("cols", 5)
        self.rows = scenario.get("grid", {}).get("rows", 5)

        # layout areas
        self.width, self.height = screen.get_size()
        self.panel_width = WINDOW_PADDING
        self.grid_origin = (20, 60)

        # compute cell size (auto-scale to fit available area)
        max_grid_width = self.width - self.grid_origin[0] - self.panel_width - 20
        max_grid_height = self.height - self.grid_origin[1] - 20
        scale_x = max_grid_width / (self.cols * CELL_SIZE)
        scale_y = max_grid_height / (self.rows * CELL_SIZE)
        self.scale = min(1.0, scale_x, scale_y)
        self.cell = max(8, int(CELL_SIZE * self.scale))

        # fonts
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", 16)
        self.big_font = pygame.font.SysFont("Arial", 20, bold=True)

    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        gx = self.grid_origin[0] + x * self.cell
        gy = self.grid_origin[1] + y * self.cell
        return pygame.Rect(gx, gy, self.cell, self.cell)

    def draw_grid(self) -> None:
        for c in range(self.cols + 1):
            x = self.grid_origin[0] + c * self.cell
            pygame.draw.line(self.screen, GRAY, (x, self.grid_origin[1]), (x, self.grid_origin[1] + self.rows * self.cell), 2)
        for r in range(self.rows + 1):
            y = self.grid_origin[1] + r * self.cell
            pygame.draw.line(self.screen, GRAY, (self.grid_origin[0], y), (self.grid_origin[0] + self.cols * self.cell, y), 2)

    def draw_warehouse(self, vm: Dict[str, Any]) -> None:
        wh = vm.get("warehouse", {})
        if not wh:
            return
        x = wh.get("x", 0)
        y = wh.get("y", 0)
        rect = self._cell_rect(x, y)
        pygame.draw.rect(self.screen, ORANGE, rect)

    def draw_pavilions(self, vm: Dict[str, Any]) -> None:
        pavilions = vm.get("pavilions", [])
        remaining = vm.get("remaining_needs", {})
        for p in pavilions:
            x = p.get("x")
            y = p.get("y")
            pid = p.get("pavilion_id")
            rect = self._cell_rect(x, y)
            pygame.draw.rect(self.screen, GREEN, rect)

            # draw pavilion id
            text = self.font.render(pid, True, BLACK)
            self.screen.blit(text, (rect.x + 4, rect.y + 2))

            # draw remaining needs above the pavilion
            rem = remaining.get(pid, [])
            tx = rect.x
            ty = rect.y - 4 - (len(rem) * 16)
            for i, need in enumerate(rem):
                s = f"{need['flower']} {need['color']} x{need['quantity']}"
                t = self.font.render(s, True, BLACK)
                self.screen.blit(t, (tx, ty + i * 16))

    def draw_robot(self, vm: Dict[str, Any]) -> None:
        rx, ry = vm.get("robot_position", (0, 0))
        rect = self._cell_rect(rx, ry)
        cx = rect.centerx
        cy = rect.centery
        radius = max(6, int(self.cell * 0.35))
        pygame.draw.circle(self.screen, BLUE, (cx, cy), radius)

    def draw_inventory_panel(self, vm: Dict[str, Any]) -> None:
        x = self.width - self.panel_width + 10
        y = self.grid_origin[1]
        title = self.big_font.render("Robot Inventory", True, BLACK)
        self.screen.blit(title, (x, y))
        y += 28
        inv = vm.get("inventory", [])
        if not inv:
            t = self.font.render("(empty)", True, BLACK)
            self.screen.blit(t, (x, y))
            return
        for b in inv:
            s = f"{b['flower']} {b['color']} x{b['quantity']}"
            t = self.font.render(s, True, BLACK)
            self.screen.blit(t, (x, y))
            y += 18

    def draw_status_panel(self, vm: Dict[str, Any], step: int, total: int, generated: Optional[int] = None) -> None:
        x = self.grid_origin[0]
        y = 8
        s1 = f"Step: {step}/{total}"
        s2 = f"Action: {vm.get('action', '')}"
        s3 = f"g={vm.get('g_cost', 0)} h={vm.get('h_cost', 0)} f={vm.get('f_cost', 0)}"
        self.screen.blit(self.font.render(s1, True, BLACK), (x, y))
        self.screen.blit(self.font.render(s2, True, BLACK), (x + 140, y))
        self.screen.blit(self.font.render(s3, True, BLACK), (x + 420, y))
        if generated is not None:
            self.screen.blit(self.font.render(f"Generated: {generated}", True, BLACK), (x + 640, y))

    def draw_step_counter(self, step: int) -> None:
        # small visual indicator at bottom-left
        txt = self.font.render(f"Step {step}", True, BLACK)
        self.screen.blit(txt, (self.grid_origin[0], self.grid_origin[1] + self.rows * self.cell + 8))

    def draw_complete_scene(self, vm: Dict[str, Any], step: int, total: int, generated: Optional[int] = None) -> None:
        # background
        self.screen.fill(WHITE)

        # draw grid/objects
        self.draw_grid()
        self.draw_warehouse(vm)
        self.draw_pavilions(vm)
        self.draw_robot(vm)

        # panels
        self.draw_inventory_panel(vm)
        self.draw_status_panel(vm, step, total, generated)
        self.draw_step_counter(step)
