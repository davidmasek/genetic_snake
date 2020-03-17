from random import randrange, random, choice
import time
import math
import pickle
import operator
import copy
from typing import List, Tuple, Dict
from .snake import Entity, Game, Point, Direction
from . import snake


class Rotation:
    TO_LEFT = 0
    TO_RIGHT = 1
    NONE = 2
    TYPES = [TO_LEFT, TO_RIGHT, NONE]
    TO_STR = {
        TO_LEFT:  "LEFT",
        TO_RIGHT: "RIGHT",
        NONE:     "AHEAD"
    }

    def __init__(self, type):
        self.type = type

    def rotate(self, direction_type: int) -> int:
        if self.type == self.TO_LEFT:
            return Direction.TO_LEFT[direction_type]
        elif self.type == self.TO_RIGHT:
            return Direction.TO_RIGHT[direction_type]
        else:
            return direction_type

    def __str__(self):
        return self.TO_STR[self.type]

    @staticmethod
    def generate_random():
        return Rotation(choice(Rotation.TYPES))

    @staticmethod
    def is_terminal():
        return True


def is_block(entity):
    return entity == Entity.SNAKE or entity == Entity.WALL


def is_food(entity):
    return entity == Entity.FOOD


def is_snake(entity):
    return entity == Entity.SNAKE


def is_nearby_wall(entity_list):
    return Entity.WALL in entity_list


def is_nearby_snake(entity_list):
    return Entity.SNAKE in entity_list


def is_nearby_food(entity_list):
    return Entity.FOOD in entity_list


class Function:
    TYPES = [snake.AHEAD, snake.VISIBLE, snake.NEARBY]
    TYPES_STR = {snake.AHEAD: "IS", snake.VISIBLE: "VISIBLE", snake.NEARBY: "NEARBY"}
    IS_FUNCTIONS = [is_food, is_block, is_snake]
    NEARBY_FUNCTIONS = [is_nearby_wall, is_nearby_snake, is_nearby_food]
    FUNCTIONS_STR = {is_food: "FOOD", is_block: "BLOCK", is_snake: "SNAKE",
                     is_nearby_wall: "WALL", is_nearby_food: "FOOD",
                     is_nearby_snake: "SNAKE"}

    def __init__(self, rotation: Rotation, func_type, is_func, is_name: str):
        self.rotation = rotation
        self.func_type = func_type
        self.is_func = is_func
        self.is_name = is_name

    def __str__(self):
        return f"IF-{self.is_name}-{self.func_type}-{self.rotation}"

    def evaluate(self, game):
        dir_type = self.rotation.rotate(game.current_direction.type)
        return self.is_func(game.state[dir_type][self.func_type])

    @staticmethod
    def is_terminal():
        return False


class Generator:
    ROTATIONS = (
        Rotation.TO_LEFT,
        Rotation.TO_RIGHT,
        Rotation.NONE,
    )

    def generate_function(self):
        func_type = choice(Function.TYPES)
        if func_type == snake.NEARBY:
            is_func = choice(Function.NEARBY_FUNCTIONS)
        else:
            is_func = choice(Function.IS_FUNCTIONS)
        return Function(Rotation(choice(self.ROTATIONS)), func_type, is_func,
                        Function.FUNCTIONS_STR[is_func])


