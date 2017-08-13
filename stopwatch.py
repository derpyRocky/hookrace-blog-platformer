from sdl2.ext import Color, FontManager, Renderer, Resources
from textbox import TextBox


class Stopwatch:
    def __init__(self, resources: Resources) -> None:
        self.ticks = -1
        self.last_finish = -1
        self.best_finish = -1

        font = FontManager(resources.get_path("DejaVuSans.ttf"), size=28)
        white = Color(r=255, g=255, b=255)
        self.timer_textbox = TextBox(font, 50, 100, white)
        self.best_time_textbox = TextBox(font, 50, 150, white)

    def reset(self) -> None:
        self.ticks = -1
        self.last_finish = -1

    def start(self) -> None:
        self.ticks = 0

    def stop(self) -> None:
        if self.ticks >= 0:
            self.last_finish = self.ticks
            self.ticks = -1
            if self.best_finish < 0 or self.last_finish < self.best_finish:
                self.best_finish = self.last_finish

    def step(self) -> None:
        if self.ticks >= 0:
            self.ticks += 1

    def render(self, renderer: Renderer) -> None:
        if self.ticks >= 0:
            self.timer_textbox.text = format_time_exact(self.ticks)
            self.timer_textbox.render(renderer)
        elif self.last_finish >= 0:
            self.timer_textbox.text = "Finished in: " + format_time_exact(self.last_finish)
            self.timer_textbox.render(renderer)
        if self.best_finish >= 0:
            self.best_time_textbox.text = " Best time: " + format_time_exact(self.best_finish)
            self.best_time_textbox.render(renderer)


def format_time(ticks: int) -> str:
    mins = int(int(ticks / 50) / 60)
    secs = int(ticks / 50) % 60
    #return f"{mins:02}:{secs:02}"
    return str(ticks)

def format_time_exact(ticks: int) -> str:
    cents = (ticks % 50) * 2
    #return f"{format_time(ticks)}:{cents:02}"
    return str(ticks)
