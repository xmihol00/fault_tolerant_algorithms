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

## Q6
Possibility of forks makes the Blockchain networks more vulnerable to attacks, as some misbehaving nodes may try to deliberately create forks. After a fork happens some nodes are wasting resources by mining block on the blockchain, which will be later invalidated. Transactions, which were in the invalidated chain, must be re-inserted in the mempool for inclusion in a next block, which prolongs the time needed for confirmation of a transaction.

## Q7
The main significance of the off-chain P2P networks is in the making the on-chain networks more scalable by not publishing every transacion on the blockchain and therefore reducing the load on the on-chain networks. They solve the problem of scalability by creating private state channels over a P2P medium. Two or more parties can communicate over the private state channel using pre-set rules, by which they can make arbitrary number of intermidiate transactions, which are then submitted as a single transaction to the on-chain network and therefore written on the blockchain, when any of the involved parties wishes to close the state channel.

## Q8
The main significance of the off-chain P2P networks is in the making the on-chain networks more scalable by not publishing every transacion on the blockchain and therefore reducing the load on the on-chain networks. They solve the problem of scalability by creating private state channels over a P2P medium. Two or more parties can communicate over the private state channel using pre-set rules, by which they can make arbitrary number of intermidiate transactions, which are then submitted as a single transaction to the on-chain network and therefore written on the blockchain, when any of the involved parties wishes to close the state channel.

## Q9
Payment channel networks (PCNs) are off-chain P2P networks, which allow transactions to happen in a safe manner between only the transacting parties, by which the load on the on-chain networks is decreased. The main difference to the to the traditional communication networks is in routing, as traditional routing algorithms typically aim to find short and low-load paths, which has stable link capacities, while the link capacities in PCNs represent payment balances, which can be highly dynamic. Additional challanges such as privacy, security or transaction fees arrise when dealing with routing in PCNs. 

## Q10
Content-centric addressing is a type of adressing, in which the hashed (multihashed) data of a file are used as an adress, rather than the address being a location, where the file is stored. IPFS makes use of it apart from addressing by Content Identifiers (CIDs) obtained as multihashes, for linking of files or parts of files, for file versioning with a use of Merkle trees or for ensuring file integrity. Multihashes are self describing hashes as they contain the used hash function and the lenght of the digets prepended in front of the actual digest value.

## Q11
Pinning alows nodes to mark files as permanent in their local storage. This prevents the garbage collector from removing them, which does otherwise periodically happen for unpinned files. Content is pinned with an explicit user request, who stores the content in his local storage.

## Q12
Content-centric addressing - files can be retrieved using the same address, even when they change location.
Decentralized nature - files or parts of files can be stored at different locations, which can improve availabilty and decrease the possibility of a single point failure as well as control over the available content.
Inherent content deduplication - detecting same files, although with different names, at the protocol level with the use of CIDs.
Content integrity checks - possibility to check, that a content of a file was not modified again by using the CIDs.
Authorization, censorship and access control - the IPFS is based on P2P network, to which anyone can connect and which does not have by its nature an authority, wich could enfoce access control or censorship.

## Q13
Filecoin is a decentralized storage and retrieval network, which builds on top of IPFS. The use of Filecoin in IPFS improves IPFS’ besteffort storage and delivery service by providing incentive mechanisms. This means, that peers, who store and replicate content, are rewarded with cryptocurency tokens. And on the other hand, peers can ask for persistent storage in exchange for a fee.

## Q14
K-resilient equilibrium (if I undestood correctly, according to the video Nash equilibrium is always 1-resilient) is an equilibrium, for which holds, that no group of size k can gain by diviating (in a cooridnated way).

K-resilient equilibria are interresting (when k is large), because they can discourage misbehaving (rational) players, as the probability of diviating and gaining is descreasing with larger k.

I would give the Bitcoin consensus mechanism as an example. It is k-resiliant, where k is a half of the currently active mining nodes. It discourages a node to mine faulty blocks, as these will be detected and the misbehaving node will not make any BTC. The probability of other nodes misbehaving in the same way is minimal, given the needed compute power.

## Q15
As irrational players do not play the objectively best strategy for them (from multiple reasons), the protocol must account for that, so rational players are not hindered by it. The protocol must be t-immune to tolerate up to t irrational players, while not affecting the payofs of rational players.

## Q16
The outcome can depend also on a scheduler, which decides who moves and how long messages are going to take to be delivered. When a protocol needs to be proven in an asynchronous distributed system, it has to be tipically proven for all possible schedules given by the scheduler.