class Node:
    TERMINAL = 0
    FUNCTION = 1
    GEN = Generator()

    def __init__(self, data, parent=None):
        self.left = None
        self.right = None
        self.data = data
        self.parent = parent

    def evaluate(self, game):
        if self.data.is_terminal():
            return self.data
        elif self.data.evaluate(game):
            return self.left.evaluate(game)
        else:
            return self.right.evaluate(game)

    @staticmethod
    def generate_random(depth=0, parent=None):
        """
        Generate random tree with probabilistic-based tree creation.
        """
        if random() < (depth / Evolution.RESTRICT_DEPTH):
            return Node.generate_random_terminal_node(depth, parent)
        else:
            return Node.generate_random_function_node(depth, parent)

    @staticmethod
    def generate_random_terminal_node(depth, parent):
        return Node(Rotation.generate_random(), parent)

    @staticmethod
    def generate_random_function_node(depth, parent):
        n = Node(Node.GEN.generate_function(), parent)
        n.left = Node.generate_random(depth + 1, n)
        n.right = Node.generate_random(depth + 1, n)
        return n

    def print_tree(self, depth=0):
        if depth == 0:
            print(self.data)
        else:
            print('|' * (depth - 1), '-', self.data, sep='')
        if self.left is not None:
            self.left.print_tree(depth+1)
        if self.right is not None:
            self.right.print_tree(depth+1)

    def tree_string(self, depth=0):
        """
        Return string representation of used decision tree.
        """
        buffer = ""
        if depth > 0:
            buffer += "|" * (depth - 1) + "-"
        buffer += str(self.data) + '\n'
        if self.left is not None:
            buffer += self.left.tree_string(depth + 1)
        if self.right is not None:
            buffer += self.right.tree_string(depth + 1)
        return buffer

    def prune(self):
        """
        Remove redundant nodes. Works in-place.
        """
        if not self.data.is_terminal():
            if self.left.data.is_terminal() and self.right.data.is_terminal():
                left_type = self.left.data.type
                right_type = self.right.data.type
                if left_type == right_type:
                    self.data = self.left.data
                    self.left = None
                    self.right = None
                    if self.parent:
                        self.parent.prune()
            else:
                self.left.prune()
                # right can be deleted on parent pruning
                if self.right is not None:
                    self.right.prune()

    def mutate_if(self, depth=0):
        """
        Mutate nodes based on base rate and depth. Works in-place.
        Does subtree mutation.
        """
        if random() < Evolution.BASE_MUTATION_RATE * (depth + 1):
            # @TODO: continue mutating or break?
            self._mutate(depth)
            if random() > Evolution.MUTATION_CHANCE:
                return
        if self.left is not None:
            self.left.mutate_if(depth + 1)
        if self.right is not None:
            self.right.mutate_if(depth + 1)

    def _mutate(self, depth=0):
        # @TODO: how deep?
        replacement = Node.generate_random(depth, self.parent)
        self.data = replacement.data
        self.left = replacement.left
        self.right = replacement.right

    def crossover(self, other):
        """
        Crossover two trees. Switches two randomly selected subtrees.
        Works in-place.
        """
        first = []
        self.flatten(first)
        second = []
        other.flatten(second)

        first_node = choice(first)
        second_node = choice(second)
        self._switch_nodes(first_node, second_node)

    @staticmethod
    def _switch_nodes(first, second):
        second_data = second.data
        second_left = second.left
        second_right = second.right

        second.data = first.data
        second.left = first.left
        second.right = first.right

        first.data = second_data
        first.left = second_left
        first.right = second_right

    def flatten(self, container): # @TODO: container=[] and return?
        container.append(self)
        if self.left is not None:
            self.left.flatten(container)
        if self.right is not None:
            self.right.flatten(container)


class Individual:
    MAX_TURNS = 5000
    LOW_SCORE = 10
    MAX_TURNS_LOW = 500
    MAX_TURNS_ZERO = 100

    def __init__(self, root: Node):
        self.root = root
        self.fitness = 0
        self.score = 0
        self.turns = 0
        self.calculate_fitness()

    def calculate_fitness(self):
        result = self.run_game()
        # @TODO: ok?
        # self.fitness = result["score"]
        # @TODO: favor smaller trees?
        # self.fitness = result["score"] + (result["turns"] / self.MAX_TURNS)
        self.fitness = result["score"] + (result["score"] / result["turns"])

        self.score = result["score"]
        self.turns = result["turns"]

    def prune(self):
        self.root.prune()

    def mutate(self):
        # nodes = []
        # self.root.flatten(nodes)
        # random_node = choice(nodes)
        # random_node._mutate(3)

        self.root.mutate_if()

    def crossover(self, other):
        self.root.crossover(other.root)

    @staticmethod
    def is_block(entity):
        return entity == Entity.SNAKE or entity == Entity.WALL

    @staticmethod
    def is_food(entity):
        return entity == Entity.FOOD

    def get_direction(self, game: Game):
        rotation = self.root.evaluate(game)
        return Direction(rotation.rotate(game.current_direction.type))

    @staticmethod
    def _get_distance(game: Game, entity_validator, direction: Point):
        """"Return distance (from head) to given entity (wall, snake, food).
        Returns 1 for next tile. Return math.inf if not found.
        """
        distance = 1
        pos = [game.head.x + direction.x, game.head.y + direction.y]
        while True:
            # if (pos[0] == game.WIDTH or pos[1] == game.HEIGHT
            #         or pos[0] == -1 or pos[1] == -1):
            #     return math.inf
            # @TODO: changed to not look over things, ok?
            pos_entity = game.grid[pos[1]][pos[0]]
            if entity_validator(pos_entity):
                return distance
            elif pos_entity != Entity.EMPTY:
                return math.inf

            pos[0] += direction.x
            pos[1] += direction.y
            distance += 1

    def run_game(self) -> Dict[str, int]:
        """
        Run one game using own strategy.
        :return: score and number of turns taken
        """
        game = Game()
        turn = 0
        while game.running and turn < Individual.MAX_TURNS:
            if game.score == 0 and turn > Individual.MAX_TURNS_ZERO:
                break
            if game.score < Individual.LOW_SCORE and turn > Individual.MAX_TURNS_LOW:
                break
            direction = self.get_direction(game)
            game.move(direction)
            turn += 1

        return {"score": game.score, "turns": turn}

    def __deepcopy__(self, memodict={}):
        return pickle.loads(pickle.dumps(self, -1))


