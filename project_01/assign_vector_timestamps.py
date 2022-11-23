import numpy as np
from py_linq import Enumerable  # pip install py-linq

from events import RECEIVE_EVENT
from events import load_events

def assign_vector_timestamps(events):
    names = (Enumerable(events).group_by(["name"], lambda x: x["host"])
                               .select(lambda x: x.key.name)
                               .order_by(lambda x: x) # order alphabetically
                               .to_list()) # get names to get the size of the vector timestamp
    vector_dict = {}
    indices_dict = {}
    for i, name in enumerate(names):
        vector_dict[name] = [[0] * len(names)] # create initial vector for each person
        indices_dict[name] = i # store the 'i' index of the person

    stammed_events = []
    for event in events:
        name = event["host"]
        index = indices_dict[name]
        vector = vector_dict[name][-1].copy() # copy the last vector, from which the new vector is created
        vector[index] += 1 # 'Vi[i] = Vi[i] + 1'
        if event["event"] == RECEIVE_EVENT:
            sender = list(event["clock"].items())[1] 
            sender_vector = vector_dict[sender[0]][sender[1]] # get the sender vector at the time of sending
            final_vector = np.array([vector, sender_vector])
            final_vector = final_vector.max(axis=0) # 'max(Vmessage[j], Vi[j]) for j != i'
            final_vector[index] = vector[index] # fix the vector so 'j != i' holds
            vector = final_vector.tolist()
        
        vector_dict[name].append(vector) # store the updated vector as a new entry
        stammed_events.append(f"{event['event']} {vector}") # store the event with vector time stamp

    return "\n".join(stammed_events)

def assign_vector_timestamps_to_dict(events):
    names = (Enumerable(events).group_by(["name"], lambda x: x["host"])
                               .select(lambda x: x.key.name)
                               .order_by(lambda x: x) # order alphabetically
                               .to_list()) # get names to get the size of the vector timestamp
    vector_dict = {}
    indices_dict = {}
    vector_event_dict = {}
    for i, name in enumerate(names):
        vector_dict[name] = [[0] * len(names)] # create initial vector for each person
        indices_dict[name] = i # store the 'i' index of the person
        vector_event_dict[name] = []

    for event in events:
        name = event["host"]
        index = indices_dict[name]
        vector = vector_dict[name][-1].copy() # copy the last vector, from which the new vector is created
        vector[index] += 1 # 'Vi[i] = Vi[i] + 1'
        if event["event"] == RECEIVE_EVENT:
            sender = list(event["clock"].items())[1] 
            sender_vector = vector_dict[sender[0]][sender[1]] # get the sender vector at the time of sending
            final_vector = np.array([vector, sender_vector])
            final_vector = final_vector.max(axis=0) # 'max(Vmessage[j], Vi[j]) for j != i'
            final_vector[index] = vector[index] # fix the vector so 'j != i' holds
            vector = final_vector.tolist()
        
        vector_dict[name].append(vector) # store the updated vector as a new entry
        vector_event_dict[name].append((event["event"], vector))

    return vector_event_dict

if __name__ == "__main__":
    events = load_events()
    print(assign_vector_timestamps(events))
