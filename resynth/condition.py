# -*- coding:utf-8 -*-
#
# Copyright (C) 2018, Maximilian Köhl <mail@koehlma.de>

import typing

from .arena import Generic, Vertex, Vertices, FrozenVertices, Arena


class IncompatibleArena(Exception):
    pass


class UnsupportedOperation(Exception):
    pass


class Condition(Generic):
    """ Represents a winning condition. """

    def check(self, arena: Arena):
        """ Ensures that the arena is compatible with the winning condition. """
        raise NotImplementedError()

    def complement(self, arena: Arena):
        """ Returns the complement of the winning condition. """
        raise UnsupportedOperation('Unable to compute complement of given condition.')

    def winning_region0(self, arena: Arena) -> Vertices:
        """ Computes the winning region of Player 0 in the given arena. """
        raise NotImplementedError()

    def winning_region1(self, arena: Arena) -> Vertices:
        """ Computes the winning region of Player 1 in the given arena. """
        raise NotImplementedError()


class Reachability(Condition):
    """
    Reachability winning condition.

    The goal of Player 0 is to reach the goal vertices.

    REACH(R) := {ρ ∈ ω(V) | Occ(ρ) ∩ R ≠ ∅}

    LTL: F(v ∈ R)
    """

    def __init__(self, goal_vertices: Vertices):
        self.goal_vertices: FrozenVertices = frozenset(goal_vertices)

    def __repr__(self):
        return f'Reachability({set(self.goal_vertices)!r})'

    def check(self, arena: Arena):
        if not self.goal_vertices <= arena.vertices:
            raise IncompatibleArena('Goal vertices must be a subset of the vertices.')

    def complement(self, arena: Arena):
        # do never reach the goal vertices
        return Safety(arena.vertices - self.goal_vertices)

    def winning_region0(self, arena: Arena) -> Vertices:
        return arena.attractor0(self.goal_vertices)

    def winning_region1(self, arena: Arena):
        return arena.vertices - self.winning_region0(arena)


class Safety(Condition):
    """
    Safety winning condition.

    The goal of Player 0 is to avoid the unsafe vertices.

    SAFETY(S) := {ρ ∈ ω(V) | Occ(ρ) ⊆ S}

    LTL: G(v ∈ S)
    """

    def __init__(self, safe_vertices: Vertices):
        self.safe_vertices: FrozenVertices = frozenset(safe_vertices)

    def __repr__(self):
        return f'Safety({set(self.safe_vertices)!r})'

    def check(self, arena: Arena):
        if not self.safe_vertices <= arena.vertices:
            raise IncompatibleArena('Safe vertices must be a subset of the vertices.')

    def complement(self, arena: Arena):
        # reach an unsafe vertex
        return Reachability(arena.vertices - self.safe_vertices)

    def winning_region0(self, arena: Arena) -> Vertices:
        return arena.vertices - self.winning_region1(arena)

    def winning_region1(self, arena: Arena):
        return arena.attractor1(arena.vertices - self.safe_vertices)


class Recurrence(Condition):
    """
    Recurrence or Büchi winning condition.

    The goal of Player 0 is to visit the accepting vertices infinitely often.

    BÜCHI(F) := {ρ ∈ ω(V) | Inf(ρ) ∩ F ≠ ∅}

    LTL: GF(v ∈ F)
    """

    def __init__(self, accepting_vertices: Vertices):
        self.accepting_vertices = accepting_vertices

    def __repr__(self):
        return f'Recurrence({set(self.accepting_vertices)!r})'

    def check(self, arena: Arena):
        if self.accepting_vertices <= arena.vertices:
            return
        raise IncompatibleArena('Accepting vertices must be a subset of the vertices.')

    def complement(self, arena: Arena):
        # avoid accepting vertices globally eventually
        return Persistence(arena.vertices - self.accepting_vertices)

    def winning_region0(self, arena: Arena) -> Vertices:
        return arena.vertices - self.winning_region1(arena)

    def winning_region1(self, arena: Arena) -> Vertices:
        accepting_vertices = set(self.accepting_vertices)
        # winning region of Player 1 is a trap for Player 0; we use a fixpoint algorithm
        # here which iteratively adds vertices to Player 1's winning region approximation
        previous = set()
        current = None
        # check whether we reached a fixpoint yet
        while previous != current:
            previous = current
            # compute the set of vertices from which Player 0 cannot force the game to the
            # accepting vertices via the complement of the Player 0's attractor
            current = arena.vertices - arena.attractor0(accepting_vertices)
            # `current` under-approximates the winning region as Player 1 can force the
            # game away from the accepting vertices; we remove those vertices from the
            # accepting vertices from which Player 1 can force Player 0 in the current
            # under-approximation of its winning region
            accepting_vertices -= arena.controlled_predecessors1(current)
        return current


class Persistence(Condition):
    """
    Persistence or co-Büchi winning condition.

    The goal of Player 0 is to globally avoid unsafe vertices eventually.

    coBÜCHI(C) := {ρ ∈ ω(V) | Inf(ρ) ⊆ C}

    LTL: FG(v ∈ C)
    """

    def __init__(self, safe_vertices: Vertices):
        self.safe_vertices = safe_vertices

    def __repr__(self):
        return f'Persistence({set(self.safe_vertices)!r})'

    def check(self, arena: Arena):
        if self.safe_vertices <= arena.vertices:
            return
        raise IncompatibleArena('Safe vertices must be a subset of the vertices.')

    def complement(self, arena: Arena):
        # visit unsafe vertices infinitely often
        return Recurrence(arena.vertices - self.safe_vertices)

    def winning_region0(self, arena: Arena) -> Vertices:
        # over-approximation of the unsafe vertices, i.e., those vertices from which
        # Player 1 can force the game away from staying within safe vertices
        unsafe_vertices = set(arena.vertices - self.safe_vertices)
        previous = set()
        current = None
        while previous != current:
            previous = current
            # under-approximate the winning region using the over-approximation of the
            # unsafe vertices; compute the set of vertices from which Player 1 cannot
            # force the game into unsafe vertices
            current = arena.vertices - arena.attractor1(unsafe_vertices)
            # `current` under-approximates the winning region as Player 0 can force the
            # game to stay within safe vertices; we remove those vertices from the unsafe
            # vertices from which Player 0 can force Player 1 in the current under-
            # approximation of its winning region
            unsafe_vertices -= arena.controlled_predecessors0(current)
        return current

    def winning_region1(self, arena: Arena) -> Vertices:
        return arena.vertices - self.winning_region0(arena)


class Parity(Condition):
    """
    Parity winning condition.

    The goal of Player 0 is to ensure that the maximum coloring
    visited infinitely often is even.

    PARITY(Ω) := {ρ ∈ ω(V) | max Inf(Ω(ρ)) is even}
    """

    def __init__(self, coloring: typing.Mapping[Vertex, int]):
        self.coloring = dict(coloring)

    def __repr__(self):
        return f'Parity({self.mapping!r})'

    def check(self, arena: Arena):
        if not arena.vertices <= self.coloring.keys():
            raise IncompatibleArena('Every vertex must be assigned a color.')

    def winning_region0(self, arena: Arena) -> Vertices:
        # TODO: implement winning region computation
        raise NotImplementedError()

    def winning_region1(self, arena: Arena) -> Vertices:
        # TODO: implement winning region computation
        raise NotImplementedError()