class Population:
    def __init__(self, start_size=0):
        self.pop = []  # type: List[Individual]
        for _ in range(start_size):
            i = Individual(Node.generate_random())
            i.prune()
            self.pop.append(i)

    def select_two(self) -> Tuple[Individual, Individual]:
        """
        Select two individuals with tournament selection. Returns copies.
        """
        tournament_size = int(Evolution.POPULATION_SIZE * Evolution.TOURNAMENT_SIZE)
        first = self._tournament_select(tournament_size)
        second = self._tournament_select(tournament_size)
        return copy.deepcopy(first), copy.deepcopy(second)

    def _tournament_select(self, tournament_size) -> Individual:
        best = choice(self.pop)
        for _ in range(tournament_size):
            cur = choice(self.pop)
            if cur.fitness > best.fitness:
                best = cur
        return best

    def get_best(self) -> Individual:
        return max(self.pop, key=operator.attrgetter('fitness'))

    def get_avg_fitness(self) -> float:
        return sum(i.fitness for i in self.pop) / len(self.pop)

    def get_avg_score(self) -> float:
        return sum(i.score for i in self.pop) / len(self.pop)

    def append(self, individual: Individual):
        self.pop.append(individual)

    def __str__(self):
        return "Average fitness: {:6.3f} (score: {:3.3f}) Best fitness: {:6.3f} (score: {:2d}, turns: {:3d})".format(
            self.get_avg_fitness(), self.get_avg_score(), self.get_best().fitness, self.get_best().score, self.get_best().turns
        )


class Evolution:
    RESTRICT_DEPTH = 6.0
    BASE_MUTATION_RATE = 0.05
    MUTATION_CHANCE = 0.05
    CROSSOVER_RATE = 0.05
    GENERATIONS = 80
    POPULATION_SIZE = 200
    MAX_RUNNING_TIME = 15000
    PRINT_RATE = 5
    TOURNAMENT_SIZE = 0.05

    @classmethod
    def change_mutation_rate(cls, value):
        Evolution.BASE_MUTATION_RATE = float(value)

    @classmethod
    def change_mutation_chance(cls, value):
        Evolution.MUTATION_CHANCE = float(value)

    @classmethod
    def change_crossover_rate(cls, value):
        Evolution.CROSSOVER_RATE = float(value)

    @classmethod
    def change_restrict_depth(cls, value):
        Evolution.RESTRICT_DEPTH = float(value)

    def __init__(self):
        self.finished = False

    def run(self, log_handler):
        start_time = time.time()
        population = Population(Evolution.POPULATION_SIZE)
        generation = 0
        log_handler.add_population(population, generation)
        for generation in range(1, Evolution.GENERATIONS + 1):
            if self.finished:
                break
            new_population = Population()

            new_population.append(copy.deepcopy(population.get_best()))

            while len(new_population.pop) < Evolution.POPULATION_SIZE:
                (first, second) = population.select_two()
                if random() < Evolution.CROSSOVER_RATE:
                    first.crossover(second)

                if random() < Evolution.MUTATION_CHANCE:
                    first.mutate()

                first.prune()
                first.calculate_fitness()
                new_population.append(first)
                if len(new_population.pop) < Evolution.POPULATION_SIZE:
                    if random() < Evolution.MUTATION_CHANCE:
                        second.mutate()
                    second.prune()
                    second.calculate_fitness()
                    new_population.append(second)

            population = new_population

            if (time.time() - start_time) > Evolution.MAX_RUNNING_TIME:
                self.finished = True

            log_handler.add_population(population, generation)

        log_handler.log_time(time.time() - start_time)


class LogHandler:
    def add_population(self, population, generation):
        print("population added")

    def log_time(self, d_time):
        pass


if __name__ == '__main__':
    Evolution.GENERATIONS = 10
    Evolution.POPULATION_SIZE = 100
    e = Evolution()
    e.run(LogHandler())
