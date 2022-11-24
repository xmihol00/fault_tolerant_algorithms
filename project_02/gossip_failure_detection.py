import random
import threading
import multiprocessing
import os
import time
import zmq
import sys
import numpy as np

# constants
GOSSIP = "GOSSIP"
TERMINATE = "TERMINATE"
SOCKET = "SOCKET"
HEARTBEATS = "HEARTBEATS"
PROCESS = "PROCESS"

SENDER_ID = "sender_id"
LISTENER_ID = "listener_id"

CONNECTION = "tcp://127.0.0.1"

T_GOSSIP = lambda _: (
    5
) # The paper suggests 'T_GOSSIP = xN/B', where: x is the number of bytes per gossip message,
  #                                              N is the number of processes and
  #                                              B is the available bandwith.
  # In this case, on localhost the bandwith is CPU bound - usually in Gb/s, the number of processes is expected to be low and
  # the number of bytes send by each process is also low, although increasing with number of processes, as the heartbeat vector increases. 
  # But still in this setting the gossip time using this equation is expected to be very small, therfore a minimum gossip time of 5 s is 
  # introduced, as the paper also suggests.
T_FAIL = lambda numnodes, additive_constant = 0, multiplicative_constant = 1: (
    T_GOSSIP(numnodes) * numnodes * np.log(numnodes) * multiplicative_constant + additive_constant
) # From the graphs and explanations in the paper, I undetstood that 'T_FAIL' should be multiplied linearithmically by the number of nodes. 
  # By adding aditive and multiplicative constans, the 'P_misstake' can be further decreased/increased.
T_CLEANUP = lambda numnodes, additive_constant = 0, multiplicative_constant = 1: (
    2 * T_FAIL(numnodes, additive_constant, multiplicative_constant)
) # 2 * 'T_FAIL'

FAILED_PROCESS = -1
CLEANED_PROCESS = -2

def gossip(n, N, process_info, print_lock):
    # create a listener
    update_lock = threading.Lock() # thread safe mutex to ensure threads don't update heartbeats over each other
    listener_thread = threading.Thread(target=responder,args=(n, N, process_info, print_lock, update_lock)) # shares the same logical memory
    listener_thread.start()

    t_gossip = T_GOSSIP(N)

    # Creates a publisher socket for sending messages
    context = zmq.Context()
    s = context.socket(zmq.PUB)
    s.bind(f"{CONNECTION}:{(5550 + n)}")

    # Randomly waiting for the listener thread sockets to connect, so the gossips messages send below are spreaded evenly accross time as 
    # described in the paper: "In practice, the protocols are not run in rounds. Each member gossips at regular intervals, but the intervals 
    # are not synchronized."
    sleep_time = random.uniform(2.0, N + 2.0)
    with print_lock:
        print(f"Sender {n} is waiting for {sleep_time} s befor sending first gossip messages...")
    time.sleep(random.randint(2, N + 2))

    while not process_info[TERMINATE]:
        # Choose a random neighbor, compile and send it a GOSSIP message
        p = n
        while p == n: # exclude the possibility of sending messages to itself
          p = random.randint(0, N - 1)

        with print_lock:
            print(f"{GOSSIP} message sent by P{n} to P{p}")

        process_info[HEARTBEATS][n] += 1 # increase its heartbeat
        
        status = { SENDER_ID: int(n), LISTENER_ID: p, HEARTBEATS: process_info[HEARTBEATS] }
        s.send_string(GOSSIP, flags=zmq.SNDMORE)
        s.send_json(status)

        time.sleep(t_gossip)

        # Process can fail with a small probability
        if random.randint(0, 3) < 1:
            process_info[TERMINATE] = True

    with print_lock:
        print(f"Terminating {n} ...")
    listener_thread.join()


