"""
=========================
Quorum Set
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: September 2024

QuorumSet class.
"""

from typing import Optional
from SCPBallot import SCPBallot

class SCPPrepare:
    def __init__(self, ballot: SCPBallot, prepared: Optional[SCPBallot] = None, aCounter: int = 0, hCounter: int = 0, cCounter: int = 0):
        self.ballot = ballot
        self.prepared = prepared
        self.aCounter = aCounter
        self.hCounter = hCounter
        self.cCounter = cCounter

    def __repr__(self):
        return (f"SCPPrepare(ballot={self.ballot}, prepared={self.prepared}, "
                f"aCounter={self.aCounter}, hCounter={self.hCounter}, cCounter={self.cCounter})")



