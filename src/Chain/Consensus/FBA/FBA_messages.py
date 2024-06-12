def schedule_propose(state, time):
    payload = {
        'type': 'propose',
        'round': state.rounds.round,
        'CP': state.NAME
    }

    state.node.scheduler.schedule_event(
        state.node, time, payload, state.handle_event)


def trusted_cast_pre_prepare(state, time, block):
    payload = {
        'type': 'pre_prepare',
        'block': block,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    state.node.scheduler.schedule_trusted_cast_message(
        state.node, time, payload, state.handle_event) 


def trusted_cast_prepare(state, time, block):
    payload = {
        'type': 'prepare',
        'block': block,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    state.node.scheduler.schedule_trusted_cast_message(
        state.node, time, payload, state.handle_event)


def trusted_cast_commit(state, time, block):
    payload = {
        'type': 'commit',
        'block': block,
        'round': state.rounds.round,
        'CP': state.NAME
    }
    state.node.scheduler.schedule_trusted_cast_message(
        state.node, time, payload, state.handle_event)


def trusted_cast_new_block(state, time, block):
    payload = {
        'type': 'new_block',
        'block': block,
        'round': state.rounds.round,
        'CP': state.NAME
    }

    state.node.scheduler.schedule_trusted_cast_message(
        state.node, time, payload, state.handle_event)
