import sys
import sdl2.ext
from time import time
from sdl2.ext import Color, Renderer, Resources, Window
from basic2d import Point2d, Vector2d
from controller import Input, Controller
from stopwatch import Stopwatch

# Objective 4: Import Player from player module
# YOUR CODE HERE...

# Objective 5: Import Map and Tile from tilemap module
# YOUR CODE HERE...


UPDATES_PER_SECOND = 50
SECONDS_PER_UPDATE = 1.0 / UPDATES_PER_SECOND

# Objective 1: Create the title and size variables
WINDOW_SIZE = (1300,1600)
WINDOW_TITLE = "???"


class Game:
    def __init__(self, resources: Resources) -> None:
        self.camera = Vector2d(0, 0)
        self.stopwatch = Stopwatch(resources)

        # Objective 4: Create a Player
        # YOUR CODE HERE...

        # Objective 5: Create a Map
        # YOUR CODE HERE...

    def update(self, controller: Controller) -> None:
        if controller.has_input(Input.RESTART):
            self.stopwatch.reset()

            # Objective 4: Put the player back at the start
            # YOUR CODE HERE...

        # Objective 6: Call the player update method
        # YOUR CODE HERE...

        # Objective 7: Call the move_camera function with a focus on the player position
        # YOUR CODE HERE...

        # Objective 8: Update the stopwatch according to the player tile
        # YOUR CODE HERE...

    def render(self, renderer: Renderer) -> None:
        # Objective 4: Render the player
        # YOUR CODE HERE...

        # Objective 5: Render the tilemap
        # YOUR CODE HERE...

        self.stopwatch.render(renderer)


def move_camera(camera: Vector2d, focus: Point2d) -> None:
    # Objective 7: Find the correct value for half the window width
    # YOUR CODE HERE...
    half_win_width = 0

    # Objective 7: Uncomment and try out the different camera movements

    # 1. always in center:
    # camera.x = focus.x - half_win_width

    # 2. follow once leaves center:
    # left_area = focus.x - half_win_width - 100
    # right_area = focus.x - half_win_width + 100
    # camera.x = min(max(camera.x, left_area), right_area)

    # 3. fluid
    # dist = camera.x - focus.x + half_win_width
    # camera.x -= 0.05 * dist


def main() -> int:
    sdl2.ext.init()
    resources = Resources(__file__, "resources")
    controller = Controller()

    # Objective 1: Create and show the Window
    window = Window(WINDOW_TITLE, WINDOW_SIZE)
    window.show()
    # Objective 2: Create the Renderer with a background color
    renderer = Renderer(window)
    color = Color(255, 255, 255)
    renderer.color = color

    # Objective 3: Set up the game


    # Game Loop, draws each frame
    last_time = time()
    lag = 0.0
    while True:
        now = time()
        lag += now - last_time
        last_time = now

        controller.handle_input()
        if controller.has_input(Input.QUIT):
            break

        # Objective 3: Update the game the appropriate number of frames
      while lag >= SECONDS_PER_UPDATE:
          lag -= SECONDS_PER_UPDATE

        # Objective 2: Draw over all drawings of the last frame with the default color
        renderer.clear()

        # Objective 3: Render the game
        renderer.present()

        # Objective 2: Show the result on screen
        # YOUR CODE HERE...

    sdl2.ext.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
