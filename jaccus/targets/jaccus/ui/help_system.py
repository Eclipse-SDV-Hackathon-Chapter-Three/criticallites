#!/usr/bin/env python

"""
Help system implementation.
"""

import pygame


class HelpText(object):
    """Help text display system."""

    def __init__(self, font, width, height):
        """Initialize help text display."""
        help_text = """
Welcome to JACCUS

Use ARROWS or WASD keys for control.

    W            : throttle
    S            : brake
    A/D          : steer left/right
    Q            : toggle reverse
    Space        : hand-brake
    P            : toggle autopilot

    J            : toggle adaptive cruise control (ACC)
    +/-          : increase/decrease ACC target speed

    TAB          : change sensor position
    H/?          : toggle help
    ESC          : quit
"""
        lines = help_text.split('\n')
        self.font = font
        self.line_space = 18
        self.dim = (780, len(lines) * self.line_space + 12)
        self.pos = (0.5 * width - 0.5 * self.dim[0], 0.5 * height - 0.5 * self.dim[1])
        self.surface = pygame.Surface(self.dim)
        self.surface.fill((0, 0, 0, 0))
        for n, line in enumerate(lines):
            text_texture = self.font.render(line, True, (255, 255, 255))
            self.surface.blit(text_texture, (22, n * self.line_space))
        self._render = False
        self.surface.set_alpha(220)

    def toggle(self):
        """Toggle help display on/off."""
        self._render = not self._render

    def render(self, display):
        """Render help text if enabled."""
        if self._render:
            display.blit(self.surface, self.pos)
