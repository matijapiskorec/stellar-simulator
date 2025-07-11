from SCPBallot import SCPBallot

class SCPCommit:
    def __init__(self, ballot: SCPBallot, preparedCounter: int, hCounter: int = 0, cCounter: int = 0):
        self.ballot = ballot
        self.preparedCounter = preparedCounter # This is the counter of the highest accepted prepared ballot--maintained identically to the "prepared" field in the PREPARE phase. Since the "value" field will always be the same as "ballot", only the counter is sent in the COMMIT phase
        self.hCounter = hCounter
        self.cCounter = cCounter

    def __repr__(self):
        return (f"SCPCommit(ballot={self.ballot}, preparedCounter={self.preparedCounter}, hCounter={self.hCounter}, cCounter={self.cCounter})")
