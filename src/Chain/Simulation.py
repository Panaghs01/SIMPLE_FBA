from Chain.Node import Node
from Chain.Block import Block
from Chain.TransactionFactory import TransactionFactory
from Chain.Parameters import Parameters
from Chain.EventQueue import Queue
from Chain.Handler import handle_event

import Chain.tools as tools
import random
import math
from itertools import combinations

from Chain.Event import SystemEvent

from Chain.Consensus.PBFT.PBFT_state import PBFT
from Chain.Consensus.BigFoot.BigFoot_state import BigFoot
from Chain.Consensus.FBA.FBA_state import FBA


class Simulation:
    def __init__(self) -> None:
        self.q = Queue()
        self.clock = 0

        self.nodes = [Node(x, self.q)
                      for x in range(Parameters.application["Nn"])]

        self.current_cp = Parameters.application['CP']

        self.manager = None

        Parameters.tx_factory = TransactionFactory(self.nodes)

    def generate_trust_lists(self):
        
        for node in self.nodes:
            size = random.randint(
                math.ceil((Parameters.application["Nn"]-1)/2),
                Parameters.application['Nn']-1)
            a = []
            for i in range(size):
                #Generate random trust list size and random trusted nodes
                #Then disallow duplicates
                n = random.randint(0, Parameters.application['Nn']-1)
                while n in a or n == node.id:
                    n = random.randint(0, Parameters.application['Nn']-1)
                a.append(n)
            
            node.trust_list = [x for x in self.nodes for y in a if x.id == y]
            
    def quorum_set(self):
        #Encoding the qset function and initializing the threshold
        #According to All neighbors Quorum Slice Configuration math formula
        for n in self.nodes:
            threshold = math.ceil((2*len(n.trust_list)+1)/3)
            n.quorum_set = (n,(n.trust_list,threshold))
    
    def get_combinations(self,lst): # creating a user-defined method
       combination = [] # empty list 
       #Generate every combination with cardinality 1 to length of list parsed
       for r in range(1, len(lst) + 1):
          combination.extend(combinations(lst, r))
       return combination
    
    def quorum_slices(self):
        for node in self.nodes:
            L = []
            a = self.get_combinations(node.quorum_set[1][0])
            for i in a:
                if len(i) >= node.quorum_set[1][1]-1:
                    tmp = list(i)
                    tmp.append(node)
                    L.append(tuple(tmp))
            node.quorum_slices = tuple(L)

    def init_simulation(self):
        genesis = Block.genesis_block()

        # for each node: add the genesis block, set and initialise CP (NOTE: cp.init() produces the first events to kickstart the simulation)
        for n in self.nodes:
            n.add_block(genesis, self.clock)
            n.cp = self.current_cp(n)
            n.cp.init()
        if Parameters.application["Faulty_nodes"]:
            faulty = random.sample(self.nodes,Parameters.application["Faulty_nodes"])
            for node in self.nodes:
                if node in faulty:
                    node.fault_chance = random.randint(5,20)
            
        self.generate_trust_lists()
        self.quorum_set()
        self.quorum_slices()

    def sim_next_event(self):
        tools.debug_logs(msg=tools.sim_info(self, print_event_queues=True))

        # get next event
        next_event = self.q.pop_next_event()
        # update sim clocks
        self.clock = next_event.time

        tools.debug_logs(msg=f"Next:{next_event}",
                         command="Command:", simulator=self)

        # call appropirate handler based on event type
        if isinstance(next_event, SystemEvent):
            self.manager.handle_system_event(next_event)
        else:
            handle_event(next_event)

    def run_simulation(self):
        while self.clock <= Parameters.simulation['simTime']:
            self.sim_next_event()
