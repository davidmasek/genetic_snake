import tkinter as tk
from tkinter import ttk
import threading
from functools import partial
from .tree import *
from . import parser
# from tree import Evolution, Individual, Game, Entity, Population


class EvolutionWorker(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.evolution = Evolution()

    def stop(self):
        self.evolution.finished = True

    def add_population(self, population, generation):
        if generation % Evolution.PRINT_RATE == 0:
            self.app.table.add_population(population, generation)
        self._show_progress(100.0*generation/self.evolution.GENERATIONS)
        print(f"{generation};{population.get_avg_fitness()};{population.get_avg_score()};"
              f"{population.get_best().fitness};{population.get_best().score}")

    def log_time(self, d_time):
        pass

    def run(self):
        self.evolution.run(self)
        # finished
        self.app.running = False

    def _show_progress(self, value):
        self.app.progress_bar["value"] = value


class PopWindow(tk.Toplevel):
    def __init__(self, generation: int, pop: Population):
        super().__init__()
        self.wm_title("Generation {}".format(generation))

        self.canvas = tk.Canvas(self)
        self.frame = tk.Frame(self.canvas)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side="left", fill=tk.BOTH, expand=True)
        self.vsb.pack(side="right", fill=tk.Y)
        self.canvas.create_window((0, 0),
                                  window=self.frame,
                                  anchor=tk.NW,
                                  tags="self.frame")

        self.frame.bind("<Configure>", self.on_frame_configure)

        for y, individual in enumerate(pop.pop):
            l = tk.Label(
                self.frame,
                text="{:6.3f}".format(
                 individual.fitness,
                ),
            )
            l.grid(
                row=y,
                column=0,
                sticky=tk.W,
                padx=5,
                pady=5
            )
            b = tk.Button(
                self.frame,
                text="strategy",
                command=partial(Table.show_popup,
                                "Strategy",
                                individual.root.tree_string()),
                padx=5,
            )
            b.grid(
                row=y,
                column=1,
                sticky=tk.E,
                padx=5)

    @staticmethod
    def show(generation: int, pop: Population):
        PopWindow(generation, pop)

    def on_frame_configure(self, event):
        """
        Reset the scroll region to encompass the inner frame
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class GameWindow(tk.Toplevel):
    FRAME_DELAY = 33 # about 30 FPS
    # see http://www.science.smith.edu/dftwiki/index.php/File:TkInterColorCharts.png
    HEAD_COLOR = "green yellow"
    SNAKE_COLOR = "dark green"
    APPLE_COLOR = "firebrick3"
    WALL_COLOR = "dim gray"

    def __init__(self, generation: int, individual: Individual, w, h):
        super().__init__()
        self.wm_title("Generation {}".format(generation))
        self.score_label = ttk.Label(self, text="Score: {:2d}".format(0))
        self.score_label.pack(side="top", fill=tk.X, padx=10, expand=True)

        self.canvas = tk.Canvas(self, background="#000")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.quit_btn = ttk.Button(self,
                                   text="Quit",
                                   command=self.stop)
        self.quit_btn.pack()

        self.info_label = tk.Label(self)
        self.info_label.pack(padx=10,pady=10)

        self.protocol("WM_DELETE_WINDOW", self.stop)

        self.game = Game(h, w)
        self.turns = 0
        self.tile_size = 0
        self._render()

        self.worker = GameWorker(self, self.canvas, self.score_label, individual, w, h)
        self.worker.start()

    def stop(self):
        if self.worker.running:
            self.worker.stop()
            self.after(50, self.stop)
        else:
            self.destroy()

    def _render(self):
        # remove old elements - explicit delete needed
        self.canvas.delete(tk.ALL)

        self._show_score()
        # ?need update to get correct size
        # self.canvas.update()
        old_size = self.tile_size
        new_size = int(min(
            self.canvas.winfo_width() / self.game.width,
            self.canvas.winfo_height() / self.game.height
        ))
        if old_size != new_size:
            # @TODO: remove?
            # self.canvas.delete(tk.ALL)
            self.tile_size = new_size

        to_left = Rotation(Rotation.TO_LEFT).rotate(self.game.current_direction.type)
        to_right = Rotation(Rotation.TO_RIGHT).rotate(self.game.current_direction.type)
        none = Rotation(Rotation.NONE).rotate(self.game.current_direction.type)

        self.info_label["text"] = "" \
                                 "NONE     -> AHEAD: {} VISIBLE: {}\n" \
                                 f" NEARBY: {[Entity.TO_STR[e] for e in self.game.state[none][snake.NEARBY]]}\n" \
                                 "TO_LEFT  -> AHEAD: {} VISIBLE: {}\n" \
                                 f" NEARBY: {[Entity.TO_STR[e] for e in self.game.state[to_left][snake.NEARBY]]}\n" \
                                 "TO_RIGHT -> AHEAD: {} VISIBLE: {}\n" \
                                 f" NEARBY: {[Entity.TO_STR[e] for e in self.game.state[to_right][snake.NEARBY]]}\n" \
                                 "".format(
                    Entity.TO_STR[self.game.state[none][snake.AHEAD]],
                    Entity.TO_STR[self.game.state[none][snake.VISIBLE]],
                    Entity.TO_STR[self.game.state[to_left][snake.AHEAD]],
                    Entity.TO_STR[self.game.state[to_left][snake.VISIBLE]],
                    Entity.TO_STR[self.game.state[to_right][snake.AHEAD]],
                    Entity.TO_STR[self.game.state[to_right][snake.VISIBLE]],
        )

        for y, row in enumerate(self.game.grid):
            for x, col in enumerate(row):
                if col == Entity.EMPTY:
                    pass
                elif col == Entity.SNAKE:
                    self._draw_oval(x, y, self.SNAKE_COLOR)
                elif col == Entity.FOOD:
                    self._draw_oval(x, y, self.APPLE_COLOR)
                elif col == Entity.WALL:
                    self._draw_rect(x, y, self.WALL_COLOR)
                else:
                    raise ValueError("Unexpected value")

        self._draw_oval(self.game.head.x, self.game.head.y, self.HEAD_COLOR)

        self.after(self.FRAME_DELAY, self._render)

    def _draw_rect(self, x, y, color):
        self.canvas.create_rectangle(
            x * self.tile_size,
            y * self.tile_size,
            (x + 1) * self.tile_size,
            (y + 1) * self.tile_size,
            fill=color
        )

    def _draw_oval(self, x, y, color):
        self.canvas.create_oval(
            x * self.tile_size,
            y * self.tile_size,
            (x + 1) * self.tile_size,
            (y + 1) * self.tile_size,
            fill=color,
            tag="movable"
        )

    def _show_score(self):
        self.score_label["text"] = "Score: {:2d}, Turn: {:3d}".format(self.game.score, self.turns)

    @staticmethod
    def run_game(generation: int, individual: Individual, w=Game.WIDTH, h=Game.HEIGHT):
        GameWindow(generation, individual, w, h)


class GameWorker(threading.Thread):
    DELAY = 0.2
    # see http://www.science.smith.edu/dftwiki/index.php/File:TkInterColorCharts.png
    HEAD_COLOR = "green yellow"
    SNAKE_COLOR = "dark green"
    APPLE_COLOR = "firebrick3"
    WALL_COLOR = "dim gray"
    _SLEEP = 0.01

    def __init__(self, window: GameWindow, canvas: tk.Canvas, score: tk.Label, individual: Individual, w, h):
        super().__init__(daemon=True)
        self.w = w
        self.h = h
        self.running = True
        self.do_stop = False
        self.canvas = canvas
        self.score = score
        self.individual = individual
        self.turn = 0
        self.tile_size = 0
        self.window = window

    def stop(self):
        self.do_stop = True

    def run(self):
        game = Game(self.h, self.w)
        start_time = time.perf_counter()
        self.window.game = game
        while game.running and not self.do_stop:
            cur_time = time.perf_counter()
            if cur_time - start_time > self.DELAY:
                direction = self.individual.get_direction(game)
                game.move(direction)
                self.window.turns += 1
                self.turn += 1
                start_time = cur_time
            else:
                time.sleep(self._SLEEP)

        self.running = False


    @staticmethod
    def change_delay(value):
        GameWorker.DELAY = float(value)


class Application(tk.Frame):
    TITLE = "Snake"
    WIDTH = 1400
    HEIGHT = 600

    def __init__(self, master=None):
        super().__init__(master)
        self.running = False

        self.master.title(self.TITLE)
        self.master.minsize(400, 400)
        # self.master.maxsize(self.WIDTH, self.HEIGHT)
        # self.master.resizable(0, 0)
        self.master.geometry(str(self.WIDTH) + "x" + str(self.HEIGHT))
        self.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP)

        self.run_btn = tk.Button(
            self.top_frame,
            text="Evolve",
            command=self._toggle_run,
        )
        self.run_btn.pack()

        self.run_btn = tk.Button(
            self.top_frame,
            text="Load individual",
            command=self._load_individual,
        )
        self.run_btn.pack(padx=10)

        self.w_scale = tk.Scale(self.top_frame,
                                from_=8,
                                to=100,
                                orient=tk.HORIZONTAL,
                                resolution=1,
                                length=200,
                                label="game width (not evolution)")

        self.w_scale.set(Game.WIDTH)
        self.w_scale.pack(side=tk.LEFT)

        self.h_scale = tk.Scale(self.top_frame,
                                from_=6,
                                to=100,
                                orient=tk.HORIZONTAL,
                                resolution=1,
                                length=200,
                                label="game height (not evolution)")
        self.h_scale.set(Game.HEIGHT)
        self.h_scale.pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(
            self,
            orient="horizontal",
            length=300,
            mode='determinate',
        )
        self.progress_bar.pack()

        self.table = Table(self, self)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.input = tk.Frame(self)
        self.input.pack(side=tk.RIGHT, padx=20, pady=10)

        scale_l = 350
        self.scale = tk.Scale(self.input, from_=0, to=10, orient=tk.HORIZONTAL,
                          resolution=0.01, length=scale_l,
                          command=Evolution.change_mutation_rate,
                          label="mutation rate")
        self.scale.set(Evolution.BASE_MUTATION_RATE)
        self.scale.pack()

        self.scale = tk.Scale(self.input, from_=0, to=1, orient=tk.HORIZONTAL,
                          resolution=0.01, length=scale_l,
                          command=Evolution.change_crossover_rate,
                          label="crossover rate")
        self.scale.set(Evolution.CROSSOVER_RATE)
        self.scale.pack()

        self.scale = tk.Scale(self.input, from_=1, to=10, orient=tk.HORIZONTAL,
                          resolution=1, length=scale_l,
                          command=Evolution.change_restrict_depth,
                          label="tree depth restriction")
        self.scale.set(Evolution.RESTRICT_DEPTH)
        self.scale.pack()

        self.scale = tk.Scale(self.input, from_=0.01, to=2, orient=tk.HORIZONTAL,
                          resolution=0.01, length=scale_l,
                          command=GameWorker.change_delay,
                          label="game delay")
        self.scale.set(GameWorker.DELAY)
        self.scale.pack()

        self.scale = tk.Scale(self.input, from_=0.01, to=2, orient=tk.HORIZONTAL,
                          resolution=0.01, length=scale_l,
                          command=Evolution.change_mutation_chance,
                          label="mutation chance")
        self.scale.set(Evolution.MUTATION_CHANCE)
        self.scale.pack()

    def _toggle_run(self):
        if self.running:
            self.worker.stop()
        else:
            self.running = True
            self.table.reset()
            self.worker = EvolutionWorker(self)
            self.worker.start()

    def run_game(self, generation: int, individual: Individual):
        GameWindow.run_game(generation, individual, int(self.w_scale.get()), int(self.h_scale.get()))

    def _load_individual(self):
        ind = parser.load_dialog()
        if ind is not None:
            pop = Population()
            pop.append(ind)
            self.table.add_population(pop, "IMP", False)


class Table(tk.Frame):
    def __init__(self, root, app):
        super().__init__(master=root, borderwidth=1, relief=tk.SOLID)
        self.app = app
        self.canvas = tk.Canvas(self)  # background="#ffffff")
        self.frame = tk.Frame(self.canvas)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side="left", fill=tk.BOTH, expand=True)
        self.vsb.pack(side="right", fill=tk.Y)
        self.canvas.create_window((0, 0),
                                  window=self.frame,
                                  anchor=tk.NW,
                                  tags="self.frame")

        # self.frame.pack() # breaks layout

        self.frame.bind("<Configure>", self.on_frame_configure)

        self.row = 0
        tk.Grid.columnconfigure(self.frame, 0, weight=1)

    def reset(self):
        for l in self.frame.grid_slaves():
            l.destroy()

    def add_population(self, pop: Population, generation, show_all: bool = False):
        tk.Label(self.frame,
                 text="{}".format(generation),
                 width=3,
                 borderwidth="1",
                 relief="solid",
                 padx=5,
                 pady=2,
                 ).grid(row=self.row,
                        column=0,
                        sticky=tk.W,
                        padx=5)
        tk.Label(self.frame,
                 text=str(pop),
                 padx=5,
                 ).grid(row=self.row,
                        column=1,
                        sticky=tk.NSEW,
                        padx=10)
        tk.Button(self.frame, text="strategy",
                  command=partial(Table.show_popup,
                                  "Generation {} - Best strategy".format(generation),
                                  pop.get_best().root.tree_string()),
                  padx=5,
                  ).grid(row=self.row,
                         column=2,
                         sticky=tk.E,
                         padx=5)
        tk.Button(self.frame, text="run",
                  command=partial(self.app.run_game,
                                  generation,
                                  pop.get_best()),
                  padx=10,
                  ).grid(row=self.row,
                         column=3,
                         sticky=tk.E,
                         padx=5)
        if show_all:
            tk.Button(self.frame, text="show",
                      command=partial(PopWindow.show,
                                      generation,
                                      pop),
                      padx=10,
                      ).grid(row=self.row,
                             column=4,
                             sticky=tk.E,
                             padx=5)

        tk.Button(self.frame, text="save best",
                  command=partial(parser.save_dialog,
                                  pop.get_best()),
                  padx=10,
                  ).grid(row=self.row,
                         column=5,
                         sticky=tk.E)
        self.row += 1

    @staticmethod
    def show_popup(title, text):
        win = tk.Toplevel()
        win.wm_title(title)
        l = tk.Label(win, text=text, anchor="w", justify=tk.LEFT)
        l.pack(padx=10, pady=10)

    def on_frame_configure(self, event):
        """
        Reset the scroll region to encompass the inner frame
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

if __name__ == '__main__':
    # GameWorker.DELAY = 0.5
    #
    # root = Node(Function(Rotation(Rotation.NONE), snake.AHEAD, is_block, "block"))
    # root.left = Node(Rotation(Rotation.TO_RIGHT), root)
    # right = Node(Function(Rotation(Rotation.TO_LEFT), snake.VISIBLE, is_food, "food"), root)
    # root.right = right
    # right.left = Node(Rotation(Rotation.TO_LEFT), right)
    #
    # r2 = Node(Function(Rotation(Rotation.TO_RIGHT), snake.VISIBLE, is_food, "food"), right)
    # right.right = r2
    #
    # r2.left = Node(Rotation(Rotation.TO_RIGHT), r2)
    # r2.right = Node(Rotation(Rotation.NONE), r2)
    #
    # win = tk.Toplevel()
    # win.wm_title("strategy")
    # l = tk.Label(win, text=root.tree_string(), anchor="w", justify=tk.LEFT)
    # l.pack(padx=10, pady=10)
    #
    # g = GameWindow(10, Individual(root))
    # g.mainloop()

    app = Application()
    app.mainloop()