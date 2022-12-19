import random
import cellular
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import sys

class QLearn:
    def __init__(self, actions, epsilon=0.1, alpha=0.2, gamma=0.9):
        self.q = {}

        self.epsilon = epsilon  # exploration constant
        self.alpha = alpha      # discount constant
        self.gamma = gamma
        self.actions = actions

    def getQ(self, state, action):
        return self.q.get((state, action), 0.0)
        # return self.q.get((state, action), 1.0)

    def learnQ(self, state, action, reward, value):
        '''
        Q-learning: Q(s, a) += alpha * (reward(s,a) + max(Q(s') - Q(s,a))
        '''
        oldv = self.q.get((state, action), None)
        if oldv is None:
            self.q[(state, action)] = reward
        else:
            self.q[(state, action)] = oldv + self.alpha * (value - oldv)

    def chooseAction(self, state):
        if random.random() < self.epsilon:
            action = random.choice(self.actions)
        else:
            q = [self.getQ(state, a) for a in self.actions]
            maxQ = max(q)
            count = q.count(maxQ)
            # In case there're several state-action max values 
            # we select a random one among them
            if count > 1:
                best = [i for i in range(len(self.actions)) if q[i] == maxQ]
                i = random.choice(best)
            else:
                i = q.index(maxQ)

            action = self.actions[i]
        return action

    def learn(self, state1, action1, reward, state2):
        maxqnew = max([self.getQ(state2, a) for a in self.actions])
        self.learnQ(state1, action1, reward, reward + self.gamma*maxqnew)

directions = 8

lookdist = 2
lookcells = []
for i in range(-lookdist,lookdist+1):
    for j in range(-lookdist,lookdist+1):
        if (abs(i) + abs(j) <= lookdist) and (i != 0 or j != 0):
            lookcells.append((i,j))

def pickRandomLocation():
    while 1:
        x = random.randrange(world.width)
        y = random.randrange(world.height)
        cell = world.getCell(x, y)
        if not (cell.wall or len(cell.agents) > 0):
            return cell


class Cell(cellular.Cell):
    wall = False

    def colour(self):
        if self.wall:
            return 'black'
        else:
            return 'white'

    def load(self, data):
        if data == 'X':
            self.wall = True
        else:
            self.wall = False


class Cat(cellular.Agent):
    cell = None
    score = 0
    colour = 'red'

    def update(self):
        cell = self.cell
        if cell != mouse.cell:
            self.goTowards(mouse.cell)
            while cell == self.cell:
                self.goInDirection(random.randrange(directions))


class Cheese(cellular.Agent):
    colour = 'green'

    def update(self):
        pass

class OriginalMouse(cellular.Agent):
    colour = 'gray'

    def __init__(self):
        self.ai = None
        self.ai = QLearn(actions=range(directions),
                                alpha=0.1, gamma=0.9, epsilon=0.1)
        self.eaten = 0
        self.fed = 0
        self.lastState = None
        self.lastAction = None

    def update(self):
        # calculate the state of the surrounding cells
        state = self.calcState()
        # asign a reward of -1 by default
        reward = -1

        # observe the reward and update the Q-value
        if self.cell == cat.cell:
            self.eaten += 1
            reward = -100
            if self.lastState is not None:
                self.ai.learn(self.lastState, self.lastAction, reward, state)
            self.lastState = None

            self.cell = pickRandomLocation()
            return

        if self.cell == cheese.cell:
            self.fed += 1
            reward = 50
            cheese.cell = pickRandomLocation()

        if self.lastState is not None:
            self.ai.learn(self.lastState, self.lastAction, reward, state)

        # Choose a new action and execute it
        state = self.calcState()
        # print(state)
        action = self.ai.chooseAction(state)
        self.lastState = state
        self.lastAction = action

        self.goInDirection(action)

    def calcState(self):
        def cellvalue(cell):
            if cat.cell is not None and (cell.x == cat.cell.x and
                                         cell.y == cat.cell.y):
                return 3
            elif cheese.cell is not None and (cell.x == cheese.cell.x and
                                              cell.y == cheese.cell.y):
                return 2
            else:
                return 1 if cell.wall else 0

        return tuple([cellvalue(self.world.getWrappedCell(self.cell.x + j, self.cell.y + i))
                      for i,j in lookcells])

