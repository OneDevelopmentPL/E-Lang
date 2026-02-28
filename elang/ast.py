from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


# Expressions ---------------------------------------------------------------


class Expr:
    pass


@dataclass
class Literal(Expr):
    value: object


@dataclass
class Variable(Expr):
    name: str


@dataclass
class Unary(Expr):
    op: str
    right: Expr


@dataclass
class Binary(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass
class Call(Expr):
    callee: str
    args: List[Expr]


@dataclass
class ListAccess(Expr):
    list_expr: Expr
    index_expr: Expr


@dataclass
class LengthOf(Expr):
    list_expr: Expr


# Statements ---------------------------------------------------------------


class Stmt:
    pass


@dataclass
class Program(Stmt):
    statements: List[Stmt]


@dataclass
class Let(Stmt):
    name: str
    expr: Expr


@dataclass
class Set(Stmt):
    name: str
    expr: Expr


@dataclass
class Say(Stmt):
    expr: Expr


@dataclass
class DisplayValue(Stmt):
    expr: Expr


@dataclass
class If(Stmt):
    condition: Expr
    then_branch: List[Stmt]
    else_branch: Optional[List[Stmt]]


@dataclass
class While(Stmt):
    condition: Expr
    body: List[Stmt]


@dataclass
class RepeatTimes(Stmt):
    count_expr: Expr
    body: List[Stmt]


@dataclass
class FunctionDef(Stmt):
    name: str
    params: List[str]
    body: List[Stmt]


@dataclass
class Return(Stmt):
    expr: Expr


@dataclass
class CreateList(Stmt):
    name: str
    items: List[Expr]


@dataclass
class MathUpdate(Stmt):
    kind: str  # "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"
    target: str
    expr: Expr


@dataclass
class ExprStmt(Stmt):
    expr: Expr

