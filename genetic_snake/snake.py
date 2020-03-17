from random import randrange, choice
from collections import namedtuple

Point = namedtuple("Point", "x y")
AHEAD = "next"
VISIBLE = "visible"
NEARBY = "nearby"


class Direction:
    UP = 0
    LEFT = 1
    DOWN = 2
    RIGHT = 3
    TO_STR = {
        UP: "UP",
        LEFT: "LEFT",
        RIGHT: "RIGHT",
        DOWN: "DOWN",
    }
    TO_POINT = {
        UP: Point(0, -1),
        LEFT: Point(-1, 0),
        RIGHT: Point(1, 0),
        DOWN: Point(0, 1),
    }
    TO_LEFT = {
        UP: LEFT,
        LEFT: DOWN,
        RIGHT: UP,
        DOWN: RIGHT,
    }
    TO_RIGHT = {
        UP: RIGHT,
        LEFT: UP,
        RIGHT: DOWN,
        DOWN: LEFT,
    }

    def __init__(self, type: int):
        self.type = type
        self.point = Direction.TO_POINT[type]

    def turn_left_type(self):
        return Direction.TO_LEFT[self.type]

    def turn_right_type(self):
        return Direction.TO_RIGHT[self.type]

    def __str__(self):
        return Direction.TO_STR[self.type]


class Entity:
    EMPTY = 0
    WALL = 1
    FOOD = 2
    SNAKE = 3
    TO_STR = {
        EMPTY: "EMPTY",
        WALL: "WALL",
        FOOD: "FOOD",
        SNAKE: "SNAKE",
    }

    @staticmethod
    def random_type():
        return choice((Entity.EMPTY, Entity.WALL, Entity.FOOD, Entity.SNAKE))

    def __init__(self, type):
        self.type = type

    def __str__(self):
        return self.TO_STR[self.type]


