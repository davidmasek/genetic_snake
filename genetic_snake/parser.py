import os.path
from tkinter.filedialog import askopenfilename, asksaveasfilename
from .tree import *

FILENAME = "individual_"


def generate_filename() -> str:
    i = 0
    filename = FILENAME + str(i)
    while os.path.exists(filename):
        i += 1
        filename = FILENAME + str(i)
    return filename


def load_dialog() -> Individual:
    filename = askopenfilename()
    if not os.path.isfile(filename):
        print(f"{filename} not found")
        return None
    return load(filename)


def save_dialog(ind: Individual):
    default_name = generate_filename()
    filename = asksaveasfilename(initialfile=default_name)
    if not filename:
        return None
    save(ind, filename)


def load(filename: str) -> Individual:
    with open(filename, 'rb') as handle:
        return pickle.load(handle)


def save(ind: Individual, filename: str):
    with open(filename, 'wb') as handle:
        pickle.dump(ind, handle, protocol=pickle.HIGHEST_PROTOCOL)



if __name__ == '__main__':
    node = Node.generate_random()
    ind = Individual(node)
    save_dialog(ind)
    loaded: Individual = load_dialog()
    if loaded is not None:
        loaded.root.print_tree()

    # parse_input(node.tree_string())