import random
import threading
import multiprocessing
import os
import time
import zmq
import sys
import numpy as np

# constants
RUN_LENGTH = 120 # lenght of the simulation in seconds
NODES_FAIL_RESTART_PROBS = [(0.0, 0.25), (0.15, 0.05), (0.0, 0.25), (0.0, 0.25)]

GOSSIP = "G"
TERMINATED = "T"
HEARTBEATS = "HBs"
PROCESS = "P"
FAIL_PROB = "fp"
RESTART_PROB = "rp"

SENDER_ID = "s_id"
LISTENER_ID = "l_id"

CONNECTION = "tcp://127.0.0.1"

T_MUL_CONST = 1
T_ADD_CONST = 0

T_GOSSIP = lambda _: (
    2.0
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

FAILED_PROCESS = -2
CLEANED_PROCESS = -1


def gossip(n, N, node, print_lock):
    # create a listener
    update_lock = threading.Lock() # thread safe mutex to ensure threads don't update heartbeats over each other
    listener_thread = threading.Thread(target=responder,args=(n, N, node, print_lock, update_lock)) # shares the same logical memory
    listener_thread.start()

    t_gossip = T_GOSSIP(N)
    heartbeats = node[HEARTBEATS]

    # Creates a publisher socket for sending messages
    context = zmq.Context()
    s = context.socket(zmq.PUB)
    s.bind(f"{CONNECTION}:{(5550 + n)}")

    # Randomly waiting for the listener thread sockets to connect, so the gossips messages send below are spreaded evenly accross time as 
    # described in the paper: "In practice, the protocols are not run in rounds. Each member gossips at regular intervals, but the intervals 
    # are not synchronized."
    sleep_time = random.uniform(2.0, N + 2.0)
    with print_lock:
        print(f"Sender P{n} is waiting for {sleep_time} s befor sending first gossip messages...")
    time.sleep(random.randint(2, N + 2))

    while True:
        if node[TERMINATED]:
            if random.random() < node[RESTART_PROB]:
                node[TERMINATED] = False
                for i in range(N):
                    node[HEARTBEATS][i] = CLEANED_PROCESS

                node[HEARTBEATS][n] = 0
                with print_lock:
                    print(f"P{n} is restarting...")
        else:
            # Choose a random neighbor, compile and send it a GOSSIP message
            heartbeats_numpy = np.array(heartbeats)
            heartbeats_numpy[n] = CLEANED_PROCESS # mark self as cleaned to exclude the possibility of sending messages to itself
            heartbeats_numpy = np.where((heartbeats_numpy != FAILED_PROCESS) & (heartbeats_numpy != FAILED_PROCESS))[0] # exclude failed and cleaned processes

            if heartbeats_numpy.shape[0]: # only send message if there is any listener
                listener_id = heartbeats_numpy[random.randint(0, heartbeats_numpy.shape[0] - 1)] # select one active process randomly

                with print_lock:
                    print(f"Gossip message sent by P{n} to P{listener_id}")

                heartbeats[n] += 1 # increase its heartbeat
                status = { SENDER_ID: int(n), LISTENER_ID: int(listener_id), HEARTBEATS: heartbeats }
                s.send_string(GOSSIP, flags=zmq.SNDMORE)
                s.send_json(status)

    
            # Process can fail with a small probability
            if random.random() < node[FAIL_PROB]:
                node[TERMINATED] = True
                with print_lock:
                    print(f"P{n} {node[FAIL_PROB]} failed...")

        time.sleep(t_gossip)

    # TODO
    listener_thread.join()


def responder(n, N, node, print_lock, update_lock):
    with print_lock:
        print(f"Listener P{n} is up and running...")
    
    ones = np.ones(N)
    t_cleanup_milli = T_CLEANUP(N, T_MUL_CONST, T_ADD_CONST) * ones * 1000
    t_fail_milli = T_FAIL(N, T_MUL_CONST, T_ADD_CONST) * ones * 1000

    t_milli = int(time.time() * 1000)
    fail_timestamps_milli = ones * t_milli
    cleanup_timestamps_milli = ones * t_milli

    current_heartbeats = np.array(node[HEARTBEATS])

    context = zmq.Context()
    
    # Create subscriber sockets for each process
    sockets = [None] * N
    for process_id in range(N):
        socket = context.socket(zmq.SUB)
        socket.connect(f"{CONNECTION}:{5550 + process_id}")
        socket.subscribe(GOSSIP)
        socket.subscribe(TERMINATED)
        sockets[process_id] = socket

    # Listening all nodes
    while True:
        for process_id in range(N):
            socket = sockets[process_id]
            try:
                socket.RCVTIMEO = 100
                message_type = socket.recv_string()
                message = socket.recv_json()
                
                if message_type == TERMINATED and message[LISTENER_ID] == n:
                    with print_lock:
                        print(f"Terminate message received by P{n} from P{message[SENDER_ID]}")
                    break

                elif message_type == GOSSIP and message[LISTENER_ID] == n:
                    t_milli = int(time.time() * 1000) * ones
                    recieved_heartbeats = np.array(message[HEARTBEATS])
                    updated_heartbeats_mask = recieved_heartbeats > current_heartbeats  # mask with ones, where recieved hearbeats are higher than current
                    
                    fail_timestamps_milli *= ~updated_heartbeats_mask # mask out changed timestamps
                    fail_timestamps_milli += t_milli * updated_heartbeats_mask # set masked timestamps to current time
                    
                    cleanup_timestamps_milli *= ~updated_heartbeats_mask # mask out changed timestamps
                    cleanup_timestamps_milli += t_milli * updated_heartbeats_mask # set masked indices to current time

                    updated_heartbeats = np.max(np.stack((current_heartbeats, recieved_heartbeats)), axis=0).astype(np.float64)

                    cleaned_processes_mask = cleanup_timestamps_milli < (t_milli - t_cleanup_milli)
                    updated_heartbeats *= ~cleaned_processes_mask # mask out failed and cleaned processes
                    updated_heartbeats += ones * CLEANED_PROCESS * cleaned_processes_mask # set the cleaned processes as cleaned
                    current_heartbeats = updated_heartbeats.copy() # keep a copy, where failed processes remain with current heartbeat value

                    failed_processes_mask = (fail_timestamps_milli < (t_milli - t_fail_milli)) & ~cleaned_processes_mask 
                    updated_heartbeats *= ~failed_processes_mask
                    updated_heartbeats += ones * FAILED_PROCESS * failed_processes_mask # set fail processes as failed, so the sender doesn't resend them

                    with update_lock: # ensure sender and listener do not update at the same time as they share memory
                        for i, updated_heartbeat in enumerate(updated_heartbeats):
                            node[HEARTBEATS][i] = int(updated_heartbeat) # convert to int in order to serilize to JSON

                    with print_lock:
                        print(f"Gossip message received by P{n} from P{message[SENDER_ID]}, heartbeats: {node[HEARTBEATS]}")
            except:
                pass
            
def run_processes(N, network):
    print_lock = multiprocessing.Lock() # process safe mutex to ensure processes don't print over each other
    for i, node in enumerate(network):
        node[PROCESS] = multiprocessing.Process(
            target=gossip, args=(i, N, node, print_lock)
        ) # No need to share the whole network as processes don't share the same logical memory, i.e. network would be copied during fork().
    
    # Start node processes
    for node in network:
        node[PROCESS].start()
    
    time.sleep(RUN_LENGTH) # run the simulation for a given time
    with print_lock:
        print("Terminating...", file=sys.stderr)

    # Terminate and join node processes
    for node in network:
        node[PROCESS].terminate()
        node[PROCESS].join()

if __name__ == "__main__":
    N = len(NODES_FAIL_RESTART_PROBS)
    print(f"T_gossip: {T_GOSSIP(N)} s, T_fail: {T_FAIL(N, T_MUL_CONST, T_ADD_CONST)} s, T_cleanup: {T_CLEANUP(N, T_MUL_CONST, T_ADD_CONST)} s")

    network = [{TERMINATED: False, HEARTBEATS: [0] * N, PROCESS: None, FAIL_PROB: fail_prob, RESTART_PROB: restart_prob} 
                  for fail_prob, restart_prob in NODES_FAIL_RESTART_PROBS]
    try:
        run_processes(N, network)
    except KeyboardInterrupt: # ensure all processes terminate and all sockets are closed after interupting the run
        print("\nTerminating...", file=sys.stderr)
        for node in network:
            if node.get(PROCESS, False): 
                node[PROCESS].terminate() # SIGTERM, this will also clear the sockets 
                node[PROCESS].join()
