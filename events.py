import ast
import re

RECEIVE_EVENT = "Receive event"
SEND_EVENT = "Send event"
CHECKPOINT = "Checkpoint"
INIT_EVENT = "Init event"
MAKING_PROGRESS = "Making progress"
COMPUTING = "Computing"
NOP = "Nop"

def load_events(file_name="sampledb.log"):
    regex = '(.*)\n(\S*) ({.*})'
    events = []

    with open(file_name) as f:
        events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
                    for event, host, clock in re.findall(regex, f.read())]
    
    return events