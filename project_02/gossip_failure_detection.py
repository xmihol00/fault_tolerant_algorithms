import random
import multiprocessing
import time
import os
import sys
import numpy as np
import socket
import pickle
import signal
import colorama as cm

# constants
RUN_LENGTH = 300 # lenght of the simulation in seconds
STATE_PRINTOUT_PERIOD = 10 # period of node states report
NUMBER_OF_PRINTOUTS = RUN_LENGTH // STATE_PRINTOUT_PERIOD

NODES_FAIL_RESTART_PROBS = [(0.05, 0.05), (0.15, 0.05), (0.02, 0.15), (0.01, 0.1), (0.01, 0.01)]

HEARTBEATS = "HBs"
SENDER_ID = "s_id"
IP = "127.0.0.1" # localhost
PORT_OFFSET = 5500 

T_MUL_CONST = 0.75
T_ADD_CONST = 0

T_GOSSIP = lambda _: (
    2.5
) # The paper suggests 'T_GOSSIP = xN/B', where: x is the number of bytes per gossip message,
  #                                              N is the number of processes and
  #                                              B is the available bandwith.
  # In this case, on localhost the bandwith is CPU bound - usually in Gb/s, the number of processes is expected to be low and
  # the number of bytes send by each process is also low, although increasing with number of processes, as the heartbeat vector increases. 
  # But still in this setting the gossip time using this equation is expected to be very small, therfore a minimum gossip time of 5 s is 
  # introduced, as the paper also suggests.
T_FAIL = lambda numnodes, multiplicative_constant = 1, additive_constant = 0: (
    T_GOSSIP(numnodes) * numnodes * np.log(numnodes) * multiplicative_constant + additive_constant
) # From the graphs and explanations in the paper, I undetstood that 'T_FAIL' should be multiplied linearithmically by the number of nodes. 
  # By adding aditive and multiplicative constans, the 'P_misstake' can be further decreased/increased.
T_CLEANUP = lambda numnodes, multiplicative_constant = 1, additive_constant = 0: (
    2 * T_FAIL(numnodes, multiplicative_constant, additive_constant)
) # 2 * 'T_FAIL'

UNKNOWN_NODE = -3
FAILED_NODE = -2
CLEANED_NODE = -1
ACTIVATED_NODE = 0

COLORS = True # Set to 'False' to print without colors, otherwise printing without colors is only non-terminal devices.
TEXT_COLORS = [cm.Fore.LIGHTBLUE_EX, cm.Fore.LIGHTGREEN_EX, cm.Fore.MAGENTA, cm.Fore.LIGHTYELLOW_EX, cm.Fore.LIGHTRED_EX, cm.Fore.CYAN, cm.Fore.BLUE, cm.Fore.GREEN, 
               cm.Fore.YELLOW, cm.Fore.LIGHTMAGENTA_EX, cm.Fore.LIGHTCYAN_EX, cm.Fore.RED]
TEXT_COLOR_LEN = len(TEXT_COLORS)

def color(node_id):
    if COLORS:
        return f"{TEXT_COLORS[node_id % TEXT_COLOR_LEN]}\33[1m"
    else:
        return ""

def bg_fail():
    if COLORS:
        return f"{cm.Back.RED}{cm.Fore.WHITE}"
    else:
        return ""

def bg_success():
    if COLORS:
        return f"{cm.Back.GREEN}{cm.Fore.WHITE}"
    else:
        return ""

def bg_warning():
    if COLORS:
        return f"{cm.Back.YELLOW}{cm.Fore.WHITE}"
    else:
        return ""

def bg_unknown():
    if COLORS:
        return f"{cm.Back.BLACK}{cm.Fore.WHITE}"
    else:
        return ""

def reset():
    if COLORS:
        return f"{cm.Style.RESET_ALL}"
    else:
        return ""

