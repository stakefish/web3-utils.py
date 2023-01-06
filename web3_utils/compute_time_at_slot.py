SECONDS_PER_SLOT = 12


def compute_time_at_slot(genesis_time: int, slot: int):
    return genesis_time + slot * SECONDS_PER_SLOT
