import re
import ast
import numpy as np
from py_linq import Enumerable  # pip install py-linq

from event_names import RECEIVE_EVENT

def assign_vector_timestamps(events):
    names = (Enumerable(events).group_by(["name"], lambda x: x["host"])
                               .select(lambda x: x.key.name)
                               .order_by(lambda x: x)
                               .to_list()) # get names to get the size of the vector timestamp
    vector_dict = {}
    indices_dict = {}
    for i, name in enumerate(names):
        vector_dict[name] = [[0] * len(names)]
        indices_dict[name] = i

    events_with_vectors = []
    for event in events:
        name = event["host"]
        index = indices_dict[name]
        vector = vector_dict[name][-1].copy()
        vector[index] += 1 # 'Vi[i] = Vi[i] + 1'
        if event["event"] == RECEIVE_EVENT:
            sender = list(event["clock"].items())[1] 
            sender_vector = vector_dict[sender[0]][sender[1]] # get the sender vector at the time of sending
            final_vector = np.array([vector, sender_vector])
            final_vector = final_vector.max(axis=0) # 'max(Vmessage[j], Vi[j]) for j != i'
            final_vector[index] = vector[index] # fix the vector so 'j != i' holds
            vector = final_vector.tolist()
        
        vector_dict[name].append(vector) # store the updated vector and keep the previous ones
        events_with_vectors.append(f"{event['event']} {vector}") # store the event with vector time stamp

    return "\n" + "\n".join(events_with_vectors)

if __name__ == "__main__":
    student_name = 'David Mihola' # fill with your student name
    assert student_name != 'your_student_name', 'Please fill in your student_name before you start.'
    mattrikel_nummer = 12211951

    regex = '(.*)\n(\S*) ({.*})'
    events = []

    with open(f'testdb4.log') as f:
        events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
                   for event, host, clock in re.findall(regex, f.read())]
    
    print(assign_vector_timestamps(events))
