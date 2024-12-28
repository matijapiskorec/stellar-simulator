from SCPBallot import SCPBallot

class SCPExternalize:
    def __init__(self, ballot: SCPBallot, hCounter: int = 0):
        self.ballot = ballot
        self.hCounter = hCounter

    def __repr__(self):
        return (f"SCPExternalize(ballot={self.ballot}, hCounter={self.hCounter})")