class ImprovedMouse(cellular.Agent):
    colour = 'gray'

    def __init__(self):
        self.ai = None
        self.ai = QLearn(actions=range(directions),
                                alpha=0.1, gamma=0.9, epsilon=0.1)
        self.eaten = 0
        self.fed = 0
        self.lastState = None
        self.lastAction = None
        self.fed_reward = 50
        self.eaten_reward = -100

        self.graph = None
        self.shortest_path_changed = True
        self.directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]
        
    def createGraph(self):
        self.graph = nx.Graph()
        for row_of_cells in self.world.grid:
            for cell in row_of_cells:
                if not cell.wall:
                    new_node = self.cellToNode(cell)
                    self.graph.add_node(new_node)

                    for x_dir, y_dir in [(-1, 0), (-1, -1), (0, -1), (1, -1)]:
                        existing_cell = self.getCell(cell.x + x_dir, cell.y + y_dir)
                        if existing_cell:
                            self.graph.add_edge(new_node, self.cellToNode(existing_cell))

        # uncomment to plot the game grid as a graph
        #_, axis = plt.subplots(figsize=(15, 15))
        #nx.draw(self.graph, ax=axis, pos=nx.spring_layout(self.graph), with_labels=True)
        #plt.show()
    
    def cellToNode(_, cell):
        return (cell.x, cell.y)
    
    def nodeToCell(self, node):
        return self.world.grid[node[1]][node[0]]

    def getCell(self, x, y):
        if x < 0 or y < 0 or y >= len(world.grid) or x >= len(world.grid[y]):
            return None
        
        cell = world.grid[y][x]
        if cell.wall:
            return None
        
        return cell

    def update(self):
        if not self.graph:
            self.createGraph()

        if self.shortest_path_changed:
            self.shortest_path = nx.shortest_path(self.graph, self.cellToNode(self.cell), self.cellToNode(cheese.cell))
            self.shortest_path.reverse()
            self.shortest_path.pop()
            self.shortest_path_changed = False

        self.shortest_path_changed = True
        if self.cell == cheese.cell:
            self.fed += 1
            cheese.cell = pickRandomLocation()
        elif self.cell == cat.cell:
            self.eaten += 1
            self.cell = pickRandomLocation()
        elif (nx.shortest_path_length(self.graph, self.cellToNode(self.cell), self.cellToNode(cat.cell)) < 3 and 
              nx.shortest_path_length(self.graph, self.cellToNode(self.cell), self.cellToNode(cheese.cell)) > 1):
            self.moveAwayFromCat()
        else:
            self.cell = self.nodeToCell(self.shortest_path.pop())
            self.shortest_path_changed = False
    
    def moveAwayFromCat(self):
        current_cell = self.cell
        escape_cells = [[] for _ in range(4)]
        best_cat_distance = 0

        for x_dir, y_dir in self.directions:
            cell = self.getCell(current_cell.x + x_dir, current_cell.y + y_dir)
            if cell:
                self.cell = cell
                cat_distance = nx.shortest_path_length(self.graph, self.cellToNode(self.cell), self.cellToNode(cat.cell))
                if cat_distance >= best_cat_distance:
                    best_cat_distance = cat_distance
                    escape_cells[best_cat_distance].append(cell)

        best_escape_cell = current_cell
        best_cheese_distance = sys.maxsize
        for escape_cell in escape_cells[best_cat_distance]:
            distance_to_cheese = nx.shortest_path_length(self.graph, self.cellToNode(escape_cell), self.cellToNode(cheese.cell))
            if distance_to_cheese < best_cheese_distance:
                best_cheese_distance = distance_to_cheese
                best_escape_cell = escape_cell

        self.cell = best_escape_cell

    def calcState(self):
        def cellvalue(cell):
            if cat.cell is not None and (cell.x == cat.cell.x and
                                         cell.y == cat.cell.y):
                return 3
            elif cheese.cell is not None and (cell.x == cheese.cell.x and
                                              cell.y == cheese.cell.y):
                return 2
            else:
                return 1 if cell.wall else 0

        return tuple([cellvalue(self.world.getWrappedCell(self.cell.x + j, self.cell.y + i))
                      for i,j in lookcells])

RUNS = 100_000
STATS_COLLECTION = 10_000
STATS_LEN = RUNS // STATS_COLLECTION

