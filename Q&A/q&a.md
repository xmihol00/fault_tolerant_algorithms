## Q1
1. Performance - multiprocessor key-value stores can spend majority of their time waiting for coordination, coordination can dramatically slow down computation or stop it altogether.
2. Scalability - reaching consesnus to ensure consistency is more difficult in terms of number of needed messages to be exchanged and therfore time spent with an increasing number of replicas (nodes, CPUs).
3. High latencies - e.g. the Google Spanner transactional database, which ensures consistency, has latencies on the order of 10ms-100ms. High latencies can mean significant losses in revenue, e.g. in case of online trading broker.
4. Availability - when a distributed system may experience network failures, it can provide either consistency, or availability, never both based on the CAP theorem. Availability is usually more important, as users rather prefer consisten results over no results at all.

## Q2
The "Distributed deadlock detection" problem does not require coordination to reach consistency, because the output grows monotonically with the input. On the other hand, the "Distributed garbage collection" problem requires coordination for consistency.

Output growing monotonically with the input means, that the output depends only on the content of the input, the order of the input is not important, e.g. unsynchronized parallelisms or networks with unpredictable delays, which could reorder parts of the input are not problematic.

## Q3
monotonic:
1. Finding a path between two nodes in a distributed graph - once a path between the two nodes is discovered, discovering new edges can only add new pahs between the two nodes.
2. Finding out if a record exist in a distributed database - after the record is found on one of the database servers, it can be declared as existitng without knowing if it exists also on other servers.

non-monotonic:
1. Finding a shortest path between two nodes in a distributed graph - to declare a path between two nodes the shortes, all paths between the nodes must be known, because discovering a new edge could introduce a new shortest path.
2. Finding out if a record does not exist in a distributed database - all servers have to be checked in order to declare a record not existing, because any server can store the record.

## Q4
Confluence is a property of an operation, which ensures deterministic output given non-deterministically ordered and batched inputs passed in to the operation on a single machine. CALM is a theorem, which states that programs that have consistent, coordination-free distributed implementations are programs that can be expressed in monotonic logic. CAP tells, that a system, which can execute arbitrary programs, can ensure only two of the following three properties: consistency, availability, partition-tolerance. CALM on the other hand defines a class of programs, for which the three named properties can be ensured at the same time. The two theorems in a way complement each other, as the first one states what cannot be achieved and the second one what can.

## Q5
1. Topology - traditional communication networks (TN) usualy use client-server topology. e.g. customers (clients) connect to a service offered by a company (server), whereas the cryptocurrency networks (CN) are peer-ro-peer, e.g. miners and users communicate between each other directly.
2. Communication pattern - TN are mostly (apart from routing protocols or other protocols necessary for running the network) based on unicast (1 to 1 communication), whereas CN are mostly based on broadcast (1 to N communication).
3. Routing - in TN routing is usually based on finding a link, which can transfer a message the fastest, whereas in CN the fastest link might not be the optimal, as there are also other concerns like transaction fees or privacy.
4. Rewards/incentives - in TN there are usually centralizes organizations, which pay for resources, whereas in CN the rewards for resources are incorporated in the protocol, as there is no centralization.
5. Security - in CN additional sercurity mechanisums must be implemented to ensure correct  function of the consensus layer. 
