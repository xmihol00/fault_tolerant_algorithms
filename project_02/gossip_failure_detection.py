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
RECEIVER_ID = "receiver_id"

CONNECTION = "tcp://127.0.0.1"
T_GOSSIP = 5 # the paper suggests 'T_GOSSIP = xN/B', where: x is the number of bytes per gossip message,
             #                                              N is the number of processes and
             #                                              B is the available bandwith.
             # In this case, on localhost the bandwith is CPU bound - usually in Gb/s, the number of processes is expected to be low and
             # the number of bytes send by each process is also low. This would lead to the gossip time being to small, therfore
             # a minimum gossip time of 5 s is introduced, as the paper also suggests.

def gossip(n, N, process_info, print_lock):
    # create a listener
    listener_thread = threading.Thread(target=responder,args=(n, N, process_info, print_lock)) # shares the same logical memory
    listener_thread.start()

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
        status = { SENDER_ID: int(n), RECEIVER_ID: p, HEARTBEATS: process_info[HEARTBEATS] }
        s.send_string(GOSSIP, flags=zmq.SNDMORE)
        s.send_json(status)

        time.sleep(T_GOSSIP)

        # Process can fail with a small probability
        if random.randint(0, 3) < 1:
            process_info[TERMINATE] = True

    with print_lock:
        print(f"Terminating {n} ...")
    listener_thread.join()


def responder(n, N, process_info, print_lock):
    with print_lock:
        print(f"Listener {n} is up and running...")

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
                
                if msg_type == TERMINATE and msg[RECEIVER_ID] == n:
                    with print_lock:
                        print(f"{TERMINATE} message received by P{n} from P{msg[SENDER_ID]}")
                    break

                elif msg_type == GOSSIP and msg[RECEIVER_ID] == n:
                    # merge the heartbeats of the reciever and sender
                    process_info[HEARTBEATS] = [int(x) for x in np.max(np.stack((process_info[HEARTBEATS], msg[HEARTBEATS])), axis=0)]
                    with print_lock:
                        print(f"{GOSSIP} message received by P{n} from P{msg[SENDER_ID]}, heartbeats: {process_info[HEARTBEATS]}")
            except:
                pass
            
def run_processes(nodes, N, msgNet, print_lock):
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
        print_lock = threading.Lock() # ensure processes don't print over each other
        run_processes(nodes, numnodes, msgNet, print_lock)
    except KeyboardInterrupt: # ensure all processes terminate and all sockets are closed after interupting the run
        print("Cleanup...", file=sys.stderr)
        for process in msgNet:
            if process.get(PROCESS, False): 
                process[PROCESS].terminate() # SIGTERM, this will also clear the sockets 
