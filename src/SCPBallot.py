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