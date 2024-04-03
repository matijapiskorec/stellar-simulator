"""
=========================
State
=========================

Author: Matija Piskorec
Last update: August 2023

State class.
"""

import enum

class State(enum.Enum):
    none = enum.auto()
    init = enum.auto()
    vote = enum.auto()
    accept = enum.auto()
    confirm = enum.auto()

    @classmethod
    def from_value(cls, value):
        """Retrieves a State object from its value."""
        return cls(value)  # Use the Enum class's __call__ method for conciseness

    @classmethod
    def from_name(cls, name):
        """Retrieves a State object from its name."""
        return getattr(cls, name)

    def get_next(self):
        """Returns the State object with the next higher value."""
        try:
            return next(state for state in self.__class__ if state > self)
        except StopIteration:
            return None

    def __repr__(self):
        """String representation for the State object."""
        return self.name  # Use __repr__ for consistency



