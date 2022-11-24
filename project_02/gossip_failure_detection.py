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
        #with print_lock:
        #    print("sender:", msgNet, end="\n\n")
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
    
    t_fail = T_FAIL(N)
    t_cleanup = T_CLEANUP(N)
    ones = np.ones(N)

    fail_timestamps_mili = ones * sys.maxsize
    cleanup_timestamps_mili = ones * sys.maxsize

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
                    t_milli = int(time.time() * 1000)
                    current_heartbeats = np.array(process_info[HEARTBEATS])
                    recieved_heartbeats = np.array(msg[HEARTBEATS])
                    updated_heartbeats = (current_heartbeats - recieved_heartbeats) < 0 # recieved hearbeat is higher than current

                    fail_timestamps_mili *= not updated_heartbeats # mask changed timestamps
                    fail_timestamps_mili += np.ones(N) * t_milli * updated_heartbeats # reset timestamps of updated heartbeats to current time

                    cleanup_timestamps_mili *= not updated_heartbeats # mask changed timestamps
                    cleanup_timestamps_mili += np.ones(N) * t_milli * updated_heartbeats # reset timestamps of updated heartbeats to current time

                    # TODO check expired timestamps

                    updated_heartbeats = [
                        int(x) for x in np.max(np.stack((current_heartbeats, recieved_heartbeats)), axis=0)
                    ]  # merge the heartbeats of the listener and sender - the listener and sender with same ID share memory, 
                       # they are just threads of the same process. Convertion to list is necesary in order to serilize to JSON.

                    with update_lock: # ensure sender and listener do not update at the same time
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
