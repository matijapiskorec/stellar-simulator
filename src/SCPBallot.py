"""
=========================
Ballot Set
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: September 2024

SCPBallot class.
"""

from Value import Value

class SCPBallot:
    def __init__(self, counter: int, value: Value):
        self.counter = counter
        self.value = value

    def __lt__(self, other):
        if self.counter != other.counter:
            return self.counter < other.counter
        return self.value.hash < other.value.hash

    def __repr__(self):
        return f"SCPBallot(counter={self.counter}, value={self.value})"