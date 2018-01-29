# -*- coding:utf-8 -*-
#
# Copyright (C) 2018, Maximilian Köhl <mail@koehlma.de>

import typing

Vertex = typing.TypeVar('Vertex')
Edge = typing.Tuple[Vertex, Vertex]

Vertices = typing.AbstractSet[Vertex]
Edges = typing.AbstractSet[Edge]

FrozenVertices = typing.FrozenSet[Vertex]
FrozenEdges = typing.FrozenSet[Edge]

Generic = typing.Generic[Vertex]


class InvalidArena(Exception):
    """ Thrown when an invalid arena is constructed. """


class Arena(Generic):
    """
    An *arena* A = (V, V₀, V₁, E) consists of a finite set V of vertices, disjoint sets
    V₀ ⊆ V and V₁ ⊆ V with V₀ ∪ V₁ = V denoting the vertices of Player 0 and Player 1
    respectively, and a set E of edges without terminal vertices.
    """

    def __init__(self,
                 vertices: Vertices,
                 player0: Vertices,
                 player1: Vertices,
                 edges: Edges):
        self._vertices: FrozenVertices = frozenset(vertices)
        self._player0: FrozenVertices = frozenset(player0)
        self._player1: FrozenVertices = frozenset(player1)
        self._edges: FrozenEdges = frozenset(edges)
        # some caches for efficiency
        self._successors: typing.Dict[Vertex, FrozenVertices] = {}
        self._predecessors: typing.Dict[Vertex, FrozenVertices] = {}
        # verify that the arena is valid
        self._verify()

    def _verify(self):
        """ Verifies that the arena is valid. """
        if self.player0 & self.player1:
            raise InvalidArena('Player 0 and Player 1 vertices are not disjoint!')
        if self.player0 | self.player1 != self.vertices:
            raise InvalidArena('Player 0 and Player 1 vertices are not a V-partition!')
        for vertex in self.vertices:
            if not self.successors(vertex):
                raise InvalidArena(f'Vertex {vertex!r} has no successors!')

    @property
    def vertices(self) -> FrozenVertices:
        """ The vertices V of the arena. """
        return self._vertices

    @property
    def player0(self) -> FrozenVertices:
        """ The vertices V₀ of Player 0. """
        return self._player0

    @property
    def player1(self) -> FrozenVertices:
        """ The vertices V₁ of Player 1. """
        return self._player1

    @property
    def edges(self) -> FrozenEdges:
        """ The edges of the arena. """
        return self._edges

    def successors(self, vertex: Vertex) -> FrozenVertices:
        """ Returns the successors of the given vertex. """
        if vertex not in self._successors:
            self._successors[vertex] = frozenset(
                successor for successor in self.vertices
                if (vertex, successor) in self.edges
            )
        return self._successors[vertex]

    def predecessors(self, vertex: Vertex) -> FrozenVertices:
        """ Returns the predecessors of the given vertex. """
        if vertex not in self._predecessors:
            self._predecessors[vertex] = frozenset(
                predecessor for predecessor in self.vertices
                if (predecessor, vertex) in self.edges
            )
        return self._predecessors[vertex]

    def dual(self) -> 'Arena':
        """ Returns the dual of the arena. """
        return Arena(self.vertices, self.player1, self.player0, self.edges)

    def attractor0(self, vertices: Vertices) -> Vertices:
        """ Returns the Player 0 attractor of the given vertices. """
        return attractor(self, vertices, self.player0, self.player1)

    def attractor1(self, vertices: Vertices) -> Vertices:
        """ Returns the Player 1 attractor of the given vertices. """
        return attractor(self, vertices, self.player1, self.player0)

    def controlled_predecessors0(self, vertices: Vertices) -> Vertices:
        """ Returns the Player 0 controlled predecessors of the given vertices. """
        return controlled_predecessors(self, vertices, self.player0, self.player1)

    def controlled_predecessors1(self, vertices: Vertices) -> Vertices:
        """ Returns the Player 1 controlled predecessors of the given vertices. """
        return controlled_predecessors(self, vertices, self.player1, self.player0)


def controlled_predecessors(arena: Arena,
                            targets: Vertices,
                            own: Vertices,
                            other: Vertices) -> Vertices:
    """ Computes the set of controlled predecessors for the respective player. """
    return ({vertex for vertex in own if arena.successors(vertex) & targets} |
            {vertex for vertex in other if arena.successors(vertex) <= targets})


def attractor_fixpoint(arena: Arena,
                       vertices: Vertices,
                       own: Vertices,
                       other: Vertices) -> Vertices:
    """ Computes the attractor of the given vertices for the respective player. """
    current = frozenset(vertices)
    previous = frozenset()
    while current != previous:
        previous = current
        current = current | controlled_predecessors(arena, current, own, other)
    return current


def attractor_efficient(arena: Arena,
                        vertices: Vertices,
                        own: Vertices,
                        other: Vertices) -> Vertices:
    """ Computes the attractor of the given vertices for the respective player. """
    coloring = {}
    for vertex in arena.vertices:
        if vertex in vertices:
            coloring[vertex] = 0
        elif vertex in own:
            coloring[vertex] = 1
        elif vertex in other:
            coloring[vertex] = len(arena.successors(vertex))
    pending = set(vertices)
    while pending:
        vertex = pending.pop()
        for predecessor in arena.predecessors(vertex):
            if coloring[predecessor] > 0:
                coloring[predecessor] -= 1
                if coloring[predecessor] == 0:
                    pending.add(vertex)
    return frozenset(vertex for vertex, color in coloring.items() if color == 0)


# select the attractor algorithm to be used
attractor = attractor_efficient