class Node(multiprocessing.Process):
    def __init__(self, id, number_of_nodes, print_lock, fail_prob, restart_prob):
        super(Node, self).__init__()

        self.id = id
        self.number_of_nodes = number_of_nodes
        self.print_lock = print_lock
        self.fail_prob = fail_prob
        self.restart_prob = restart_prob

        self.ones = np.ones(number_of_nodes)
        self.t_cleanup = T_CLEANUP(N, T_MUL_CONST, T_ADD_CONST) * self.ones
        self.t_fail = T_FAIL(N, T_MUL_CONST, T_ADD_CONST) * self.ones
        self.t_gossip = T_GOSSIP(N)
        self.heartbeats = np.zeros(number_of_nodes) * UNKNOWN_NODE # A node does not know the state of other nodes at the beginning.
        self.heartbeats[id] = ACTIVATED_NODE                       # But sets itsel to active.
        self.current_heartbeats = np.zeros(number_of_nodes)
        
        # As the paper suggests "In gossip protocols, a member forwards new information to randomly chosen members.", the communication
        # should be unicast, not some kind of broadcast as in the original code
        self.gossip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # internet - UDP, transmission of gossip messages does not have to be reliable
        self.receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_socket.bind((IP, PORT_OFFSET + self.id)) # node listens on this socket
        # sockets will be closed by the OS

        self.fail_timestamps = None
        self.cleanup_timestamps = None
        self.failed = False
    
    def stop(self):
        self.terminate()
        self.join()
        
    def print_state(self, *_):
        with self.print_lock:
            print(f"{color(self.id)}Node {self.id}{reset()} is {f'{bg_fail()}not working{reset()}.' if self.failed else f'{bg_success()}working{reset()}, its perception of the network is:'}{reset()}", file=sys.stdout)
            if not self.failed:
                for i, heartbeat in enumerate(self.heartbeats):
                    if i != self.id:
                        print(f"   {color(i)}Node {i}{reset()} is {f'{bg_warning()}failed' if heartbeat == FAILED_NODE else f'{bg_fail()}cleaned' if heartbeat == CLEANED_NODE else f'{bg_unknown()}unknown' if heartbeat == UNKNOWN_NODE else f'{bg_success()}running'}{reset()}.", file=sys.stdout)
    
    def register_signal_handlers(self):
        signal.signal(signal.SIGUSR1, self.print_state)
        signal.siginterrupt(signal.SIGUSR1, False)

    def run(self):
        self.register_signal_handlers()

        # Randomly waiting before nodes start to gossip as described in the paper: "In practice, the protocols are not run in rounds. 
        # Each member gossips at regular intervals, but the intervals are not synchronized."
        sleep_time = random.uniform(0.0, N)
        with self.print_lock:
            print(f"{color(self.id)}Node {self.id}{reset()} is waiting for {sleep_time} s befor sending first gossip messages...", file=sys.stderr)
        time.sleep(sleep_time)

        current_time = time.time() # set up timestamps to current time
        self.fail_timestamps = self.ones * current_time
        self.cleanup_timestamps = self.ones * current_time

        while True:
            if self.failed:
                if random.random() < self.restart_prob:
                    self.failed = False
                    for i in range(N):
                        self.heartbeats[i] = UNKNOWN_NODE # Node does not know the state of other nodes after restarting.

                    self.heartbeats[self.id] = ACTIVATED_NODE # Sets its heartbeat to active again
                    with self.print_lock:
                        print(f"{color(self.id)}Node {self.id}{reset()} is {bg_success()}restarting{reset()}...", file=sys.stdout)
            else:
                self.send_gossip()
                if random.random() < self.fail_prob: # Process can fail with a small probability
                    self.failed = True
                    with self.print_lock:
                        print(f"{color(self.id)}Node {self.id}{reset()} {bg_fail()}failed{reset()}...", file=sys.stdout)

            try: # Waiting on socket is used instead of polling in the previous code. 
                 # Waiting up to maximum of T_GOSSIP, then new gossip message must be sent.

                sleep_start = time.time() # timestamp of the start of the waiting
                current_time = sleep_start
                while sleep_start + self.t_gossip > current_time: # waited less than for T_GOSSIP
                    self.receiver_socket.settimeout(sleep_start + self.t_gossip - current_time) # set the timeout to wait exactly for T_GOSSIP waiting to be fullfilled
                    message = self.receiver_socket.recvfrom(65507) # expecting the gossip message is never larger than maximum UDP packet size
                    message = pickle.loads(message[0]) # deserilize
                    if not self.failed: # process the message only of the node is running
                        self.process_gossip(message) # parse the gossip message and update heartbeats
                    current_time = time.time()

            except: # socket timed out, which means waiting for at least T_GOSSIP was performed
                pass
    
    def send_gossip(self):
        heartbeats_numpy = np.array(self.heartbeats)
        heartbeats_numpy[self.id] = CLEANED_NODE # mark self as cleaned to exclude the possibility of sending messages to itself
        heartbeats_numpy = np.where((heartbeats_numpy != FAILED_NODE) & (heartbeats_numpy != CLEANED_NODE))[0] # exclude failed and cleaned processes

        if heartbeats_numpy.shape[0]: # only send message if there is any listener
            listener_id = heartbeats_numpy[random.randint(0, heartbeats_numpy.shape[0] - 1)] # select randomly another node

            with self.print_lock:
                print(f"{color(self.id)}Node {self.id}{reset()} gossips to {color(listener_id)}node {listener_id}{reset()}.", file=sys.stdout)

            self.heartbeats[self.id] += 1 # increase its heartbeat
            status = { SENDER_ID: int(self.id), HEARTBEATS: self.heartbeats }
            self.gossip_socket.sendto(pickle.dumps(status), (IP, PORT_OFFSET + listener_id)) # serilize and send a message to exactly one other node - unicast

    def process_gossip(self, message):
        current_time = time.time()
        recieved_heartbeats = message[HEARTBEATS]
        updated_heartbeats_mask = recieved_heartbeats > self.current_heartbeats  # mask with ones, where recieved hearbeats are higher than current

        self.fail_timestamps *= ~updated_heartbeats_mask # mask out changed timestamps
        self.fail_timestamps += current_time * updated_heartbeats_mask # set masked timestamps to current time

        self.cleanup_timestamps *= ~updated_heartbeats_mask # mask out changed timestamps
        self.cleanup_timestamps += current_time * updated_heartbeats_mask # set masked indices to current time

        updated_heartbeats = np.max(np.stack((self.current_heartbeats, recieved_heartbeats)), axis=0).astype(np.float64)

        cleaned_processes_mask = self.cleanup_timestamps < (current_time - self.t_cleanup)
        updated_heartbeats *= ~cleaned_processes_mask # mask out failed and cleaned processes
        updated_heartbeats += self.ones * CLEANED_NODE * cleaned_processes_mask # set the cleaned processes as cleaned
        self.current_heartbeats = updated_heartbeats.copy() # keep a copy, where failed processes remain with current heartbeat value

        failed_processes_mask = (self.fail_timestamps < (current_time - self.t_fail)) & ~cleaned_processes_mask 
        updated_heartbeats *= ~failed_processes_mask
        updated_heartbeats += self.ones * FAILED_NODE * failed_processes_mask # set fail processes as failed, so the sender doesn't resend them

        self.heartbeats = updated_heartbeats

        with self.print_lock:
            print(f"{color(self.id)}Node {self.id}{reset()} received gossip from {color(message[SENDER_ID])}node {message[SENDER_ID]}{reset()}, heartbeats: {color(self.id)}{self.heartbeats}{reset()}", file=sys.stdout)

