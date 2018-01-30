# -*- coding:utf-8 -*-
#
# Copyright (C) 2018, Maximilian Köhl <mail@koehlma.de>

import itertools
import typing


class Manager:
    """ Manager for boolean formulas and operations on them. """

    def __init__(self):
        self.counter = itertools.count()
        self.variables: typing.Dict[int, 'Variable'] = {}
        # initialize constants
        self.true = self.verum = Verum(self)
        self.false = self.falsum = Falsum(self)
        # variable ordering
        self.ordering: typing.Dict['Variable', int] = {}

    def __getitem__(self, index: int) -> 'Variable':
        try:
            return self.variables[index]
        except KeyError:
            raise ValueError(f'Variable with index {index} does not exist!')

    def greater(self, left: 'Variable', right: 'Variable'):
        return self.ordering[left] > self.ordering[right]

    def less(self, left: 'Variable', right: 'Variable'):
        return self.ordering[left] < self.ordering[right]

    def sort(self, variables: typing.Sequence['Variable']) -> typing.List['Variable']:
        return list(sorted(variables, key=lambda variable: self.ordering[variable]))

    def swap(self, variable0: 'Variable', variable1: 'Variable'):
        (self.ordering[variable0],
         self.ordering[variable1]) = self.ordering[variable1], self.ordering[variable0]

    def variable(self, name=None) -> 'Variable':
        index = next(self.counter)
        self.variables[index] = Variable(self, index, name)
        self.ordering[variable] = index
        return self.variables[index]


class Formula:
    """ Represents a boolean formula. """

    precedence = 0

    def __init__(self, manager: Manager):
        self.manager = manager

    def __hash__(self):
        return hash((self.manager, self.__class__))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.manager == other.manager

    def __ne__(self, other):
        return not self == other

    def __invert__(self) -> 'Not':
        return Not(self.manager, self)

    def __and__(self, other: 'Formula') -> 'And':
        return And(self.manager, self, other)

    def __or__(self, other: 'Formula') -> 'Or':
        return Or(self.manager, self, other)

    def __xor__(self, other: 'Formula') -> 'Xor':
        return Xor(self.manager, self, other)

    def __lshift__(self, other: 'Formula') -> 'Implication':
        return Implication(self.manager, other, self)

    def __rshift__(self, other: 'Formula') -> 'Implication':
        return Implication(self.manager, self, other)

    def equivalent(self, other: 'Formula') -> 'Equivalence':
        return Equivalence(self.manager, self, other)

    equals = equivalent

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        raise NotImplementedError()

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        raise NotImplementedError()

    def variables(self) -> typing.Set['Variable']:
        raise NotImplementedError()

    def simplify(self):
        return self.evaluate({})


def _parenthesize(formula, outer_precedence):
    return f'({formula})' if formula.precedence < outer_precedence else f'{formula}'


class Constant(Formula):
    precedence = 20
    symbol = ''

    def __str__(self):
        return self.symbol

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        return self

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        return self

    def variables(self) -> typing.Set['Variable']:
        return set()


class Verum(Constant):
    symbol = '⊤'


class Falsum(Constant):
    symbol = '⊥'


class Variable(Formula):
    precedence = 19

    def __init__(self, manager, index, name=None):
        super().__init__(manager)
        self.index = index
        self.name = name

    def __str__(self):
        return self.name or f'_{self.index}'

    def __hash__(self):
        return hash((super().__hash__(), self.index))

    def __eq__(self, other):
        return super().__eq__(other) and self.index == other.index

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        return formula if variable == self else self

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        return assignment[self] if self in assignment else self

    def variables(self) -> typing.Set['Variable']:
        return {self}


class Not(Formula):
    precedence = 18

    def __init__(self, manager: Manager, operand: Formula):
        super().__init__(manager)
        self.operand: Formula = operand

    def __str__(self):
        operand = _parenthesize(self.operand, self.precedence)
        return f'¬{operand}'

    def __hash__(self):
        return hash((super().__hash__(), self.operand))

    def __eq__(self, other):
        return super().__eq__(self) and other.operand == self.operand

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        operand = self.operand.compose(variable, formula)
        return self if operand == self.operand else Not(self.manager, operand)

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        operand = self.operand.evaluate(assignment)
        if operand == self.manager.verum:
            return self.manager.falsum
        elif operand == self.manager.falsum:
            return self.manager.verum
        return Not(self.manager, operand)

    def variables(self) -> typing.Set['Variable']:
        return self.operand.variables()


