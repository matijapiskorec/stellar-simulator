"""
=========================
SCPBallot
=========================

Author: Azizbek Asadov
Last update: August 2024

SCPBallot struct/class.

Documentation:

[2] Nicolas Barry and Giuliano Losa and David Mazieres and Jed McCaleb and Stanislas Polu, The Stellar Consensus Protocol (SCP) - technical implementation draft, https://datatracker.ietf.org/doc/draft-mazieres-dinrg-scp/05/
"""

from Value import Value
from Log import log

class SCPBallot:
    def __init__(self, counter: int, value: Value):
        self.counter = counter
        self.value = value
        log.value.info('Created value, hash = %s, state = %s, transactions = %s', self.counter, self.value,)


    def __lt__(self, other):
        if self.counter != other.counter:
            return self.counter < other.counter
        return self.value.hash < other.value.hash

    def __repr__(self):
        return f"SCPBallot(counter={self.counter}, value={self.value})"