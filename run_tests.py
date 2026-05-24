#!/usr/bin/env python3
"""
Test runner for Ezy.

Runs every program in examples/ with scripted input and checks that the
expected text shows up in the output. Run it with:

    python run_tests.py

It exits with status 0 if everything passes, 1 otherwise.
"""

import os
import random
import sys

# Make sure we can import the interpreter modules no matter where we run from.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lexer import tokenize          # noqa: E402
from parser import parse            # noqa: E402
from interpreter import Interpreter  # noqa: E402
from errors import EzyError         # noqa: E402

EXAMPLES = os.path.join(HERE, "examples")


def run_program(filename, inputs):
    """Run an example file with a list of canned input answers.

    Returns the full captured output as a single string.
    """
    path = os.path.join(EXAMPLES, filename)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    feed = iter(inputs)
    captured = []

    def fake_input(prompt=""):
        try:
            return next(feed)
        except StopIteration:
            raise AssertionError(f"{filename} asked for more input than provided")

    def capture(text):
        captured.append(str(text))

    interp = Interpreter(input_fn=fake_input, output_fn=capture)
    interp.run(parse(tokenize(source)))
    return "\n".join(captured)


# Each case: (filename, inputs, list-of-substrings-that-must-appear)
CASES = [
    (
        "hello.ezy",
        ["Caspar"],
        ["Hello, world!", "Nice to meet you, Caspar", "Welcome to Ezy!"],
    ),
    (
        "loop_demo.ezy",
        [],
        ["Loop!", "count is 1", "count is 5", "Done counting."],
    ),
    (
        "function_demo.ezy",
        [],
        ["Hi Sam, great to see you!", "Double of 21 is 42",
         "A 3 by 4 room has area 12"],
    ),
    (
        "guessing_game.ezy",
        [str(n) for n in range(1, 11)],   # one of 1..10 must be the secret
        ["I'm thinking of a number", "Correct!", "Thanks for playing!"],
    ),
    (
        "calculator.ezy",
        ["6", "+", "7"],
        ["Simple calculator!", "6 + 7 = 13"],
    ),
]


def main():
    random.seed(1)   # make the guessing game deterministic for testing
    passed = 0
    failed = 0

    for filename, inputs, expected in CASES:
        try:
            output = run_program(filename, inputs)
        except (EzyError, AssertionError, Exception) as e:  # noqa: BLE001
            msg = e.friendly() if isinstance(e, EzyError) else str(e)
            print(f"FAIL  {filename}\n      crashed: {msg}")
            failed += 1
            continue

        missing = [s for s in expected if s not in output]
        if missing:
            print(f"FAIL  {filename}")
            for s in missing:
                print(f"      expected to find: {s!r}")
            print("      --- actual output ---")
            for line in output.splitlines():
                print(f"      {line}")
            failed += 1
        else:
            print(f"PASS  {filename}")
            passed += 1

    print(f"\n{passed} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
