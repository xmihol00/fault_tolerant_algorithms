import re
import ast
import matplotlib.pyplot as plt
from py_linq import Enumerable  # pip install py-linq

def recovery_line(events, failed_processes):
    events_dictonary = dict(
                           tuple(
                               Enumerable(events).group_by(["name"], lambda x: x["host"])
                                                 .order_by(lambda x: x.key.name)
                                                 .select(lambda x: [x.key.name, # name of the person
                                                                    x.select(lambda y: [y["event"]] + list(y["clock"].items())) # select the event name and time information for the person
                                                                     .order_by(lambda y: y[1][1])  # events seem to be order, but might not be always the case, order them to be sure from 1 to N
                                                                     .to_list() # make list of the events for the person
                                                                   ])
                                                 .to_list()
                                )
                           )
    for receiver, sender in (Enumerable(events).where(lambda x: x["event"] == "Receive event")
                                               .select(lambda x: list(x["clock"].items()))):
        events_dictonary[sender[0]][sender[1] - 1].append(receiver) # add recievers to all send events

    print(events_dictonary)
    


if __name__ == "__main__":
    student_name = 'David Mihola' # fill with your student name
    assert student_name != 'your_student_name', 'Please fill in your student_name before you start.'
    mattrikel_nummer = 12211951

    regex = '(.*)\n(\S*) ({.*})'
    events = []

    with open(f'sampledb.log') as f:
        events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
                   for event, host, clock in re.findall(regex, f.read())]

    print("Computed recovery line: ", recovery_line(events, ["Bob"]))