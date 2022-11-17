import matplotlib.pyplot as plt
import numpy as np
from py_linq import Enumerable  # pip install py-linq
import networkx as nx           # pip install networkx

from assign_vector_timestamps import assign_vector_timestamps_to_dict
from events import load_events

def count_concurrent_events(events, plot_graph=False):
    events_grouped = (Enumerable(events).group_by(["name"], lambda x: x["host"]) # group the events by each person
                                        .order_by(lambda x: x.key.name)) # order them alphabetically
    
    names_enumerable = events_grouped.select(lambda x: x.key.name) # select just the names
    
    name_events_enumerable = (events_grouped.select(lambda x: [x.key.name, # name of the person
                                                               x.select(lambda y: list(y["clock"].items())) # select the time information
                                                                .order_by(lambda y: y[0][1])  # events seem to be order, but might not be always the case, order them to be sure from 1 to N
                                                                .to_list() # make list of the events for the person
                                                              ]))
    
    events_dict = (dict(tuple(name_events_enumerable.to_list()))) # create a dictonary of events for each person

    G = nx.DiGraph() # create a directed graph

    for name in names_enumerable:
        previous_event = events_dict[name][0][0] # get the first event for a given person
        G.add_node(previous_event)
        for current_event in events_dict[name][1:]: # for all events from the given person apart form the first
            current_event = current_event[0]
            G.add_node(current_event) # add it to the graph
            G.add_edge(previous_event, current_event) # create a directed connection between subsequent events
            previous_event = current_event
    
    for recieve_event in (name_events_enumerable.select_many(lambda x: x[1])
                                                .where(lambda x: len(x) > 1)): # get all Receive events
        G.add_edge(recieve_event[1], recieve_event[0]) # create a directed connection between the sender and reciever

    if plot_graph: # optionally plot the graph, there are too many events, so it isn't very clear
        _, axis = plt.subplots(figsize=(15, 15))
        nx.draw(G, ax=axis, pos=nx.spring_layout(G))
        plt.show()

    concurrent_event_pairs_dict = { } # dictonary to store already found concurrent event pairs 
    pure_events_enumerable = ((Enumerable(events).select(lambda x: list(x["clock"].items())[0])))
    for event_A in pure_events_enumerable: 
        for event_B in pure_events_enumerable.where(lambda x: x != event_A): # do the cartesian product of events
            if not (concurrent_event_pairs_dict.get((event_A, event_B), False) or 
                    concurrent_event_pairs_dict.get((event_B, event_A), False)): # check if the event pair isn't already marked as concurrent
                if not (nx.has_path(G, event_A, event_B) or nx.has_path(G, event_B, event_A)): # no path from 'event_A' to 'event_B' or the other way around, therefore they must be concurrent
                    concurrent_event_pairs_dict[(event_A, event_B)] = True # mark the pair as a concurrent event pair

    return len(concurrent_event_pairs_dict) # number of concurrent event pairs is equal to the number of unique entries in the dictonary

def count_concurrent_events_validation(events):
    # clean and merge the vector timestamps
    vector_timestamps = (Enumerable(assign_vector_timestamps_to_dict(events).values()).select_many(lambda x: Enumerable(x).select(lambda y: y[1]) # select just the vectors
                                                                                                                          .to_list())
                                                                                      .to_list())
    concurent_event_count = 0
    vector_timestamps = np.array(vector_timestamps)
    for vector_timestamp_A in vector_timestamps:
        for vector_timestamp_B in vector_timestamps: # do the cartesian product of events
            timestamp_difference = vector_timestamp_A - vector_timestamp_B
            if timestamp_difference.max() > 0 and timestamp_difference.min() < 0: # events are not comparable
                concurent_event_count += 1
    
    return concurent_event_count // 2 # make pairs
            
if __name__ == "__main__":
    events = load_events()
    print('Number of concurrent event pairs:', count_concurrent_events_validation(events))
    print('Number of concurrent event pairs:', count_concurrent_events(events))
