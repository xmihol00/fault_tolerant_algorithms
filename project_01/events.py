import ast
import re

RECEIVE_EVENT = "Receive event"
SEND_EVENT = "Send event"
CHECKPOINT = "Checkpoint"
INIT_EVENT = "Init event"
MAKING_PROGRESS = "Making progress"
COMPUTING = "Computing"
NOP = "Nop"

EVENT_REGEX = '(.*)\n(.*?) ({.*})' # regex which allows also spaces in process names

def load_events(file_name="sampledb.log"):
    events = []

    with open(file_name) as f:
        events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
                    for event, host, clock in re.findall(EVENT_REGEX, f.read())]
    
    return events

def load_events_from_text(text):
    return [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)} for event, host, clock in re.findall(EVENT_REGEX, text)]
