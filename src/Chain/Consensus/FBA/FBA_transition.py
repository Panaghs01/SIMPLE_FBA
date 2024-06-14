from Chain.Parameters import Parameters

import Chain.Consensus.HighLevelSync as Sync
import Chain.Consensus.FBA.FBA_messages as FBA_messages
import Chain.Consensus.Rounds as Rounds

import math
import random

from Chain.Network import Network

def can_externalize(node):
    counter = 0
    for n in node.cp.msgs['commit']:
        counter += 1
    if counter >= math.ceil((Parameters.application["Nn"]*2 + 1) / 3):
        return True
    return False

def can_commit(node):
    for qslice in node.quorum_slices:
        counter = 0
        for n in qslice:
            if n.id in node.cp.msgs['prepare']:
                counter += 1
        if counter >= len(qslice):
            return True
    return False

def misbehave(state): 
    chance = random.randint(0, 100)
    idle_chance = random.randint(0,10)
    misinform = random.randint(idle_chance,idle_chance+10)
    delay_chance= random.randint(misinform,misinform+10)
    if chance<=idle_chance:
        state.state='idle'
    elif chance<=misinform:
        coinflip=random.randint(1,2) 
        if coinflip == 1:
            state.state='mispreparing'
        else: 
            state.state='miscommiting'
    elif chance<delay_chance:
        state.state='delaying'
        state.node.delay=random.randint(1,10)
        
        
def propose(state, event):
    time = event.time
      
    if not state.state=='delaying':
        # attempt to create block
        block, creation_time = state.create_FBA_block(time)
    else:
        block, creation_time = state.create_FBA_block(
            time+state.node.behaviour.delay)
    
    if block is None:
        # if there is still time in the round, attempt to reschedule later when txions might be there
        if creation_time + 1 + Parameters.execution['creation_time'] <= state.timeout.time:
            FBA_messages.schedule_propose(state, creation_time + 1)
        else:
            print(
                f"Block creation failed at {time} for CP {state.NAME}")
    else:

        # block created, change state, and broadcast it.
        state.state = 'prepared'
        state.block = block.copy()
        # create the votes extra_data field and log votes
        state.block.extra_data['votes'] = {
            'prepare': [], 'commit': []}
        state.process_vote('prepare', state.node,
                          state.rounds.round, time)
        state.block.extra_data['votes']['prepare'].append((
            event.creator.id, time, Network.size(event)))
        
        if state.node.behaviour.Byzantine==False:
            FBA_messages.trusted_cast_prepare(state, time, block)
        else: 
            FBA_messages.broadcast_prepare(
                state, time+state.node.behaviour.delay, block)

    return 'handled'


def prepare(state, event):
    time = event.time
    block = event.payload['block']
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return 'invalid'
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]

    if state.state=='delaying':
        time+=state.node.behaviour.delay
        if not state.block:
            state.state='new_round'
        elif can_commit(state.node):
            state.state='commit' 
        elif state.state=='mispreparing' or state.state=='miscommiting':
            pass
        else:
            state.state='prepared'
    
    match state.state:
        case 'new_round':
            #validate block
            time += Parameters.execution["block_val_delay"]

            if state.validate_block(block):
                # store block as current block
                state.block = event.payload['block'].copy()
                state.block.extra_data['votes'] = {
                        'prepare': [], 'commit': []}
                state.process_vote('prepare', event.creator,
                                   state.rounds.round, time)
    
                state.block.extra_data['votes']['prepare'].append((
                    event.creator.id, time, Network.size(event)))
                
                state.process_vote('prepare',state.node,state.rounds.round,time)

                # if >= threshold ammount of nodes have prepared we can start commiting
                if can_commit(state.node):
                    # change to prepared
                    state.state = 'commit'
    
                    # trusted_cast commit message
                    FBA_messages.trusted_cast_commit(state, time, block)
    
                    # count own vote
                    state.process_vote('commit', state.node,
                                       state.rounds.round, time)
    
                    state.block.extra_data['votes']['commit'].append((
                        event.actor.id, time, Network.size(event)))
                else:
                    state.state = 'prepared'
                    FBA_messages.trusted_cast_prepare(state, time, block)
    
                    return 'new_state'
            else:
                # if the block was invalid begin round change
                Rounds.change_round(state.node, time)
                return 'handled'  # event handled but state did not change

            # not enough votes yet...
            return 'handled'
        case 'prepared':
            state.process_vote('prepare',event.creator,
                               state.rounds.round,time)
            state.block.extra_data['votes']['prepare'].append((
                event.creator.id, time, Network.size(event)))
            if can_commit(state.node):
                
                state.state = 'commit'

                # trusted_cast commit message
                FBA_messages.trusted_cast_commit(state, time, block)

                # count own vote
                state.process_vote('commit', state.node,
                                   state.rounds.round, time)

                state.block.extra_data['votes']['commit'].append((
                    event.actor.id, time, Network.size(event)))

                return 'new_state'
        case 'commit':
            return 'handled'
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case 'idle':
            #If node is idle do not notify anyone just store the information
            #And hide in the shadows
            state.block = event.payload['block'].copy()
            state.block.extra_data['votes'] = {
                    'prepare': [], 'commit': []}
            
            pass
        case 'mispreparing':
            if state.validate_block(block):
                # store block as current block
                state.block = event.payload['block'].copy()
                state.block.extra_data['votes'] = {
                        'prepare': [], 'commit': []}
                state.process_vote('prepare', event.creator,
                                   state.rounds.round, time)
    
                state.block.extra_data['votes']['prepare'].append((
                    event.creator.id, time, Network.size(event)))
                # count own vote
                state.process_vote('prepare', state.node, state.rounds.round, time)
                #broadcast a propose statement, in case it fools anyone
                FBA_messages.broadcast_prepare(state, time, block)
        case 'miscommiting':
            if state.validate_block(block):
                # store block as current block
                state.block = event.payload['block'].copy()
                state.block.extra_data['votes'] = {
                        'prepare': [], 'commit': []}
                state.process_vote('prepare', event.creator,
                                   state.rounds.round, time)
    
                state.block.extra_data['votes']['prepare'].append((
                    event.creator.id, time, Network.size(event)))
                # count own vote
                state.process_vote('prepare', state.node, state.rounds.round, time)
                #broadcast a propose statement, in case it fools anyone
                FBA_messages.broadcast_commit(state, time, block)
        case _:
            raise ValueError(
                f"Unexpected state '{state.state}' for cp FBA...'")


