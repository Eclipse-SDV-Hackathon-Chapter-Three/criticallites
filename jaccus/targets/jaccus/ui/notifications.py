#!/usr/bin/env python

"""
Notification system implementation.
"""

import pygame
from ..core.config import Config


class FadingText(object):
    """Text that fades out over time."""

    def __init__(self, font, dim, pos):
        self.font = font
        self.dim = dim
        self.pos = pos
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)

    def set_text(self, text, color=(255, 255, 255), seconds=Config.NOTIFICATION_DEFAULT_DURATION):
        """Set the text to display with fade effect."""
        text_texture = self.font.render(text, True, color)
        self.surface = pygame.Surface(self.dim)
        self.seconds_left = seconds
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(text_texture, (10, 11))

    def tick(self, _, clock):
        """Update the fade effect each frame."""
        delta_seconds = 1e-3 * clock.get_time()
        self.seconds_left = max(0.0, self.seconds_left - delta_seconds)
        self.surface.set_alpha(Config.NOTIFICATION_FADE_RATE * self.seconds_left)

    def render(self, display):
        """Render the fading text to the display."""
        display.blit(self.surface, self.pos)


class NotificationManager:
    """Manages all notification display."""

    def __init__(self, font, width, height):
        self.notifications = FadingText(font, (width, 40), (0, height - 40))

    def show(self, text, color=(255, 255, 255), seconds=Config.NOTIFICATION_DEFAULT_DURATION):
        """Show a notification."""
        self.notifications.set_text(text, color, seconds)

    def show_error(self, text):
        """Show an error notification."""
        self.notifications.set_text(f'Error: {text}', (255, 0, 0))

    def tick(self, world, clock):
        """Update notifications each frame."""
        self.notifications.tick(world, clock)

    def render(self, display):
        """Render notifications to display."""
        self.notifications.render(display)
