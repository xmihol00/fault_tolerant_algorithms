import random
import cellular
import networkx as nx
import matplotlib.pyplot as plt
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


class Mouse(cellular.Agent):
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
        self.directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1),
                           (0, -2), (2, -2), (2, 0), (2, 2), (0, 2), (-2, 2), (-2, 0), (-2, -2),
                           (2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (-1, 2), (1, -2), (-1, -2)]
        
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

        #print(self.graph)
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
        elif self.canBeEaten():
            self.moveAwayFromCat()
        else:

            self.cell = self.nodeToCell(self.shortest_path.pop())
            self.shortest_path_changed = False

    def canBeEaten(self):
        for x_dir, y_dir in self.directions:
            if self.getCell(self.cell.x + x_dir, self.cell.y + y_dir) == cat.cell:
                return True
        return False
    
    def canBeImidiatelyEaten(self):
        for x_dir, y_dir in self.directions[0:8]:
            if self.getCell(self.cell.x + x_dir, self.cell.y + y_dir) == cat.cell:
                return True
        return False
    
    def moveAwayFromCat(self):
        current_cell = self.cell
        best_cell = self.cell
        best_path = sys.maxint
        for x_dir, y_dir in self.directions:
            cell = self.getCell(self.cell.x + x_dir, self.cell.y + y_dir)
            if cell and cell != cat.cell:
                self.cell = cell
                if self.canBeImidiatelyEaten():
                    self.cell = current_cell
                else:
                    # TODO
                    return
        
        self.cell = best_cell

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

cheese = Cheese()
mouse = Mouse()
cat = Cat()

world = cellular.World(Cell, directions=directions, filename='world_empty.txt')
world.age = 0

world.addAgent(cheese, cell=pickRandomLocation())   # assign random cell, otherwise agent can be spawned inside wall
world.addAgent(cat, cell=pickRandomLocation())      # assign random cell, otherwise agent can be spawned inside wall
world.addAgent(mouse, cell=pickRandomLocation())    # assign random cell, otherwise agent can be spawned inside wall

endAge = world.age + 00000
while world.age < endAge:
    world.update()

    if world.age % 10000 == 0:
        print ("{:d}, e: {:0.2f}, W: {:d}, L: {:d}".format(world.age, mouse.ai.epsilon, mouse.fed, mouse.eaten))
        mouse.eaten = 0
        mouse.fed = 0

world.display.activate(size=40)
world.display.delay = 2
while 1:
    world.update(mouse.fed, mouse.eaten)