def responder(n, N, process_info, print_lock, update_lock):
    with print_lock:
        print(f"Listener {n} is up and running...")
    
    ones = np.ones(N)
    t_cleanup_milli = T_CLEANUP(N) * ones * 1000
    t_fail_milli = T_FAIL(N) * ones * 1000

    fail_timestamps_milli = ones * np.iinfo(np.int32).max
    cleanup_timestamps_milli = ones * np.iinfo(np.int32).max

    current_heartbeats = np.array(process_info[HEARTBEATS])

    context = zmq.Context()
    
    # Create subscriber sockets for each process
    sockets = [k for k in range(N)]
    for p in range(N):
        s = context.socket(zmq.SUB)
        s.connect(f"{CONNECTION}:{5550 + p}")
        s.subscribe(GOSSIP)
        s.subscribe(TERMINATE)
        sockets[p] = s

    # Listening all nodes
    while not process_info[TERMINATE]:
        for p in range(N):
            s = sockets[p]
            try:
                s.RCVTIMEO = 100
                msg_type = s.recv_string()
                msg = s.recv_json()
                
                if msg_type == TERMINATE and msg[LISTENER_ID] == n:
                    with print_lock:
                        print(f"{TERMINATE} message received by P{n} from P{msg[SENDER_ID]}")
                    break

                elif msg_type == GOSSIP and msg[LISTENER_ID] == n:
                    t_milli = int(time.time() * 1000) * ones
                    recieved_heartbeats = np.array(msg[HEARTBEATS])
                    updated_heartbeats_mask = recieved_heartbeats > current_heartbeats  # mask with ones, where recieved hearbeats are higher than current
                    
                    fail_timestamps_milli *= ~updated_heartbeats_mask # mask out changed timestamps
                    fail_timestamps_milli += t_milli * updated_heartbeats_mask # set masked timestamps to current time
                    
                    cleanup_timestamps_milli *= ~updated_heartbeats_mask # mask out changed timestamps
                    cleanup_timestamps_milli += t_milli * updated_heartbeats_mask # set masked indices to current time

                    updated_heartbeats = np.max(np.stack((current_heartbeats, recieved_heartbeats)), axis=0).astype(np.float64)

                    cleaned_processes_mask = cleanup_timestamps_milli < t_milli - t_cleanup_milli
                    updated_heartbeats *= ~cleaned_processes_mask # mask out cleaned processes
                    updated_heartbeats += ones * CLEANED_PROCESS * cleaned_processes_mask # set the cleaned processes as cleaned
                    current_heartbeats = updated_heartbeats.copy() # keep of a copy, where failed processes remain with current heartbeat value

                    failed_processes_mask = fail_timestamps_milli < t_milli - t_fail_milli

                    updated_heartbeats *= ~failed_processes_mask # mask out failed processes
                    updated_heartbeats += ones * FAILED_PROCESS * failed_processes_mask # set fail processes as failed, so the sender doesn't resend them

                    updated_heartbeats = [int(x) for x in updated_heartbeats]  # convertion to list in order to serilize to JSON.

                    with update_lock: # ensure sender and listener do not update at the same time as they share memory
                        process_info[HEARTBEATS] = updated_heartbeats 

                    with print_lock:
                        print(f"{GOSSIP} message received by P{n} from P{msg[SENDER_ID]}, heartbeats: {process_info[HEARTBEATS]}")
            except:
                pass
            
def run_processes(nodes, N, msgNet):
    print_lock = multiprocessing.Lock() # process safe mutex to ensure processes don't print over each other
    processes = []
    for n in nodes:
        p = multiprocessing.Process(target=gossip, args=(n, N, msgNet[n], print_lock)) # No need to share the whole msgNet as processes don't share 
                                                                                       # the same logical memory, i.e. msgNet would copied during fork().
        msgNet[n][PROCESS] = p # to be able to kill the process                        
        processes.append(p)
        
    # Start node processes
    for p in processes:
        p.start()
    
    # Join node processes
    for p in processes:
        p.join()

if __name__ == "__main__":
    numnodes = 3
    nodes = np.arange(numnodes)
    np.random.shuffle(nodes)
    print("Node IDs: ", nodes)

    msgNet = [dict() for _ in range(numnodes)]
    for k in range(numnodes):
        msgNet[k][TERMINATE] = False
        msgNet[k][HEARTBEATS] = [0] * numnodes

    try:
        run_processes(nodes, numnodes, msgNet)
    except KeyboardInterrupt: # ensure all processes terminate and all sockets are closed after interupting the run
        print("Cleanup...", file=sys.stderr)
        for process in msgNet:
            if process.get(PROCESS, False): 
                process[PROCESS].terminate() # SIGTERM, this will also clear the sockets 
