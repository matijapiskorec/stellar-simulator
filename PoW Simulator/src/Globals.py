"""
=========================
Globals
=========================

Author: Matija Piskorec
Last update: August 2023

Globals class which stores the variables that need to be accessible to different classes in the simulation.
"""

class Globals:

    simulation_time = 0
    slot = 1
    TIMEOUT_THRESHOLD = simulation_time * 0.01
    target_block_time = 1
    mine_time_scale = 0.1

