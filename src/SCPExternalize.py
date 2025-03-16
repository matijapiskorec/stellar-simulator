from SCPBallot import SCPBallot
import time

class SCPExternalize:
    def __init__(self, ballot: SCPBallot, hCounter: int = 0, timestamp=None):
        self.ballot = ballot
        self.hCounter = hCounter
        self._time = timestamp if timestamp is not None else time.time() # add this to keep track of next slots nomination round

    def __repr__(self):
        return (f"SCPExternalize(ballot={self.ballot}, hCounter={self.hCounter}, time={self._time})")
