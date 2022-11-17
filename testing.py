import json
import itertools
import sys

from db_generator import EventGenerator
from events import load_events_from_text
from count_concurrent_events import count_concurrent_events
from count_concurrent_events import count_concurrent_events_validation
from recovery_line import recovery_line
from recovery_line import recovery_line_validation

SUCCESS_COLOR = "\033[92m"
FAIL_COLOR = "\033[91m"
BOLD = "\033[1m"
RESET_COLOR = "\033[0m"

def success():
    return f"{BOLD}{SUCCESS_COLOR}SUCCESS{RESET_COLOR}"

def fail():
    return f"{BOLD}{FAIL_COLOR}FAIL{RESET_COLOR}"

NAMES_RATIOS = [
                  [("Alice", 1.0), ("Bob", 1.07), ("Carol", 1.05), ("Dave", 1.02), ("Eve", 1.1)],
                  [("PC A", 0.9), ("PC B", 0.97), ("PC C", 0.95), ("PC D", 0.92)],
                  [("New York", 1.2), ("Paris", 1.22), ("Berlin", 1.24), ("Tokio", 1.26), ("Prague", 1.28), ("Las Vegas", 1.3), ("Beijing", 1.32)]
               ]
EVENTS_RATIONS = [
                    [("Send event", 2.0), ("Receive event", len(NAMES_RATIOS[0]) ), ("Checkpoint", 1.5), ("Making progress", 0.75), ("Computing", 0.75)],
                    [("Send event", 1.0), ("Receive event", len(NAMES_RATIOS[1]) ), ("Checkpoint", 1.0), ("Making progress", 0.85), ("Computing", 0.85)],
                    [("Send event", 2.5), ("Receive event", len(NAMES_RATIOS[2]) ), ("Checkpoint", 1.75), ("Making progress", 1.0), ("Computing", 1.0)],
                 ]

NUMER_OF_EVENTS_PER_PROCESS = [ 10, 15, 20, 25, 30 ]
if __name__ == "__main__":
    print(RESET_COLOR, end="")

    for run_number in range(10):
        for i in range(len(NAMES_RATIOS)):
            names_ratio = NAMES_RATIOS[i]
            events_ratio = EVENTS_RATIONS[i]
            
            event_generator = EventGenerator(names_ratio, events_ratio)
            for number_of_events_per_process in NUMER_OF_EVENTS_PER_PROCESS:
                number_of_events = number_of_events_per_process * len(names_ratio) + run_number

                event_file = ""
                event_generator.reset()
                for _ in range(number_of_events):
                    event, name, timings = event_generator.get_name_event_timing()
                    event_file += f"{event}\n{name} {json.dumps(timings)}\n"
                
                events = load_events_from_text(event_file)
                try:
                    result_A = count_concurrent_events(events)
                    result_B = count_concurrent_events_validation(events)
                    ok = result_A == result_B
                    print("Number of concurrent event pairs:", result_A, result_B, "\t", success() if ok else fail(), "\n")
                    if not ok:
                        raise

                    names = [name for name, _ in names_ratio]
                    for i in range(1, len(names) + 1):
                        for combination in itertools.combinations(names, i):
                            result_A = recovery_line(events, combination)
                            result_B = recovery_line_validation(events, combination)
                            ok = result_A == result_B
                            print("Computed recovery line:", result_A, result_B, "\t", success() if ok else fail())
                            if not ok:
                                raise
                    print()
                except:
                    print(event_file, file=sys.stderr)
                    exit(1)
