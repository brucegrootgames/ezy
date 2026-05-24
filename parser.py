"""
Ezy Parser
==========

Stage 2: turn the flat list of tokens into an Abstract Syntax Tree (AST) -- a
nested structure that captures the *meaning* of the program.

For example the tokens for `let score be 10` become an Assign node holding the
name "score" and a Literal node for 10.

The parser is a hand-written "recursive descent" parser: there is roughly one
method per grammar rule, and the methods call each other the way the grammar
nests. Expression precedence (so that `2 + 3 * 4` means `2 + (3 * 4)`) is
handled by layering the methods: or -> and -> not -> comparison -> +/- -> */ .
"""

import ast_nodes as A
from errors import EzyError


# How the comparison words map onto operators. Longer phrases are checked first.
COMPARISONS = [
    (["is", "not"], "!="),
    (["is", "bigger", "than"], ">"),
    (["is", "greater", "than"], ">"),
    (["is", "smaller", "than"], "<"),
    (["is", "less", "than"], "<"),
    (["is", "at", "least"], ">="),
    (["is", "at", "most"], "<="),
    (["is"], "=="),
]


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---- low-level token helpers ------------------------------------------

    def peek(self, offset=0):
        return self.tokens[self.pos + offset]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def at(self, kind, value=None):
        tok = self.peek()
        if tok.kind != kind:
            return False
        return value is None or tok.value == value

    def at_keyword(self, *words):
        tok = self.peek()
        return tok.kind == "KEYWORD" and tok.value in words

    def expect(self, kind, value=None, what=None):
        if not self.at(kind, value):
            tok = self.peek()
            want = what or (value or kind)
            raise EzyError(
                f"I expected {want} here but found '{self._describe(tok)}'.",
                tok.line,
                hint="Check the spelling and the order of the words on this line.",
            )
        return self.advance()

    def _describe(self, tok):
        if tok.kind in ("NEWLINE", "EOF"):
            return "the end of the line"
        if tok.kind in ("INDENT", "DEDENT"):
            return "a change in spacing"
        return str(tok.value)

    def skip_newlines(self):
        while self.at("NEWLINE"):
            self.advance()

    # ---- program structure ------------------------------------------------

    def parse_program(self):
        statements = []
        self.skip_newlines()
        while not self.at("EOF"):
            statements.append(self.parse_statement())
            self.skip_newlines()
        return statements

    def parse_block(self):
        """Parse an indented group of statements following a header line."""
        self.expect("NEWLINE", what="a new line before this block")
        self.skip_newlines()
        if not self.at("INDENT"):
            tok = self.peek()
            raise EzyError(
                "I expected an indented block here, but nothing was indented.",
                tok.line,
                hint="Lines that belong inside an 'if', 'repeat' or 'make' must "
                     "be indented (start with a few spaces).",
            )
        self.advance()  # consume INDENT
        statements = []
        self.skip_newlines()
        while not self.at("DEDENT") and not self.at("EOF"):
            statements.append(self.parse_statement())
            self.skip_newlines()
        if self.at("DEDENT"):
            self.advance()
        return statements

    # ---- statements -------------------------------------------------------

    def parse_statement(self):
        tok = self.peek()

        if self.at_keyword("say"):
            return self.parse_say()
        if self.at_keyword("ask"):
            return self.parse_ask()
        if self.at_keyword("let"):
            return self.parse_let()
        if self.at_keyword("change"):
            return self.parse_change()
        if self.at_keyword("if"):
            return self.parse_if()
        if self.at_keyword("repeat"):
            return self.parse_repeat()
        if self.at_keyword("make"):
            return self.parse_make()
        if self.at_keyword("give"):
            return self.parse_give_back()
        if self.at("NAME"):
            return self.parse_call_statement()

        raise EzyError(
            f"I don't know how to start a line with '{self._describe(tok)}'.",
            tok.line,
            hint="Lines usually start with a word like say, ask, let, if, "
                 "repeat, make, or the name of one of your functions.",
        )

    def parse_say(self):
        line = self.advance().line          # 'say'
        expr = self.parse_expression()
        self.end_of_statement()
        return A.Say(expr, line)

    def parse_ask(self):
        line = self.advance().line          # 'ask'
        name = self.expect("NAME", what="a variable name to store the answer in").value
        prompt = None
        if not self.at("NEWLINE"):
            prompt = self.parse_expression()
        self.end_of_statement()
        return A.Ask(name, prompt, line)

    def parse_let(self):
        line = self.advance().line          # 'let'
        name = self.expect("NAME", what="a variable name after 'let'").value
        self.expect("KEYWORD", "be", what="the word 'be' after the variable name")
        expr = self.parse_expression()
        self.end_of_statement()
        return A.Assign(name, expr, line)

    def parse_change(self):
        line = self.advance().line          # 'change'
        name = self.expect("NAME", what="a variable name after 'change'").value
        self.expect("KEYWORD", "to", what="the word 'to' after the variable name")
        expr = self.parse_expression()
        self.end_of_statement()
        return A.Assign(name, expr, line)

    def parse_if(self):
        line = self.advance().line          # 'if'
        branches = []
        condition = self.parse_expression()
        body = self.parse_block()
        branches.append((condition, body))

        else_block = None
        self.skip_newlines()
        while self.at_keyword("otherwise"):
            self.advance()                  # 'otherwise'
            if self.at_keyword("if"):
                self.advance()              # 'otherwise if'
                cond = self.parse_expression()
                blk = self.parse_block()
                branches.append((cond, blk))
                self.skip_newlines()
            else:
                else_block = self.parse_block()
                break
        return A.If(branches, else_block, line)

    def parse_repeat(self):
        line = self.advance().line          # 'repeat'
        if self.at_keyword("while"):
            self.advance()
            condition = self.parse_expression()
            body = self.parse_block()
            return A.RepeatWhile(condition, body, line)
        count = self.parse_expression()
        self.expect("KEYWORD", "times", what="the word 'times' after the count")
        body = self.parse_block()
        return A.RepeatTimes(count, body, line)

    def parse_make(self):
        line = self.advance().line          # 'make'
        name = self.expect("NAME", what="a name for your function after 'make'").value
        params = []
        if self.at_keyword("with"):
            self.advance()
            params.append(self.expect("NAME", what="a parameter name").value)
            while self.at("OP", ","):
                self.advance()
                params.append(self.expect("NAME", what="another parameter name").value)
        body = self.parse_block()
        return A.MakeFunc(name, params, body, line)

    def parse_give_back(self):
        line = self.advance().line          # 'give'
        self.expect("KEYWORD", "back", what="the word 'back' after 'give'")
        expr = None
        if not self.at("NEWLINE"):
            expr = self.parse_expression()
        self.end_of_statement()
        return A.GiveBack(expr, line)

    def parse_call_statement(self):
        name_tok = self.advance()           # NAME
        args = self.parse_call_args()
        self.end_of_statement()
        return A.CallStmt(name_tok.value, args, name_tok.line)

    def parse_call_args(self):
        """Parse the arguments of a call.

        Accepts an optional leading 'with', then a comma-separated list of
        expressions. `greet "Sam"` and `greet with "Sam"` are both fine, and a
        bare `greet` (no args) works too.
        """
        if self.at_keyword("with"):
            self.advance()
        args = []
        if self.at("NEWLINE") or self.at("EOF") or self.at("DEDENT") or self.at("OP", ")"):
            return args
        args.append(self.parse_expression())
        while self.at("OP", ","):
            self.advance()
            args.append(self.parse_expression())
        return args

    def end_of_statement(self):
        if not (self.at("NEWLINE") or self.at("EOF") or self.at("DEDENT")):
            tok = self.peek()
            raise EzyError(
                f"I found extra stuff at the end of this line: '{self._describe(tok)}'.",
                tok.line,
                hint="Each instruction goes on its own line. Did you forget a "
                     "comma, an operator, or quotes around some text?",
            )

    # ---- expressions (precedence climbing) --------------------------------

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.at_keyword("or"):
            line = self.advance().line
            right = self.parse_and()
            left = A.LogicOp("or", left, right, line)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.at_keyword("and"):
            line = self.advance().line
            right = self.parse_not()
            left = A.LogicOp("and", left, right, line)
        return left

    def parse_not(self):
        if self.at_keyword("not"):
            line = self.advance().line
            return A.Not(self.parse_not(), line)
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_addition()
        op = self.match_comparison()
        if op is not None:
            line = self.peek(-1).line
            right = self.parse_addition()
            return A.Compare(op, left, right, line)
        return left

    def match_comparison(self):
        """If the upcoming tokens spell a comparison phrase, consume it."""
        for words, op in COMPARISONS:
            if self._lookahead_keywords(words):
                for _ in words:
                    self.advance()
                return op
        return None

    def _lookahead_keywords(self, words):
        for offset, word in enumerate(words):
            tok = self.peek(offset)
            if tok.kind != "KEYWORD" or tok.value != word:
                return False
        return True

    def parse_addition(self):
        left = self.parse_term()
        while self.at("OP", "+") or self.at("OP", "-"):
            op = self.advance()
            right = self.parse_term()
            left = A.BinOp(op.value, left, right, op.line)
        return left

    def parse_term(self):
        left = self.parse_unary()
        while self.at("OP", "*") or self.at("OP", "/"):
            op = self.advance()
            right = self.parse_unary()
            left = A.BinOp(op.value, left, right, op.line)
        return left

    def parse_unary(self):
        if self.at("OP", "-"):
            line = self.advance().line
            return A.Neg(self.parse_unary(), line)
        if self.at_keyword("text", "number", "length"):
            kind_tok = self.advance()
            self.expect("KEYWORD", "of",
                        what=f"the word 'of' after '{kind_tok.value}'")
            return A.Convert(kind_tok.value, self.parse_unary(), kind_tok.line)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()

        if tok.kind == "NUMBER":
            self.advance()
            return A.Literal(tok.value, tok.line)

        if tok.kind == "STRING":
            self.advance()
            return A.Literal(tok.value, tok.line)

        if self.at_keyword("yes", "true"):
            self.advance()
            return A.Literal(True, tok.line)
        if self.at_keyword("no", "false"):
            self.advance()
            return A.Literal(False, tok.line)

        if tok.kind == "OP" and tok.value == "(":
            self.advance()
            expr = self.parse_expression()
            self.expect("OP", ")", what="a closing ')'")
            return expr

        if tok.kind == "NAME":
            self.advance()
            if self.at_keyword("with"):       # function call used as a value
                self.advance()
                args = [self.parse_expression()]
                while self.at("OP", ","):
                    self.advance()
                    args.append(self.parse_expression())
                return A.Call(tok.value, args, tok.line)
            return A.Var(tok.value, tok.line)

        raise EzyError(
            f"I expected a value here but found '{self._describe(tok)}'.",
            tok.line,
            hint="A value can be a number, text in \"quotes\", yes/no, a "
                 "variable name, or something in ( ).",
        )


def parse(tokens):
    return Parser(tokens).parse_program()
