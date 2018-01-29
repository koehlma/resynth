# -*- coding:utf-8 -*-
#
# Copyright (C) 2018, Maximilian Köhl <mail@koehlma.de>

from .arena import Generic, Vertices, Arena
from .condition import Condition


class Game(Generic):
    """ A game G = (A, Win) consists of an arena and a winning condition. """

    def __init__(self, arena: Arena, condition: Condition):
        self.arena: Arena = arena
        self.condition: Condition = condition
        # ensure condition is compatible with arena
        self.condition.check(self.arena)

    def winning_region0(self) -> Vertices:
        """ Returns the winning region of Player 0. """
        return self.condition.winning_region0(self.arena)

    def winning_region1(self) -> Vertices:
        """ Returns the winning region of Player 1. """
        return self.condition.winning_region1(self.arena)

    def dual(self) -> 'Game':
        """ Returns the dual of the game. """
        condition = self.condition.complement(self.arena)
        return Game(self.arena.dual(), condition)
