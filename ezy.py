#!/usr/bin/env python3
"""
Ezy -- a tiny, friendly programming language for absolute beginners.

Usage:
    python ezy.py program.ezy     # run a program file
    python ezy.py                 # start the interactive REPL

This file ties the three stages together:
    1. lexer.tokenize   -> tokens
    2. parser.parse     -> AST
    3. interpreter.run  -> runs it

It also owns all the friendly error printing.
"""

import sys

# Make sure text (friendly errors, anything a program prints) shows up even on
# terminals whose default encoding can't handle accents or emoji.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from lexer import tokenize
from parser import parse
from interpreter import Interpreter
from errors import EzyError


def run_source(source, interpreter):
    """Tokenize, parse, and run one chunk of Ezy source with a given interpreter."""
    tokens = tokenize(source)
    program = parse(tokens)
    interpreter.run(program)


def run_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"Ezy couldn't open the file '{path}': {e}")
        return 1

    interpreter = Interpreter()
    try:
        run_source(source, interpreter)
    except EzyError as err:
        print(err.friendly())
        return 1
    except RecursionError:
        print("Oops! A function called itself too many times and Ezy ran out "
              "of room.\n  Hint: make sure your function eventually stops "
              "calling itself ('give back' without another call).")
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 1
    return 0


def repl():
    """A simple interactive prompt.

    Single-line statements run immediately. If you type a line that starts a
    block (if / repeat / make), keep typing indented lines and finish with a
    blank line to run the whole block.
    """
    print("Ezy REPL -- type Ezy code and press Enter.")
    print('Try:  say "Hello!"      Type  bye  or press Ctrl+C to leave.\n')
    interpreter = Interpreter()

    while True:
        try:
            line = input("ezy> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if line.strip() in ("bye", "exit", "quit"):
            print("Bye!")
            break
        if line.strip() == "":
            continue

        # If this line opens a block, gather indented continuation lines until
        # the user enters a blank line.
        source_lines = [line]
        if _starts_block(line):
            while True:
                try:
                    cont = input("...  ")
                except (EOFError, KeyboardInterrupt):
                    break
                if cont.strip() == "":
                    break
                source_lines.append(cont)

        try:
            run_source("\n".join(source_lines), interpreter)
        except EzyError as err:
            print(err.friendly())
        except RecursionError:
            print("Oops! A function called itself too many times.")


def _starts_block(line):
    stripped = line.strip()
    return any(stripped.startswith(k + " ") or stripped == k
               for k in ("if", "repeat", "make"))


def main(argv):
    if len(argv) == 1:
        repl()
        return 0
    if len(argv) == 2:
        return run_file(argv[1])
    print("Usage: python ezy.py [program.ezy]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
