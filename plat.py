import sys
import sdl2.ext
from math import sqrt
from time import time
from typing import List, Set, Tuple
from enum import Enum
from sdl2 import SDL_FLIP_NONE, SDL_FLIP_HORIZONTAL, SDL_KEYDOWN, SDL_KEYUP, SDL_QUIT, SDL_RENDERER_ACCELERATED, SDL_RENDERER_PRESENTVSYNC
from sdl2.ext import Color, FontManager, Renderer, Resources, SpriteFactory, TextureSprite, Window
from collections import namedtuple

Rect = namedtuple("Rect", ["x", "y", "w", "h"])


BodyPart = namedtuple("BodyPart", ["source", "dest", "flip"])


class Point2d:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __sub__(self, other):
        return Point2d(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        return Point2d(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Point2d(self.x * scalar, self.y * scalar)

    def len(self):
        return sqrt(self.x * self.x + self.y * self.y)

Vector2d = Point2d


class Input(Enum):
    NONE = 1
    LEFT = 2
    RIGHT = 3
    JUMP = 4
    RESTART = 5
    QUIT = 6


class Time:
    def __init__(self):
        self.begin = -1
        self.finish = -1
        self.best = -1


class CacheLine:
    def __init__(self, texture: TextureSprite, w: int, h: int) -> None:
        self.texture = texture
        self.w = w
        self.h = h


class TextCache:
    def __init__(self):
        self.text = ""
        self.cache = None  # type: CacheLine


class Player:
    def __init__(self, texture: TextureSprite) -> None:
        self.texture = texture
        self.time = Time()
        self.pos = None  # type: Point2d
        self.vel = None  # type: Vector2d
        self.restart()

    def restart(self):
        self.pos = Point2d(170, 500)
        self.vel = Vector2d(0, 0)
        self.time.begin = -1
        self.time.finish = -1


class Collision(Enum):
    X = 1
    Y = 2
    CORNER = 3

TILES_PER_ROW = 16
TILE_SIZE = Point2d(64, 64)
PLAYER_SIZE = Point2d(64, 64)
WINDOW_SIZE = Point2d(1280, 720)

AIR = 0
START = 78
FINISH = 110


class Map:
    def __init__(self, texture: TextureSprite, file_name: str) -> None:
        self.texture = texture
        self.tiles = []  # type: List[int]
        self.width = 0
        self.height = 0

        file = open(file_name, "r")
        for line in file.readlines():
            width = 0
            for word in line.split(' '):
                if word == "":
                    continue
                value = int(word)
                self.tiles.append(value)
                width += 1

            if self.width > 0 and self.width != width:
                raise RuntimeError("Incompatible line length in map " + file_name)
            self.width = width
            self.height += 1

    def __get_tile(self, x: int, y: int) -> int:
        nx = min(max(int(x / TILE_SIZE.x), 0), self.width - 1)
        ny = min(max(int(y / TILE_SIZE.y), 0), self.height - 1)
        pos = ny * self.width + nx
        return self.tiles[pos]

    def get_tile(self, pos: Point2d) -> int:
        return self.__get_tile(int(round(pos.x)), int(round(pos.y)))

    def __is_solid(self, x: int, y: int) -> bool:
        return self.__get_tile(x, y) not in {AIR, START, FINISH}

    def is_solid(self, pos: Point2d) -> bool:
        return self.__is_solid(int(round(pos.x)), int(round(pos.y)))

    def on_ground(self, pos: Point2d, size: Vector2d) -> bool:
        size = size * 0.5
        return (self.is_solid(Point2d(pos.x - size.x, pos.y + size.y + 1)) or
                self.is_solid(Point2d(pos.x + size.x, pos.y + size.y + 1)))

    def test_box(self, pos: Point2d, size: Vector2d) -> bool:
        size = size * 0.5
        return (
            self.is_solid(Point2d(pos.x - size.x, pos.y - size.y)) or
            self.is_solid(Point2d(pos.x + size.x, pos.y - size.y)) or
            self.is_solid(Point2d(pos.x - size.x, pos.y + size.y)) or
            self.is_solid(Point2d(pos.x + size.x, pos.y + size.y))
        )

    def move_box(self, pos: Point2d, vel: Vector2d, size: Vector2d) -> Tuple[Set[Collision], Point2d, Point2d]:
        distance = vel.len()
        maximum = int(distance)

        result = set()  # type: Set[Collision]
        if distance < 0:
            return result, pos, vel

        fraction = 1.0 / float(maximum + 1)

        for i in range(0, maximum + 1):
            new_pos = pos + vel * fraction
            if self.test_box(new_pos, size):
                hit = False
                if self.test_box(Point2d(pos.x, new_pos.y), size):
                    result.add(Collision.Y)
                    new_pos.y = pos.y
                    vel.y = 0
                    hit = True

                if self.test_box(Point2d(new_pos.x, pos.y), size):
                    result.add(Collision.X)
                    new_pos.x = pos.x
                    vel.x = 0
                    hit = True

                if not hit:
                    result.add(Collision.CORNER)
                    new_pos = pos
                    vel = Vector2d(0, 0)

            pos = new_pos

        return result, pos, vel


class Game:
    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer

        self.inputs = {
            Input.NONE: False,
            Input.LEFT: False,
            Input.RIGHT: False,
            Input.JUMP: False,
            Input.RESTART: False,
            Input.QUIT: False
        }

        # load resources
        resources = Resources(__file__, "resources")
        self.font = FontManager(resources.get_path("DejaVuSans.ttf"), size=28)
        factory = SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
        self.player = Player(factory.from_image(resources.get_path("player.png")))
        self.map = Map(factory.from_image(resources.get_path("grass.png")),
                       resources.get_path("default.map"))
        self.camera = Vector2d(0, 0)
        self.tc_timer = TextCache()
        self.tc_best_time = TextCache()

    def handle_input(self) -> None:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == SDL_QUIT:
                self.inputs[Input.QUIT] = True
            elif event.type == SDL_KEYDOWN:
                self.inputs[to_input(event.key.keysym.sym)] = True
            elif event.type == SDL_KEYUP:
                self.inputs[to_input(event.key.keysym.sym)] = False

    def physics(self) -> None:
        if self.inputs[Input.RESTART]:
            self.player.restart()

        ground = self.map.on_ground(self.player.pos, PLAYER_SIZE)

        if self.inputs[Input.JUMP]:
            if ground:
                self.player.vel.y = -21

        direction = ((1 if self.inputs[Input.RIGHT] else 0)
                     - (1 if self.inputs[Input.LEFT] else 0))

        self.player.vel.y += 0.75  # gravity
        if ground:
            self.player.vel.x = 0.5 * self.player.vel.x + 4.0 * direction
        else:
            self.player.vel.x = 0.95 * self.player.vel.x + 2.0 * direction
        self.player.vel.x = min(max(self.player.vel.x, -8), 8)

        collisions, self.player.pos, self.player.vel = self.map.move_box(
            self.player.pos, self.player.vel, PLAYER_SIZE
        )
        # self.player.pos += self.player.vel

    def move_camera(self) -> None:
        half_win = WINDOW_SIZE.x / 2
        # 1. always in center:
        # self.camera.x = self.player.pos.x - half_win
        # 2. follow once leaves center:
        left_area = self.player.pos.x - half_win - 100
        right_area = self.player.pos.x - half_win + 100
        self.camera.x = min(max(self.camera.x, left_area), right_area)
        # 3. fluid
        dist = self.camera.x - self.player.pos.x + half_win
        # self.camera.x -= 0.05 * dist

    def logic(self, tick: int) -> None:
        player_time = self.player.time
        player_tile = self.map.get_tile(self.player.pos)
        if player_tile == START:
            player_time.begin = tick
        elif player_tile == FINISH:
            if player_time.begin >= 0:
                player_time.finish = tick - player_time.begin
                player_time.begin = -1
                if player_time.best < 0 or player_time.finish < player_time.best:
                    player_time.best = player_time.finish

    def __render_text(self, text: str, x: int, y: int, color: Color, tc: TextCache):
        if text != tc.text:
            # TODO: tc.cache.texture.destroy()
            tc.cache = render_text(self.renderer, self.font, text, color)
            tc.text = text

        source = Rect(0, 0, tc.cache.w, tc.cache.h)
        dest = Rect(x, y, tc.cache.w, tc.cache.h)
        self.renderer.copy(tc.cache.texture, source, dest, angle=0, center=None, flip=SDL_FLIP_NONE)

    def render(self, tick: int) -> None:
        # Draw over all drawings of the last frame with the default color
        self.renderer.clear()
        # Actual drawing here
        render_tee(
            self.renderer, self.player.texture,
            self.player.pos - self.camera)
        render_map(self.renderer, self.map, self.camera)

        player_time = self.player.time
        white = Color(255, 255, 255)
        if player_time.begin >= 0:
            self.__render_text(format_time_exact(tick - player_time.begin), 50, 100, white, self.tc_timer)
        elif player_time.finish >= 0:
            self.__render_text("Finished in: " + format_time_exact(player_time.finish), 50, 100, white, self.tc_timer)
        if player_time.best >= 0:
            self.__render_text("Best time: " + format_time_exact(player_time.best), 50, 150, white, self.tc_best_time)

        # Show the result on screen
        self.renderer.present()


def format_time(ticks: int) -> str:
    mins = int(int(ticks / 50) / 60)
    secs = int(ticks / 50) % 60
    return f"{mins:02}:{secs:02}"


def format_time_exact(ticks: int) -> str:
    cents = (ticks % 50) * 2
    return f"{format_time(ticks)}:{cents:02}"


def render_tee(renderer: Renderer, texture: TextureSprite,
               pos: Point2d):
    x = int(pos.x)
    y = int(pos.y)

    body_parts = [
        BodyPart(Rect(192, 64, 64, 32), Rect(x - 60, y, 96, 48),
                 SDL_FLIP_NONE),  # back feet shadow
        BodyPart(Rect(96, 0, 96, 96), Rect(x - 48, y - 48, 96, 96),
                 SDL_FLIP_NONE),  # body shadow
        BodyPart(Rect(192, 64, 64, 32), Rect(x - 36, y, 96, 48),
                 SDL_FLIP_NONE),  # front feet shadow
        BodyPart(Rect(192, 32, 64, 32), Rect(x - 60, y, 96, 48),
                 SDL_FLIP_NONE),  # back feet
        BodyPart(Rect(0, 0, 96, 96), Rect(x - 48, y - 48, 96, 96),
                 SDL_FLIP_NONE),  # body
        BodyPart(Rect(192, 32, 64, 32), Rect(x - 36, y, 96, 48),
                 SDL_FLIP_NONE),  # front feet
        BodyPart(Rect(64, 96, 32, 32), Rect(x - 18, y - 21, 36, 36),
                 SDL_FLIP_NONE),  # left eye
        BodyPart(Rect(64, 96, 32, 32), Rect(x - 6, y - 21, 36, 36),
                 SDL_FLIP_HORIZONTAL)  # right eye
    ]
    for part in body_parts:
        renderer.copy(texture, part.source, part.dest, angle=0.0,
                      center=None, flip=part.flip)


def render_map(renderer: Renderer, map: Map, camera: Vector2d):
    for i, tile_nr in enumerate(map.tiles):
        if tile_nr == 0:
            continue
        clip_x = (tile_nr % TILES_PER_ROW) * TILE_SIZE.x
        clip_y = int(tile_nr / TILES_PER_ROW) * TILE_SIZE.y
        dest_x = (i % map.width) * TILE_SIZE.x - int(camera.x)
        dest_y = int(i / map.width) * TILE_SIZE.y - int(camera.y)

        clip = Rect(clip_x, clip_y, TILE_SIZE.x, TILE_SIZE.y)
        dest = Rect(dest_x, dest_y, TILE_SIZE.x, TILE_SIZE.y)
        renderer.copy(map.texture, clip, dest)


def render_text(
        renderer: Renderer, font: FontManager,
        text: str, color: Color) -> CacheLine:
    surface = font.render(text, color=color)
    # TODO: surface.setSurfaceAlphaMod

    width = surface.w
    height = surface.h
    factory = SpriteFactory(sdl2.ext.TEXTURE, renderer=renderer)
    texture = factory.from_surface(surface, free=True)

    return CacheLine(texture, width, height)


def to_input(key):
    if key == sdl2.SDLK_a:
        return Input.LEFT
    elif key == sdl2.SDLK_d:
        return Input.RIGHT
    elif key == sdl2.SDLK_SPACE:
        return Input.JUMP
    elif key == sdl2.SDLK_r:
        return Input.RESTART
    elif key == sdl2.SDLK_q:
        return Input.QUIT
    else:
        return Input.NONE


def main() -> int:
    sdl2.ext.init()

    window = Window("Our own 2D platformer", size=(WINDOW_SIZE.x, WINDOW_SIZE.y))
    window.show()

    renderer = Renderer(
        window,
        index=-1,
        flags=SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC
    )

    renderer.color = Color(r=110, g=132, b=174)

    game = Game(renderer)

    start_time = time()
    last_tick = 0
    # Game loop, draws each frame
    while not game.inputs[Input.QUIT]:
        game.handle_input()

        new_tick = int((time() - start_time) * 50)
        for tick in range(last_tick + 1, new_tick + 1):
            game.physics()
            game.move_camera()
            game.logic(tick)
        last_tick = new_tick

        game.render(last_tick)

    sdl2.ext.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
