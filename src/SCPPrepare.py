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