def commit(state, event):
    time = event.time
    block = event.payload['block']
    round = state.rounds.round

    # validate message: old (invalid), current (continue processing), future (valid, add to backlog)
    valid, future = state.validate_message(event)
    if not valid:
        return 'invalid'
    if future is not None:
        return future
    time += Parameters.execution["msg_val_delay"]
    
    if state.node.behaviour.Byzantine: 
        misbehave(state)
        if state.state=='delaying':
            time+=state.node.behaviour.delay
            if not state.block:
                state.state='new_round'
            elif can_commit(state.node):
                state.state='commit' 
            elif state.state=='mispreparing' or state.state=='miscommiting':
                pass
            else:
                state.state='prepared'
    
    match state.state:
        case 'prepared':
            if event.creator.id not in state.node.cp.msgs['prepare']:
                state.process_vote('prepare', event.creator,
                                   state.rounds.round, time)
                state.block.extra_data['votes']['prepare'].append((
                                event.creator.id, time, Network.size(event)))
            state.process_vote('commit', event.creator,
                               state.rounds.round, time)

            state.block.extra_data['votes']['commit'].append((
                event.creator.id, time, Network.size(event)))
            if can_commit(state.node):
                # count vote
                state.state = 'commit'
                state.process_vote('commit', state.node,
                                   state.rounds.round, time)
                state.block.extra_data['votes']['commit'].append((
                    state.node.id, time, Network.size(event)))
                FBA_messages.trusted_cast_commit(state,time,block)
                # if we have enough votes
                if can_externalize(state.node):
                    # add block to BC
                    state.node.add_block(state.block, time)
                    FBA_messages.broadcast_new_block(state, time, block)
                    # start new round
                    state.start(state.rounds.round + 1, time)
                    return 'new_state'
                # not enough votes yet...
            return 'handled'
        case 'commit':
            state.process_vote('commit',event.creator,
                               state.rounds.round,time)
            
            state.block.extra_data['votes']['commit'].append((
                event.creator.id, time, Network.size(event)))
            
            if can_externalize(state.node):
                # add block to BC
                state.node.add_block(state.block, time)

                FBA_messages.broadcast_new_block(state, time, block)
                # start new round
                state.start(state.rounds.round + 1, time)

                return 'new_state'
        case 'new_round':
            return 'backlog'  # node is behind in votes... add to backlog
        case 'round_change':
            return 'invalid'  # node has decided to skip this round
        case 'idle':
            pass
        case 'mispreparing':
            if event.creator.id not in state.node.cp.msgs['prepare']:
                #If there is no block only broadcast the byzantine msg
                #If there is a block also add the votes of that node
                if state.block is not None:
                    state.process_vote('prepare', event.creator,
                                       state.rounds.round, time)
                    state.block.extra_data['votes']['prepare'].append((
                                    event.creator.id, time, Network.size(event)))
                else:
                    pass
            state.process_vote('commit', state.node,
                               state.rounds.round, time)
            #broadcast a propose statement, in case it fools anyone
            FBA_messages.broadcast_prepare(state, time, block)
            # count own vote
            state.process_vote('prepare', state.node, state.rounds.round, time)
        case 'miscommiting':
            if event.creator.id not in state.node.cp.msgs['prepare']:
                #Same as prepare, no block == only broadcast
                if state.block is not None:
                    state.process_vote('prepare', event.creator,
                                       state.rounds.round, time)
                    state.block.extra_data['votes']['prepare'].append((
                                    event.creator.id, time, Network.size(event)))
                else:
                    pass
            state.process_vote('commit', state.node,
                               state.rounds.round, time)
            #broadcast a commit statement, without caring if slice is satisfied
            FBA_messages.broadcast_commit(state, time, block)
            # count own vote
            state.process_vote('commit', state.node, state.rounds.round, time)
        case _:
            raise ValueError(
                f"Unexpected state '{state.state} for cp FBA...'")


def new_block(state, event):
    block = event.payload['block']
    time = event.time

    time += Parameters.execution["msg_val_delay"]
    time += Parameters.execution["block_val_delay"]

    if block.depth <= state.node.blockchain[-1].depth:
        return "invalid"  # old block: ingore
    elif block.depth > state.node.blockchain[-1].depth + 1:
        # future block: initiate sync
        if state.node.state.synced:
            state.node.state.synced = False
            Sync.create_local_sync_event(state.node, event.creator, time)
        # if not synced then we have to wait for ohter blocks in order to validate this so we cannot accept it
        return "handled"
    else:  # valid block
        # update_round if necessary
        state.rounds.round = event.payload['round']

        # add block and start new round
        state.node.add_block(block.copy(), time)

        state.start(event.payload['round']+1, time)

        return "handled"
