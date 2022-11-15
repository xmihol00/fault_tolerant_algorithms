import json
import random as rnd
from py_linq import Enumerable  # pip install py-linq

NAMES_RATIO = [("Alice", 1.0), ("Bob", 1.07), ("Carol", 1.05), ("Dave", 1.02), ("Eve", 1.1)]
EVENTS_RATION = [("Send event", 2.0), ("Receive event", len(NAMES_RATIO) ), ("Checkpoint", 1.5), ("Making progress", 0.75), ("Computing", 0.75)]
RECEIVE_EVENT = "Receive event"
SEND_EVENT = "Send event"
START_EVENT = "Init event"
NUMBER_OF_EVENTS = 35

class EventGenerator():
    def __init__(self, names_ration, events_ration):
        self.names = [ name for name, _ in names_ration ]
        self.names_probs = self.normalize_ratio_to_probability(names_ration)
        self.events_probs = self.normalize_ratio_to_probability(events_ration)
        self.name_times = { name: 1 for name, _ in names_ration }
        self.name_send_events = { name: [] for name, _ in names_ration }
        self.names_count = len(names_ration)
        self.send_event_prob_increase = 1 / self.names_count + 0.02 # set the increase between names with some small bias

    def normalize_ratio_to_probability(self, tupled_ratios):
        tupled_ratios_enumerable = Enumerable(tupled_ratios)
        total = tupled_ratios_enumerable.select(lambda x: x[1]).sum()
        return tupled_ratios_enumerable.select(lambda x: (x[0], x[1] / total)).to_list()

    def get_name_event_timing(self):
        drawn_distrib = rnd.random()
        current_distrib = 0
        picked_name = ""
        for name, prob in self.names_probs:
            current_distrib += prob
            if current_distrib >= drawn_distrib:
                picked_name = name
                break

        time = self.name_times[picked_name]
        timings = { picked_name: time }
        
        piceked_event = ""
        if time == 1:
            piceked_event = START_EVENT
        else:
            while True:
                drawn_distrib = rnd.random()
                current_distrib = 0
                for event, prob in self.events_probs:
                    current_distrib += prob
                    if current_distrib >= drawn_distrib:
                        piceked_event = event
                        break
                    
                if event == SEND_EVENT: 
                    self.name_send_events[picked_name].append([time, 0.0, {}])
                elif event == RECEIVE_EVENT:
                    rnd.shuffle(self.names) # randomize the selection of sender
                    for name in self.names:
                        if name == picked_name: # skip the same sender/reciever pair
                            continue
                        not_recieved = Enumerable(self.name_send_events[name]).where(lambda x: x[2].get(picked_name, True)).to_list() # filter only not recieved messages from given sender
                        if len(not_recieved) > 0:
                            send_event = rnd.choice(not_recieved)
                            timings[name] = send_event[0]
                            send_event[1] += self.send_event_prob_increase # increase the probability of send event being removed
                            send_event[2][picked_name] = False # mark, that given 'name' has already recieved this message
                            if send_event[1] > rnd.random():
                                self.name_send_events[name].remove(send_event)
                            break

                    if len(timings) == 1: # sufficient send event was not found
                        continue

                break
            
        
        self.name_times[picked_name] += 1
        return piceked_event, picked_name, timings

generator = EventGenerator(NAMES_RATIO, EVENTS_RATION)
for _ in range(NUMBER_OF_EVENTS):
    event, name, timings = generator.get_name_event_timing()
    print(event)
    print(name, json.dumps(timings))
