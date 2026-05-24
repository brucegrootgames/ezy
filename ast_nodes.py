"""
AST node definitions for Ezy.

Stage 2 (the parser) builds a tree out of these little classes. Each node is a
dumb data container -- it just remembers its parts and the line it came from
(so we can show good error messages later). Stage 3 (the interpreter) walks the
tree and actually *does* things.

We keep the nodes as plain classes for readability.
"""


class Node:
    """Base class so every node can carry a line number."""
    line = None


# ----- Statements -----------------------------------------------------------

class Say(Node):
    def __init__(self, expr, line):
        self.expr, self.line = expr, line


class Ask(Node):
    def __init__(self, name, prompt, line):
        self.name, self.prompt, self.line = name, prompt, line


class Assign(Node):
    """`let X be ...` and `change X to ...` both produce this."""
    def __init__(self, name, expr, line):
        self.name, self.expr, self.line = name, expr, line


class If(Node):
    def __init__(self, branches, else_block, line):
        # branches: list of (condition_expr, list_of_statements)
        self.branches, self.else_block, self.line = branches, else_block, line


class RepeatTimes(Node):
    def __init__(self, count, body, line):
        self.count, self.body, self.line = count, body, line


class RepeatWhile(Node):
    def __init__(self, condition, body, line):
        self.condition, self.body, self.line = condition, body, line


class MakeFunc(Node):
    def __init__(self, name, params, body, line):
        self.name, self.params, self.body, self.line = name, params, body, line


class GiveBack(Node):
    def __init__(self, expr, line):
        self.expr, self.line = expr, line


class CallStmt(Node):
    """A function call used as a whole statement, e.g. `greet with "Sam"`."""
    def __init__(self, name, args, line):
        self.name, self.args, self.line = name, args, line


# ----- Expressions ----------------------------------------------------------

class Literal(Node):
    """A number, piece of text, or boolean written directly in the source."""
    def __init__(self, value, line):
        self.value, self.line = value, line


class Var(Node):
    def __init__(self, name, line):
        self.name, self.line = name, line


class BinOp(Node):
    """Arithmetic: + - * /"""
    def __init__(self, op, left, right, line):
        self.op, self.left, self.right, self.line = op, left, right, line


class Compare(Node):
    """Comparisons: == != > < >= <= (written in words in the source)."""
    def __init__(self, op, left, right, line):
        self.op, self.left, self.right, self.line = op, left, right, line


class LogicOp(Node):
    """`and` / `or`."""
    def __init__(self, op, left, right, line):
        self.op, self.left, self.right, self.line = op, left, right, line


class Not(Node):
    def __init__(self, operand, line):
        self.operand, self.line = operand, line


class Neg(Node):
    """Unary minus, e.g. -5."""
    def __init__(self, operand, line):
        self.operand, self.line = operand, line


class Convert(Node):
    """`text of X`, `number of X`, `length of X`."""
    def __init__(self, kind, operand, line):
        self.kind, self.operand, self.line = kind, operand, line


class Call(Node):
    """A function call used as a value, e.g. `add with 3, 4`."""
    def __init__(self, name, args, line):
        self.name, self.args, self.line = name, args, line
