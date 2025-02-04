"""
=========================
State
=========================

Author: Matija Piskorec
Last update: August 2023

State class.
"""

from Log import log
import enum

class State(enum.Enum):

    none = enum.auto()
    init = enum.auto()
    vote = enum.auto()
    accept = enum.auto()
    confirm = enum.auto()

    @classmethod
    def from_value(cls, value):
        for i in cls:
            if i.value == value:
                return i

        return None

    @classmethod
    def from_name(cls, name):
        return getattr(cls, name)

    @classmethod
    def get_from_value(cls, v):
        for i in list(cls):
            if i.value == v:
                return i

        return

    def get_next(self):
        for i in list(self.__class__):
            if i.value > self.value:
                return i

        return None

    # # TODO: For some reason __repr__ doesn't work for State so we have to use __str__!
    # def __str__(self):
    # # def __repr__(self):
    #     return self.name

    def is_next(self, state):
        return state.value > self.value

    def __gt__(self, state):
        return self.value > state.value

    def __lt__(self, state):
        return self.value < state.value

    def __ge__(self, state):
        return self.value >= state.value

    def __le__(self, state):
        return self.value <= state.value

    def __eq__(self, state):
        return self.value == state.value