def run_network(network):
    for node in network: # start nodes processes
        node.start()
    
    for _ in range(NUMBER_OF_PRINTOUTS): # run the simulation for a given time
        time.sleep(STATE_PRINTOUT_PERIOD) 
        for node in network:
            os.kill(node.pid, signal.SIGUSR1)

    for node in network: # terminate and join node processes
        node.stop()

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True) # do not buffet output of print(), flush after each line
    if not sys.stdout.isatty(): # when the output of the script is not a terminal, print without colors
        COLORS = False

    print(f"{reset()}", end="", file=sys.stdout)
    N = len(NODES_FAIL_RESTART_PROBS)
    print(f"T_gossip: {T_GOSSIP(N)} s, T_fail: {T_FAIL(N, T_MUL_CONST, T_ADD_CONST)} s, T_cleanup: {T_CLEANUP(N, T_MUL_CONST, T_ADD_CONST)} s", file=sys.stderr)

    print_lock = multiprocessing.Lock() # process safe mutex to ensure processes don't print over each other
    network = [Node(id, N, print_lock, fail_prob, restart_prob)
                  for id, (fail_prob, restart_prob) in enumerate(NODES_FAIL_RESTART_PROBS)]
    try:
        run_network(network)
    except KeyboardInterrupt: # ensure all processes terminate
        with print_lock:
            print("\nTerminating...\n", file=sys.stderr)
        for node in network:
            node.stop()