for world_filename, world_name in [("world_empty.txt", "Empty world"), ("world_walls.txt", "World with walls")]:
    world_stats = [None, None]
    for j, (mouse, mouse_name) in enumerate([(OriginalMouse(), "Q-learning mouse"), (ImprovedMouse(), "Improved mouse")]):
        print(f"\n{world_name}, {mouse_name}:")
        cat = Cat()
        cheese = Cheese()
        world = cellular.World(Cell, directions=directions, filename=world_filename)
        world.age = 0

        world.addAgent(cheese, cell=pickRandomLocation())   # assign random cell, otherwise agent can be spawned into a wall
        world.addAgent(cat, cell=pickRandomLocation())      # assign random cell, otherwise agent can be spawned into a wall
        world.addAgent(mouse, cell=pickRandomLocation())    # assign random cell, otherwise agent can be spawned into a wall

        stats = np.zeros((3, STATS_LEN))
        endAge = world.age + RUNS
        idx = 0
        while world.age < endAge:
            world.update()

            if world.age % STATS_COLLECTION == 0:
                print ("{:d}, e: {:0.2f}, W: {:d}, L: {:d}".format(world.age, mouse.ai.epsilon, mouse.fed, mouse.eaten))
                stats[0][idx] = mouse.fed
                stats[1][idx] = mouse.eaten
                stats[2][idx] = mouse.fed + mouse.eaten
                idx += 1

                mouse.eaten = 0
                mouse.fed = 0
        world_stats[j] = (stats, mouse_name)
    
    figure, axis = plt.subplots(2, 2)
    figure.set_size_inches(12, 10)
    figure.suptitle(f"Absolute statistics of {STATS_LEN} runs per {STATS_COLLECTION} updates in world {world_name}")
    lables = ["fed", "eaten", "games"]
    x_positions = [0, 1, 2]
    colors = ['m', 'c']
    for i in range(2):
        heights = world_stats[i][0].mean(axis=1)
        height_offset = heights.max() / 100
        axis[0, i].bar(lables, heights, width=0.5, color=colors[i])
        axis[0, i].set_title(f"{world_stats[i][1]} - mean")
        axis[0, i].set_yticks([], [])
        axis[0, i].set_frame_on(False)
        for count, x_pos in zip(heights, x_positions):
            axis[0, i].annotate(f"{count:.2f}", (x_pos, count + height_offset), ha="center")

        heights = world_stats[i][0].std(axis=1)
        height_offset = heights.max() / 100
        axis[1, i].bar(lables, heights, width=0.5, color=colors[i])
        axis[1, i].set_title(f"{world_stats[i][1]} - stddev")
        axis[1, i].set_yticks([], [])
        axis[1, i].set_frame_on(False)
        for count, x_pos in zip(heights, x_positions):
            axis[1, i].annotate(f"{count:.2f}", (x_pos, count + height_offset), ha="center")
    plt.show()
    
    figure, axis = plt.subplots(2, 2)
    figure.set_size_inches(12, 10)
    figure.suptitle(f"Relative statistics of {STATS_LEN} runs per {STATS_COLLECTION} updates in world {world_name}")
    lables = ["fed", "eaten", "updates per games"]
    x_positions = [0, 1, 2]
    colors = ['m', 'c']

    world_relative_stats = []
    for i in range(2):
        stats = np.zeros_like(world_stats[i][0])
        stats[:2, :] = world_stats[i][0][:2, :] / world_stats[i][0][2, :]
        stats[2, :] = STATS_COLLECTION / world_stats[i][0][2, :]
        world_relative_stats.append(stats)

    for i in range(2):
        heights = world_relative_stats[i].mean(axis=1)
        height_offset = heights.max() / 100
        axis[0, i].bar(lables, heights, width=0.5, color=colors[i])
        axis[0, i].set_title(f"{world_stats[i][1]} - mean")
        axis[0, i].set_yticks([], [])
        axis[0, i].set_frame_on(False)
        for count, x_pos in zip(heights[:2], x_positions[:2]):
            axis[0, i].annotate(f"{count * 100:.2f} %", (x_pos, count + height_offset), ha="center")
        axis[0, i].annotate(f"{heights[2]:.2f}", (x_positions[2], heights[2] + height_offset), ha="center")

        heights = world_relative_stats[i].std(axis=1)
        height_offset = heights.max() / 100
        axis[1, i].bar(lables, heights, width=0.5, color=colors[i])
        axis[1, i].set_title(f"{world_stats[i][1]} - stddev")
        axis[1, i].set_yticks([], [])
        axis[1, i].set_frame_on(False)
        for count, x_pos in zip(heights[:2], x_positions[:2]):
            axis[1, i].annotate(f"{count * 100:.2f} %", (x_pos, count + height_offset), ha="center")
        axis[1, i].annotate(f"{heights[2]:.2f}", (x_positions[2], heights[2] + height_offset), ha="center")
    plt.show()
    exit(0)

    figure, axis = plt.subplots(2, 2)
    figure.set_size_inches(12, 10)
    figure.suptitle(f"Absolute statistics per {STATS_LEN} runs of {STATS_COLLECTION} updates in world {world_name}")
    lables = ["fed", "eaten", "games"]
    x_positions = [0, 1, 2]
    titles = ["mean", "stddev"]
    colors = ['m', 'c']
    for i, j in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        heights = world_stats[i][j]
        height_offset = heights.max() / 100
        axis[j, i].bar(lables, heights, width=0.5, color=colors[i])
        axis[j, i].set_title(f"{world_stats[i][2]} - {titles[j]}")
        axis[j, i].set_yticks([], [])
        axis[j, i].set_frame_on(False)
        for count, x_pos in zip(heights, x_positions):
            axis[j, i].annotate(f"{count:.2f}", (x_pos, count + height_offset), ha="center")
    plt.show()

    figure, axis = plt.subplots(1, 1)
    figure.set_size_inches(10, 10)
    figure.suptitle(f"{world_name} significant improvements")
    fed_significant_improvement = world_stats[1][0][0] - world_stats[0][0][0] - world_stats[0][1][0] * 2
    eaten_significant_improvement = world_stats[0][0][1] - world_stats[0][1][1] * 2 - world_stats[1][0][1]
    colors = ['g', 'r']
    axis.bar(["fed", "eaten"], [fed_significant_improvement, eaten_significant_improvement], 
             color=[colors[int(fed_significant_improvement < 0)], colors[int(eaten_significant_improvement < 0)]])
    plt.show()

world.display.activate(size=40)
world.display.delay = 1
while 1:
    world.update(mouse.fed, mouse.eaten)