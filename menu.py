import pygame

from starfield import Starfield

BG_PANEL = (16, 19, 30, 190)
BG_PANEL_SELECTED = (32, 40, 64, 220)
BORDER_SELECTED = (140, 190, 255)
TEXT = (218, 221, 230)
TEXT_DIM = (140, 145, 160)
TITLE_COLOR = (235, 238, 246)
START_COLOR = (150, 225, 180)
START_COLOR_SELECTED = (190, 255, 215)


class MenuOption:

    def __init__(self, key, label, choices, default_index=0, visible_if=None):
        self.key = key
        self.label = label
        self.choices = choices
        self.index = default_index
        self.visible_if = visible_if

    @property  # Encapsulation
    def value(self):
        return self.choices[self.index][1]

    @property  # Encapsulation
    def display(self):
        return self.choices[self.index][0]

    def cycle(self, direction):
        self.index = (self.index + direction) % len(self.choices)


class MainMenu:
    ROW_H = 52
    ROW_W = 620
    ROW_START_Y = 210

    def __init__(self, width=900, height=700):
        pygame.init()
        pygame.display.set_caption("Gravity Simulation")
        self.screen = pygame.display.set_mode((width, height))
        self.width, self.height = self.screen.get_size()
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("consolas", 32, bold=True)
        self.subtitle_font = pygame.font.SysFont("consolas", 14)
        self.label_font = pygame.font.SysFont("consolas", 17)
        self.value_font = pygame.font.SysFont("consolas", 17, bold=True)
        self.hint_font = pygame.font.SysFont("consolas", 13)
        self.start_font = pygame.font.SysFont("consolas", 20, bold=True)

        self.starfield = Starfield(self.width, self.height)
        self.frame_count = 0

        self.options = [
            MenuOption("scenario", "Scenario",
                       [("Solar System (accurate)", "solar"),
                        ("Random Cluster (Barnes-Hut demo)", "cluster")]),
            MenuOption("bodies", "Cluster body count",
                       [("50", 50), ("80", 80), ("150", 150), ("300", 300)],
                       default_index=1,
                       visible_if=lambda s: s["scenario"] == "cluster"),
            MenuOption("collisions", "Collisions",
                       [("Merge on impact", 0.0), ("Bounce (elastic)", 1.0)]),
            MenuOption("integrator", "Integrator",
                       [("Verlet (accurate)", "verlet"), ("Euler (simple)", "euler")]),
            MenuOption("barnes_hut", "Force calculation",
                       [("Direct (exact)", False),
                        ("Barnes-Hut (approximate, faster for many bodies)", True)]),
            MenuOption("fullscreen", "Display",
                       [("Fullscreen", True), ("Windowed", False)]),
        ]
        self.selected = 0
        self.start_hovered = False

    def _current_settings(self):
        return {o.key: o.value for o in self.options}

    def _visible_options(self):
        settings = self._current_settings()
        return [o for o in self.options if o.visible_if is None or o.visible_if(settings)]

    def _row_rect(self, row_index):
        x = self.width / 2 - self.ROW_W / 2
        y = self.ROW_START_Y + row_index * self.ROW_H
        return pygame.Rect(int(x), int(y), self.ROW_W, self.ROW_H - 10)

    def _start_button_rect(self, num_rows):
        y = self.ROW_START_Y + num_rows * self.ROW_H + 22
        return pygame.Rect(int(self.width / 2 - 110), int(y), 220, 48)

    def _handle_click(self, pos, visible):
        for i, option in enumerate(visible):
            rect = self._row_rect(i)
            if rect.collidepoint(pos):
                self.selected = i
                third = rect.width / 3
                if pos[0] - rect.x < third:
                    option.cycle(-1)
                elif pos[0] - rect.x > 2 * third:
                    option.cycle(1)
                return None
        if self._start_button_rect(len(visible)).collidepoint(pos):
            return self._current_settings()
        return None

    def run(self):
        while True:
            visible = self._visible_options()
            if self.selected >= len(visible):
                self.selected = len(visible) - 1

            mouse_pos = pygame.mouse.get_pos()
            self.start_hovered = self._start_button_rect(len(visible)).collidepoint(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_UP:
                        self.selected = (self.selected - 1) % len(visible)
                    elif event.key == pygame.K_DOWN:
                        self.selected = (self.selected + 1) % len(visible)
                    elif event.key == pygame.K_LEFT:
                        visible[self.selected].cycle(-1)
                    elif event.key == pygame.K_RIGHT:
                        visible[self.selected].cycle(1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return self._current_settings()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    result = self._handle_click(event.pos, visible)
                    if result is not None:
                        return result

            self._render(visible)
            pygame.display.flip()
            self.clock.tick(60)
            self.frame_count += 1

    def _render(self, visible):
        self.starfield.draw(self.screen)
        self.starfield.draw_twinkle(self.screen, self.frame_count)

        title = self.title_font.render("Gravity Simulation", True, TITLE_COLOR)
        self.screen.blit(title, title.get_rect(center=(self.width / 2, 110)))
        subtitle = self.subtitle_font.render(
            "An N-body gravity simulation - pick your scenario", True, TEXT_DIM)
        self.screen.blit(subtitle, subtitle.get_rect(center=(self.width / 2, 148)))

        for i, option in enumerate(visible):
            self._draw_row(option, i, i == self.selected)

        self._draw_start_button(len(visible))

        hint = self.hint_font.render(
            "Up/Down: select row     Left/Right or click arrows: change value     "
            "Enter or click Start: begin     Esc: quit", True, TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(self.width / 2, self.height - 28)))

    def _draw_row(self, option, index, is_selected):
        rect = self._row_rect(index)
        color = BG_PANEL_SELECTED if is_selected else BG_PANEL
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, color, panel.get_rect(), border_radius=8)
        if is_selected:
            pygame.draw.rect(panel, BORDER_SELECTED, panel.get_rect(), width=1, border_radius=8)
        self.screen.blit(panel, rect.topleft)

        label = self.label_font.render(option.label, True, TEXT)
        self.screen.blit(label, (rect.x + 20, rect.centery - label.get_height() / 2))

        value_color = TITLE_COLOR if is_selected else TEXT
        value_text = f"<  {option.display}  >" if is_selected else option.display
        value = self.value_font.render(value_text, True, value_color)
        self.screen.blit(value, value.get_rect(midright=(rect.right - 20, rect.centery)))

    def _draw_start_button(self, num_rows):
        rect = self._start_button_rect(num_rows)
        color = START_COLOR_SELECTED if self.start_hovered else START_COLOR
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*color, 45), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, color, panel.get_rect(), width=2, border_radius=10)
        self.screen.blit(panel, rect.topleft)
        label = self.start_font.render(">  Start", True, color)
        self.screen.blit(label, label.get_rect(center=rect.center))