class SnakeFragment:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Game:
    NEARBY_DISTANCE = 3
    WIDTH = 30
    HEIGHT = 20
    TO_MAP = {
        Entity.EMPTY: " ",
        Entity.WALL: "#",
        Entity.SNAKE: "X",
        Entity.FOOD: "F",
    }

    def __init__(self, height=HEIGHT, width=WIDTH):
        self.height = height
        self.width = width
        self.grid = []
        # default 2D array
        self.dir_map = [[Direction(Direction.RIGHT) for _ in range(width)] for _ in range(height)]
        self.score = 0
        self.running = True
        self.current_direction = Direction(Direction.RIGHT)
        for y in range(height):
            row = []
            for x in range(width):
                if y == 0 or y == height - 1 or x == 0 or x == width - 1:
                    row.append(Entity.WALL)
                else:
                    row.append(Entity.EMPTY)
            self.grid.append(row)

        start_x = int(width / 2)
        start_y = int(height / 2)
        self.head = SnakeFragment(start_x, start_y)
        self.grid[start_y][start_x] = Entity.SNAKE
        self.grid[start_y][start_x - 1] = Entity.SNAKE
        self.grid[start_y][start_x - 2] = Entity.SNAKE
        self.tail = SnakeFragment(start_x - 2, start_y)

        self.generate_apple()
        self.state = {Direction.UP: {}, Direction.DOWN: {}, Direction.LEFT: {}, Direction.RIGHT: {}}
        self._generate_state()

    def _generate_state(self):
        head_x = self.head.x
        head_y = self.head.y
        self.state[Direction.UP][AHEAD] = self.grid[head_y - 1][head_x]
        self.state[Direction.LEFT][AHEAD] = self.grid[head_y][head_x - 1]
        self.state[Direction.RIGHT][AHEAD] = self.grid[head_y][head_x + 1]
        self.state[Direction.DOWN][AHEAD] = self.grid[head_y + 1][head_x]

        self.state[Direction.UP][VISIBLE] = Entity.WALL
        self.state[Direction.LEFT][VISIBLE] = Entity.WALL
        self.state[Direction.RIGHT][VISIBLE] = Entity.WALL
        self.state[Direction.DOWN][VISIBLE] = Entity.WALL

        self.state[Direction.UP][NEARBY] = []
        self.state[Direction.LEFT][NEARBY] = []
        self.state[Direction.RIGHT][NEARBY] = []
        self.state[Direction.DOWN][NEARBY] = []

        # RIGHT
        found = False
        x = head_x + 1
        while x < Game.WIDTH:
            if self.grid[head_y][x] != Entity.EMPTY:
                if not found:
                    self.state[Direction.RIGHT][VISIBLE] = self.grid[head_y][x]
                    self.state[Direction.RIGHT][NEARBY].append(self.grid[head_y][x])
                    found = True
                elif abs(x - head_x) <= Game.NEARBY_DISTANCE:
                    self.state[Direction.RIGHT][NEARBY].append(self.grid[head_y][x])
            x += 1

        # LEFT
        x = head_x - 1
        found = False
        while x > 0:
            if self.grid[head_y][x] != Entity.EMPTY:
                if not found:
                    self.state[Direction.LEFT][VISIBLE] = self.grid[head_y][x]
                    self.state[Direction.LEFT][NEARBY].append(self.grid[head_y][x])
                    found = True
                elif abs(x - head_x) <= Game.NEARBY_DISTANCE:
                    self.state[Direction.LEFT][NEARBY].append(self.grid[head_y][x])
            x -= 1

        # DOWN
        y = head_y + 1
        found = False
        while y < Game.HEIGHT:
            if self.grid[y][head_x] != Entity.EMPTY:
                if not found:
                    self.state[Direction.DOWN][VISIBLE] = self.grid[y][head_x]
                    self.state[Direction.DOWN][NEARBY].append(self.grid[y][head_x])
                    found = True
                elif abs(y - head_y) <= Game.NEARBY_DISTANCE:
                    self.state[Direction.DOWN][NEARBY].append(self.grid[y][head_x])
            y += 1

        # UP
        y = head_y - 1
        found = False
        while y > 0:
            if self.grid[y][head_x] != Entity.EMPTY:
                if not found:
                    self.state[Direction.UP][VISIBLE] = self.grid[y][head_x]
                    self.state[Direction.UP][NEARBY].append(self.grid[y][head_x])
                    found = True
                elif abs(y - head_y) <= Game.NEARBY_DISTANCE:
                    self.state[Direction.UP][NEARBY].append(self.grid[y][head_x])
            y -= 1

    def move(self, direction_obj: Direction):
        self.current_direction = direction_obj
        direction = direction_obj.point
        # save the direction we moved
        self.dir_map[self.head.y][self.head.x] = self.current_direction
        self.head.y += direction.y
        self.head.x += direction.x
        collision_entity = self.grid[self.head.y][self.head.x]

        if collision_entity == Entity.WALL or collision_entity == Entity.SNAKE:
            if self.head.x != self.tail.x or self.head.y != self.tail.y:
                self.running = False
        if collision_entity == Entity.FOOD:
            self.score += 1
            self.generate_apple()
        else:
            self.grid[self.tail.y][self.tail.x] = Entity.EMPTY
            tail_direction = self.dir_map[self.tail.y][self.tail.x]
            self.tail.x += tail_direction.point.x
            self.tail.y += tail_direction.point.y
        # place head here to prevent position clearing when going to tail position
        self.grid[self.head.y][self.head.x] = Entity.SNAKE

        if self.running:
            self._generate_state()

    def print(self):
        """
        Print current grid state.
        """
        for row in self.grid:
            for col in row:
                print(self.TO_MAP[col], sep="", end="")
            print()

    def generate_apple(self):
        i = 0
        # random position
        while i < 20:
            y = randrange(1, self.height - 1)
            x = randrange(1, self.width - 1)
            if self.grid[y][x] == Entity.EMPTY:
                self.grid[y][x] = Entity.FOOD
                return
            i += 1
        # fallback to any position
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == Entity.EMPTY:
                    self.grid[y][x] = Entity.FOOD
                    return
        # no empty positions
        self.running = False


if __name__ == '__main__':
    g = Game(5, 6)
    while g.running:
        g.print()
        i = input()
        if i == "a":
            g.move(Direction(Direction.LEFT))
        elif i == "d":
            g.move(Direction(Direction.RIGHT))
        elif i == "s":
            g.move(Direction(Direction.DOWN))
        elif i == "w":
            g.move(Direction(Direction.UP))


