"""Animator that replays a solution path using the Renderer.

Controls:
  SPACE - pause/resume
  RIGHT - next step
  LEFT  - previous step
  R     - restart
  ESC   - quit
"""
from typing import List, Dict, Any, Optional
import time


class SolutionAnimator:
    """Replay a list of StateNode objects as a pygame animation.

    The animator converts states to view models via the ViewModel layer
    and delegates drawing to the Renderer.
    """

    def __init__(self, scenario: Dict[str, Any], solution_path: List[Any]):
        self.scenario = scenario
        self.solution_path = list(solution_path)
        self.current_index = 0
        self.paused = False
        self._last_advance = 0.0

        # derived
        self.total = len(self.solution_path)

        # precompute view models (lightweight)
        from .view_models import state_to_view_model

        self.view_models = [state_to_view_model(s, scenario) for s in self.solution_path]

    def next_step(self) -> None:
        if self.current_index < self.total - 1:
            self.current_index += 1

    def previous_step(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def restart(self) -> None:
        self.current_index = 0
        self.paused = False

    def render_current_state(self, renderer, step_info: Dict[str, Any]) -> None:
        vm = self.view_models[self.current_index]
        renderer.draw_complete_scene(vm, self.current_index + 1, self.total, step_info.get("generated"))

    def run(self) -> None:
        """Start the pygame loop and replay the solution path.

        This method blocks until the user quits the window.
        """
        try:
            import pygame
        except Exception as e:
            raise RuntimeError("pygame is required to run the animator: install pygame") from e

        from .renderer import Renderer
        from .constants import FPS, STEP_DURATION

        pygame.init()

        # window sizing
        cols = self.scenario.get("grid", {}).get("cols", 5)
        rows = self.scenario.get("grid", {}).get("rows", 5)
        cell = 64
        width = cols * cell + 300
        height = rows * cell + 150
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Smart Flower Exhibition - Solution Replay")

        renderer = Renderer(screen, self.scenario)

        clock = pygame.time.Clock()

        running = True
        self._last_advance = time.time() * 1000

        # try to show number of generated states if available
        generated = None
        # If the solution_path elements have no attribute for generated count,
        # caller can pass this info via step_info. We keep it optional.

        while running:
            now = time.time() * 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.toggle_pause()
                    elif event.key == pygame.K_RIGHT:
                        self.next_step()
                    elif event.key == pygame.K_LEFT:
                        self.previous_step()
                    elif event.key == pygame.K_r:
                        self.restart()

            if not self.paused and (now - self._last_advance) >= STEP_DURATION:
                self.next_step()
                self._last_advance = now

            # render
            step_info = {"generated": generated}
            self.render_current_state(renderer, step_info)

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
