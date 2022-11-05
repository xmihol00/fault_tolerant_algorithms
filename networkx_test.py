import networkx as nx 
import matplotlib.pyplot as plt

G = nx.DiGraph()
G.add_node("Alice 1")
G.add_node("Alice 2")
G.add_edge("Alice 1", "Alice 2")
nx.draw(G)
nx.draw_networkx_labels(G, nx.spring_layout(G), labels={"Alice 1": "Alice 1", "Alice 2": "Alice 2"})

print(nx.has_path(G, "Alice 1", "Alice 2"), nx.has_path(G, "Alice 2", "Alice 1"))

plt.show()
