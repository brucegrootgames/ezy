"""
Ezy Interpreter
===============

Stage 3: walk the AST and actually run the program.

The interpreter keeps an "environment" -- a dictionary of variable names to
values -- and a separate table of user-defined functions. It visits each node
and does the right thing: a Say node prints, an Assign node stores a value, an
If node checks a condition and runs one branch, and so on.

Ezy values map onto Python values directly:
    number  -> int or float
    text    -> str
    boolean -> bool

All the careful, beginner-friendly checking (like "you can't add a number to
text") lives here.
"""

import random

import ast_nodes as A
from errors import EzyError


class Environment:
    """A scope: variables live here. Function bodies get their own child env."""
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name, line):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise EzyError(
            f"I don't know what '{name}' is.",
            line,
            hint=f"Make a variable first with: let {name} be ...   "
                 f"(check the spelling, too).",
        )

    def set_here(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        """Update an existing variable wherever it lives, else create it here."""
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        self.vars[name] = value


class Function:
    def __init__(self, node):
        self.name = node.name
        self.params = node.params
        self.body = node.body


class _Return(Exception):
    """Internal signal used by `give back` to jump out of a function."""
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self, input_fn=input, output_fn=print):
        self.globals = Environment()
        self.functions = {}
        self.input_fn = input_fn        # injectable so tests can feed input
        self.output_fn = output_fn      # injectable so tests can capture output

    def run(self, statements):
        for stmt in statements:
            self.exec_stmt(stmt, self.globals)

    # ---- statements -------------------------------------------------------

    def exec_block(self, statements, env):
        for stmt in statements:
            self.exec_stmt(stmt, env)

    def exec_stmt(self, node, env):
        method = getattr(self, "_exec_" + type(node).__name__)
        method(node, env)

    def _exec_Say(self, node, env):
        value = self.eval(node.expr, env)
        self.output_fn(ezy_str(value))

    def _exec_Ask(self, node, env):
        if node.prompt is not None:
            prompt = ezy_str(self.eval(node.prompt, env))
        else:
            prompt = ""
        answer = self.input_fn(prompt)
        env.assign(node.name, answer)       # always stored as text

    def _exec_Assign(self, node, env):
        env.assign(node.name, self.eval(node.expr, env))

    def _exec_If(self, node, env):
        for condition, body in node.branches:
            if is_truthy(self.eval(condition, env), condition.line):
                self.exec_block(body, env)
                return
        if node.else_block is not None:
            self.exec_block(node.else_block, env)

    def _exec_RepeatTimes(self, node, env):
        count = self.eval(node.count, env)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            raise EzyError(
                "The number of times to repeat must be a number.",
                node.line,
                hint="Write something like: repeat 3 times",
            )
        for _ in range(int(count)):
            self.exec_block(node.body, env)

    def _exec_RepeatWhile(self, node, env):
        guard = 0
        while is_truthy(self.eval(node.condition, env), node.line):
            self.exec_block(node.body, env)
            guard += 1
            if guard > 1_000_000:
                raise EzyError(
                    "This 'repeat while' loop ran a very long time and looks "
                    "like it will never stop.",
                    node.line,
                    hint="Make sure something inside the loop eventually makes "
                         "the condition false.",
                )

    def _exec_MakeFunc(self, node, env):
        self.functions[node.name] = Function(node)

    def _exec_GiveBack(self, node, env):
        value = self.eval(node.expr, env) if node.expr is not None else None
        raise _Return(value)

    def _exec_CallStmt(self, node, env):
        self.call_function(node.name, node.args, env, node.line)

    # ---- expressions ------------------------------------------------------

    def eval(self, node, env):
        method = getattr(self, "_eval_" + type(node).__name__)
        return method(node, env)

    def _eval_Literal(self, node, env):
        return node.value

    def _eval_Var(self, node, env):
        return env.get(node.name, node.line)

    def _eval_Neg(self, node, env):
        value = self.eval(node.operand, env)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EzyError(
                "You can only put a minus sign in front of a number.",
                node.line,
            )
        return -value

    def _eval_Not(self, node, env):
        return not is_truthy(self.eval(node.operand, env), node.line)

    def _eval_LogicOp(self, node, env):
        left = is_truthy(self.eval(node.left, env), node.line)
        if node.op == "and":
            return left and is_truthy(self.eval(node.right, env), node.line)
        return left or is_truthy(self.eval(node.right, env), node.line)

    def _eval_BinOp(self, node, env):
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        return self.apply_binop(node.op, left, right, node.line)

    def apply_binop(self, op, left, right, line):
        if op == "+":
            # Both numbers -> add. Both text -> join. Otherwise, a friendly nudge.
            if _is_number(left) and _is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            kinds = f"{kind_name(left)} and {kind_name(right)}"
            raise EzyError(
                f"You tried to add {kinds} together with '+', and Ezy isn't "
                f"sure what you meant.",
                line,
                hint="To stick text and a number together, turn the number "
                     'into text first, e.g.  "Score: " + text of score',
            )

        # The remaining operators are number-only.
        if not (_is_number(left) and _is_number(right)):
            raise EzyError(
                f"You can only use '{op}' with numbers, but you used it with "
                f"{kind_name(left)} and {kind_name(right)}.",
                line,
                hint="Maybe one of these should be a number instead of text?",
            )
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise EzyError(
                    "You tried to divide by zero, which has no answer.",
                    line,
                    hint="Make sure the number you divide by is never 0.",
                )
            result = left / right
            # Keep whole-number results looking like whole numbers.
            return int(result) if result == int(result) else result
        raise EzyError(f"Unknown operator '{op}'.", line)

    def _eval_Compare(self, node, env):
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        op = node.op

        if op == "==":
            return _equal(left, right)
        if op == "!=":
            return not _equal(left, right)

        # Ordering comparisons need two values of the same comparable kind.
        if _is_number(left) and _is_number(right):
            pass
        elif isinstance(left, str) and isinstance(right, str):
            pass
        else:
            raise EzyError(
                f"You compared {kind_name(left)} with {kind_name(right)} using "
                f"'bigger/smaller than', but those can't be compared that way.",
                node.line,
                hint="Compare numbers with numbers, or text with text.",
            )
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        raise EzyError(f"Unknown comparison '{op}'.", node.line)

    def _eval_Convert(self, node, env):
        value = self.eval(node.operand, env)
        if node.kind == "text":
            return ezy_str(value)
        if node.kind == "number":
            return self._to_number(value, node.line)
        if node.kind == "length":
            if isinstance(value, str):
                return len(value)
            raise EzyError(
                f"'length of' works on text, but you gave it {kind_name(value)}.",
                node.line,
            )
        raise EzyError(f"Unknown conversion '{node.kind}'.", node.line)

    def _to_number(self, value, line):
        if isinstance(value, bool):
            raise EzyError("Ezy can't turn yes/no into a number.", line)
        if isinstance(value, (int, float)):
            return value
        try:
            text = value.strip()
            return int(text) if _looks_like_int(text) else float(text)
        except (ValueError, AttributeError):
            raise EzyError(
                f'"{value}" doesn\'t look like a number, so Ezy can\'t turn it '
                f"into one.",
                line,
                hint="The text should contain only digits, like \"42\" or \"3.5\".",
            )

    def _eval_Call(self, node, env):
        return self.call_function(node.name, node.args, env, node.line)

    # ---- function calls ---------------------------------------------------

    def call_function(self, name, arg_nodes, env, line):
        if name == "random":
            return self._builtin_random(arg_nodes, env, line)

        if name not in self.functions:
            raise EzyError(
                f"I don't know a function called '{name}'.",
                line,
                hint=f"Define it first with:  make {name} with ...   "
                     f"(or check the spelling).",
            )
        func = self.functions[name]
        if len(arg_nodes) != len(func.params):
            raise EzyError(
                f"The function '{name}' needs {len(func.params)} value(s) "
                f"({', '.join(func.params) or 'none'}), but you gave "
                f"{len(arg_nodes)}.",
                line,
                hint=f"Call it like:  {name} with "
                     f"{', '.join(func.params) if func.params else '(nothing)'}",
            )
        call_env = Environment(parent=self.globals)
        for param, arg_node in zip(func.params, arg_nodes):
            call_env.set_here(param, self.eval(arg_node, env))
        try:
            self.exec_block(func.body, call_env)
        except _Return as r:
            return r.value
        return None

    def _builtin_random(self, arg_nodes, env, line):
        if len(arg_nodes) != 2:
            raise EzyError(
                "'random' needs two numbers: the lowest and the highest.",
                line,
                hint="Use it like:  random with 1, 10",
            )
        low = self.eval(arg_nodes[0], env)
        high = self.eval(arg_nodes[1], env)
        if not (_is_number(low) and _is_number(high)):
            raise EzyError("'random' needs two numbers.", line)
        return random.randint(int(low), int(high))


# ---- value helpers --------------------------------------------------------

def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _looks_like_int(text):
    t = text[1:] if text[:1] in "+-" else text
    return t.isdigit()


def _equal(a, b):
    # Don't let Python treat True == 1; keep beginner types distinct.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def is_truthy(value, line):
    """Decide if a value counts as 'true' in an if / while condition."""
    if isinstance(value, bool):
        return value
    raise EzyError(
        f"A yes/no answer was expected here, but I got {kind_name(value)}.",
        line,
        hint="Conditions usually use words like 'is', 'is bigger than', "
             "'and', 'or', which give a yes/no result.",
    )


def kind_name(value):
    """Beginner-friendly name for the kind of a value."""
    if isinstance(value, bool):
        return "a yes/no value"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "text"
    return "nothing"


def ezy_str(value):
    """How a value should look when printed or turned into text."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return str(int(value)) if value == int(value) else str(value)
    if value is None:
        return "nothing"
    return str(value)
