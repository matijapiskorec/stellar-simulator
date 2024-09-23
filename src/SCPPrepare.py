"""
=========================
SCPPrepare
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: September 2024

SCPPrepare class.
"""

from typing import Optional
from SCPBallot import SCPBallot
from Log import log

class SCPPrepare:
    def __init__(self, ballot: SCPBallot, prepared: Optional[SCPBallot] = None,
                 aCounter: int = 0, hCounter: int = 0, cCounter: int = 0):
        self.ballot = ballot
        self.prepared = prepared
        self.aCounter = aCounter
        self.hCounter = hCounter
        self.cCounter = cCounter
        log.message.info('Created SCPPrepare message, data = %s', self)

    def __repr__(self):
        return (f"SCPPrepare(ballot={self.ballot}, prepared={self.prepared}, "
                f"aCounter={self.aCounter}, hCounter={self.hCounter}, cCounter={self.cCounter})")

    def __eq__(self, other):
        if isinstance(other, SCPPrepare):
            return (self.ballot == other.ballot and
                    self.prepared == other.prepared and
                    self.aCounter == other.aCounter and
                    self.hCounter == other.hCounter and
                    self.cCounter == other.cCounter)
        return False

    def __hash__(self):
        return hash((self.ballot, self.prepared, self.aCounter, self.hCounter, self.cCounter))