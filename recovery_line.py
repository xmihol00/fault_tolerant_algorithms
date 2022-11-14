import re
import ast
import matplotlib.pyplot as plt
from py_linq import Enumerable  # pip install py-linq

from event_names import RECEIVE_EVENT
from event_names import SEND_EVENT
from event_names import CHECKPOINT
from event_names import INIT_EVENT
from event_names import MAKING_PROGRESS
from event_names import COMPUTING

def recovery_line(events, failed_processes):
    events_dict = dict(
                      tuple(
                          Enumerable(events).group_by(["name"], lambda x: x["host"]) # group the events by each person
                                            .order_by(lambda x: x.key.name) # order them alphabetically
                                            .select(lambda x: [x.key.name, # name of the person
                                                               x.select(lambda y: [y["event"]] + list(y["clock"].items())) # select the event name and time information for the person
                                                                .order_by(lambda y: y[1][1])  # events seem to be order, but might not be always the case, order them to be sure from 1 to N
                                                                .to_list() # make list of the events for the person
                                                              ])
                                            .to_list()
                           )
                      )

    failed_processes_dict = { name: len(events_dict[name]) for name in failed_processes } # convert the list to dictonary to be able to use hashing and store each name just once

    for receiver, sender in (Enumerable(events).where(lambda x: x["event"] == RECEIVE_EVENT)
                                               .select(lambda x: list(x["clock"].items()))):
        events_dict[sender[0]][sender[1] - 1].append(receiver) # add recievers to all send events
    
    while len(failed_processes_dict): # until there are failed processes
        canceled_send_events = []
        for name, time in failed_processes_dict.items():
            timeline = events_dict[name]
            while len(timeline) >= time or (timeline[-1][0] != CHECKPOINT and timeline[-1][0] != INIT_EVENT): # rollback to either of these events
                if timeline[-1][0] == SEND_EVENT:
                    canceled_send_events.append(timeline[-1][2:]) # store all recievers of send events, which didn't happen due to rollback
                timeline.pop()

        failed_processes_dict = {} # all failed processes were rolled back
        for canceled_send_event in canceled_send_events:
            for receiver, time in canceled_send_event:
                if len(events_dict[receiver]) >= time: # reciever received message, that was never send, must rollback
                    failed_processes_dict[receiver] = time  # they must rollback to at least one event before the time of receival of the message

    return "\n" + "\n".join([f"{events[-1][0]} from {events[-1][1][0]} at time {events[-1][1][1]}" for events in events_dict.values()])

if __name__ == "__main__":
    student_name = 'David Mihola' # fill with your student name
    assert student_name != 'your_student_name', 'Please fill in your student_name before you start.'
    mattrikel_nummer = 12211951

    regex = '(.*)\n(\S*) ({.*})'
    events = []

    with open(f'testdb4.log') as f:
        events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
                   for event, host, clock in re.findall(regex, f.read())]

    print("Computed recovery line: ", recovery_line(events, ["Bob", "Dave", "Eve", "Alice", "Carol"]))