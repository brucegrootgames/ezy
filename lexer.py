"""
Ezy Lexer
=========

Stage 1 of the interpreter: turn raw source text into a flat list of *tokens*.

A token is just a small labelled chunk of the program, e.g. the text `say`
becomes a KEYWORD token and `"Hello"` becomes a STRING token. Working with
tokens is much easier than working with raw characters, because the parser
(stage 2) can then think in terms of words instead of letters.

The only tricky part is indentation. Like Python, Ezy uses indentation to mark
blocks. We track the current indentation on a stack and emit special INDENT and
DEDENT tokens whenever it changes. We are *forgiving* about tabs vs spaces by
expanding tabs to the next multiple of 8 columns before measuring.
"""

from errors import EzyError


# Words that have special meaning. Everything else that looks like a word is
# treated as a NAME (a variable or function name).
KEYWORDS = {
    "say", "ask", "let", "be", "change", "to",
    "if", "otherwise", "repeat", "times", "while",
    "make", "with", "give", "back",
    "and", "or", "not",
    "is", "bigger", "smaller", "greater", "less", "than", "at", "least", "most",
    "text", "number", "length", "of",
    "yes", "no", "true", "false",
}

# Single-character operators / punctuation.
SYMBOLS = {"+", "-", "*", "/", "(", ")", ","}


class Token:
    def __init__(self, kind, value, line, col):
        self.kind = kind      # e.g. "KEYWORD", "NAME", "NUMBER", "STRING", ...
        self.value = value    # the actual text / parsed value
        self.line = line      # 1-based line number, used for friendly errors
        self.col = col        # 1-based column number

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r}, line={self.line})"


def tokenize(source):
    """Turn an Ezy program (a string) into a list of Token objects."""
    tokens = []
    indent_stack = [0]            # column widths of currently open blocks
    # Many Windows editors save a "byte order mark" at the very start of a
    # file. Quietly drop it so beginners never have to know it exists.
    source = source.lstrip("﻿")
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = source.split("\n")

    for line_no, raw_line in enumerate(lines, start=1):
        # --- Measure indentation, expanding tabs to a tab-stop of 8. ---
        col = 0
        i = 0
        while i < len(raw_line) and raw_line[i] in " \t":
            if raw_line[i] == "\t":
                col += 8 - (col % 8)
            else:
                col += 1
            i += 1

        rest = raw_line[i:]

        # Skip blank lines and full-line comments entirely: they have no
        # tokens and should not affect indentation.
        if rest == "" or rest.startswith("#"):
            continue

        # --- Emit INDENT / DEDENT based on how this line's indent compares. ---
        if col > indent_stack[-1]:
            indent_stack.append(col)
            tokens.append(Token("INDENT", None, line_no, 1))
        else:
            while col < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token("DEDENT", None, line_no, 1))
            if col != indent_stack[-1]:
                raise EzyError(
                    "The spacing at the start of this line doesn't line up "
                    "with any block above it.",
                    line_no,
                    hint="Make sure indented lines use a consistent amount of "
                         "spacing. Try lining this line up with the ones around it.",
                )

        # --- Tokenize the rest of the line, character by character. ---
        _tokenize_line(rest, line_no, i + 1, tokens)

        tokens.append(Token("NEWLINE", None, line_no, len(raw_line) + 1))

    # Close any blocks still open at end of file.
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token("DEDENT", None, len(lines), 1))

    tokens.append(Token("EOF", None, len(lines) + 1, 1))
    return tokens


def _tokenize_line(text, line_no, start_col, tokens):
    """Scan one line of code (indentation already removed) into tokens."""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        col = start_col + i

        # Whitespace between tokens.
        if ch in " \t":
            i += 1
            continue

        # Comment to end of line.
        if ch == "#":
            break

        # Strings.
        if ch == '"':
            value, length = _read_string(text, i, line_no)
            tokens.append(Token("STRING", value, line_no, col))
            i += length
            continue

        # Numbers (integer or decimal).
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            value, length = _read_number(text, i, line_no)
            tokens.append(Token("NUMBER", value, line_no, col))
            i += length
            continue

        # Words: keywords, booleans, or names.
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            if word in KEYWORDS:
                tokens.append(Token("KEYWORD", word, line_no, col))
            else:
                tokens.append(Token("NAME", word, line_no, col))
            i = j
            continue

        # Symbols / operators.
        if ch in SYMBOLS:
            tokens.append(Token("OP", ch, line_no, col))
            i += 1
            continue

        # Anything else is a character Ezy doesn't understand.
        raise EzyError(
            f"I found a character I don't understand: '{ch}'.",
            line_no,
            hint="Ezy uses words like 'say' and 'if', and the symbols + - * / "
                 "( ) and commas. Did you mean something else?",
        )


def _read_string(text, start, line_no):
    """Read a "double quoted" string starting at index `start`."""
    i = start + 1   # skip opening quote
    chars = []
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            chars.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        if ch == '"':
            return "".join(chars), (i - start + 1)
        chars.append(ch)
        i += 1

    raise EzyError(
        "This piece of text is missing its closing quote mark.",
        line_no,
        hint='Every piece of text needs quotes on both ends, like "hello".',
    )


def _read_number(text, start, line_no):
    """Read an integer or decimal number starting at index `start`."""
    i = start
    seen_dot = False
    while i < len(text) and (text[i].isdigit() or text[i] == "."):
        if text[i] == ".":
            if seen_dot:
                break          # a second dot ends the number
            seen_dot = True
        i += 1
    raw = text[start:i]
    value = float(raw) if seen_dot else int(raw)
    return value, (i - start)