class BinaryOperator(Formula):
    operator = ''

    def __init__(self, manager: Manager, left: Formula, right: Formula):
        super().__init__(manager)
        self.left = left
        self.right = right

    def __str__(self):
        left = _parenthesize(self.left, self.precedence)
        right = _parenthesize(self.right, self.precedence)
        return f'{left} {self.operator} {right}'

    def __hash__(self):
        return hash((super().__hash__(), self.left, self.right))

    def __eq__(self, other):
        return (super().__eq__(other) and
                other.left == self.left and
                other.right == self.right)

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        left = self.left.compose(variable, formula)
        right = self.right.compose(variable, formula)
        return type(self)(self.manager, left, right)

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        left = self.left.evaluate(assignment)
        right = self.right.evaluate(assignment)
        return self._evaluate(left, right)

    def variables(self) -> typing.Set['Variable']:
        return self.left.variables() | self.right.variables()

    def _evaluate(self, left: Formula, right: Formula):
        raise NotImplementedError()


class And(BinaryOperator):
    precedence = 10
    operator = '∧'

    def _evaluate(self, left: Formula, right: Formula):
        if left == self.manager.verum and right == self.manager.verum:
            return self.manager.verum
        elif left == self.manager.falsum or right == self.manager.falsum:
            return self.manager.falsum
        elif left == self.manager.verum:
            return right
        elif right == self.manager.verum:
            return left
        return And(self.manager, left, right)


class Or(BinaryOperator):
    precedence = 9
    operator = '∨'

    def _evaluate(self, left: Formula, right: Formula):
        if left == self.manager.verum or right == self.manager.verum:
            return self.manager.verum
        elif left == self.manager.falsum and right == self.manager.falsum:
            return self.manager.falsum
        return Or(self.manager, left, right)


class Xor(BinaryOperator):
    precedence = 8
    operator = '⊕'

    def _evaluate(self, left: Formula, right: Formula):
        if left == self.manager.verum and right == self.manager.verum:
            return self.manager.falsum
        elif left == self.manager.falsum:
            return right
        elif right == self.manager.falsum:
            return left
        return Xor(self.manager, left, right)


class Implication(BinaryOperator):
    precedence = 7
    operator = '→'

    def _evaluate(self, left: Formula, right: Formula):
        if left == self.manager.falsum or right == self.manager.verum:
            return self.manager.verum
        elif left == self.manager.verum:
            return right
        return Implication(self.manager, left, right)


class Equivalence(BinaryOperator):
    precedence = 6
    operator = '↔'

    def _evaluate(self, left: Formula, right: Formula):
        if left == right:
            return self.manager.verum
        return Equivalence(self.manager, left, right)


class ITE(Formula):
    precedence = 15

    def __init__(self,
                 manager: Manager,
                 condition: Formula,
                 consequence: Formula,
                 alternative: Formula):
        super().__init__(manager)
        self.condition = condition
        self.consequence = consequence
        self.alternative = alternative

    def __str__(self):
        return f'ite({self.condition}, {self.consequence}, {self.alternative})'

    def __hash__(self):
        return hash((super().__hash__(), self.condition,
                     self.consequence, self.alternative))

    def __eq__(self, other):
        return (super().__eq__(other) and
                other.condition == self.condition and
                other.consequnce == self.consequence and
                other.alternative == self.alternative)

    def compose(self, variable: 'Variable', formula: 'Formula') -> 'Formula':
        condition = self.condition.compose(variable, formula)
        consequence = self.consequence.compose(variable, formula)
        alternative = self.alternative.compose(variable, formula)
        return ITE(self.manager, condition, consequence, alternative)

    def evaluate(self, assignment: typing.Mapping['Variable', 'Constant']):
        condition = self.condition.evaluate(assignment)
        consequence = self.consequence.evaluate(assignment)
        alternative = self.alternative.evaluate(assignment)
        if condition is self.manager.verum:
            return consequence
        elif condition is self.manager.falsum:
            return alternative
        else:
            return ITE(self.manager, condition, consequence, alternative)

    def variables(self) -> typing.Set['Variable']:
        return (self.condition.variables() |
                self.consequence.variables() |
                self.alternative.variables())


_default_manager = Manager()

variable = _default_manager.variable
true = _default_manager.verum
false = _default_manager.falsum


def variables(names):
    return [_default_manager.variable(name) for name in names]
