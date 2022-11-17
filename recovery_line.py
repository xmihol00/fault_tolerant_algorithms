from py_linq import Enumerable  # pip install py-linq
import sys
import numpy as np

from events import RECEIVE_EVENT
from events import SEND_EVENT
from events import CHECKPOINT
from events import INIT_EVENT

from assign_vector_timestamps import assign_vector_timestamps_to_dict
from events import load_events

def recovery_line(events, failed_processes, verbose=False):
    events_dict = dict(
                      tuple(
                          Enumerable(events).group_by(["name"], lambda x: x["host"]) # group the events by each person
                                            .order_by(lambda x: x.key.name) # order them alphabetically
                                            .select(lambda x: [x.key.name, # name of the person
                                                               x.select(lambda y: [y["event"]] + list(y["clock"].items())) # select the event name and time information, time is given by the number of events
                                                                .order_by(lambda y: y[1][1])  # events seem to be order, but might not be always the case, order them to be sure from 1 to N
                                                                .to_list() # make list of the events for the person
                                                              ])
                                            .to_list()
                           )
                      )

    failed_processes_dict = { name: len(events_dict[name]) for name in failed_processes } # convert the list to dictonary, to be able to use hashing for storing each name just once

    for receiver, sender in (Enumerable(events).where(lambda x: x["event"] == RECEIVE_EVENT)
                                               .select(lambda x: list(x["clock"].items()))):
        events_dict[sender[0]][sender[1] - 1].append(receiver) # add recievers to all send events
    
    while len(failed_processes_dict): # until there are failed processes
        canceled_send_events = []
        for name, time in failed_processes_dict.items():
            timeline = events_dict[name]
            while len(timeline) > time or (timeline[-1][0] != CHECKPOINT and timeline[-1][0] != INIT_EVENT): # rollback to either of these events
                if timeline[-1][0] == SEND_EVENT:
                    canceled_send_events.append(timeline[-1][2:]) # store all recievers of send events, which didn't happen due to rollback
                timeline.pop()

        failed_processes_dict = {} # all failed processes were rolled back, clear them
        for canceled_send_event in canceled_send_events:
            for receiver, time in canceled_send_event:
                if len(events_dict[receiver]) >= time and time < failed_processes_dict.get(receiver, sys.maxsize): # reciever received message, that wasn't send, and when receiving multiple of these, he must rollback to the first of them
                    failed_processes_dict[receiver] = time  # reciever must rollback at least to this time

    if verbose:
        return "\n" + "\n".join([f"{events[-1][0]} from {events[-1][1][0]} at time {events[-1][1][1]}" for events in events_dict.values()])
    else:
        return [events[-1][1][1] for events in events_dict.values()]

def recovery_line_validation(events, failed_processes):
    vector_timestamps = assign_vector_timestamps_to_dict(events)
    names = list(vector_timestamps.keys())
    
    while len(failed_processes):
        for failed_process in failed_processes:
            vector_timestamps_process = vector_timestamps[failed_process]
            while vector_timestamps_process[-1][0] != CHECKPOINT and vector_timestamps_process[-1][0] != INIT_EVENT:
                vector_timestamps_process.pop() # rollback until checpoint or initial event
        
        failed_processes = [] # all failed processes were rolled back at this point
        timestamps_matrix = []
        for name in vector_timestamps.keys():
            timestamps_matrix.append(vector_timestamps[name][-1][1])
        
        # Get the transposed timestamps matrix, where each row contains timestamp values for a person, columns are vector timestamps for the person, 
        # this matrix must have largest values at the diagonal regarding to the rows, which means a person has the largest timestamp value for itself.
        # If this is not satisfied, it means a message, which was not sent, was recieved, therefore everyone on a such a row, who has higher timestamp value, must rollback.
        timestamps_matrix = np.array(timestamps_matrix).T
        for i, diagonal_value in enumerate(timestamps_matrix.diagonal()):
            for index in np.where(timestamps_matrix[i] > diagonal_value)[0]: # get people who have largest timestamp value, than supposted
                if not (names[index] in failed_processes): # if not already marked to rollback
                    vector_timestamps[names[index]].pop()  # pop the last event of the person, which might be a chepoint and the rollback wouldn't work
                    failed_processes.append(names[index])
        
    return timestamps_matrix.diagonal().tolist()

if __name__ == "__main__":
    events = load_events()    
    print("Computed recovery line: ", recovery_line(events, ["Bob"]))
