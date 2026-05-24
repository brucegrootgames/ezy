# Ezy 

**Ezy** is a tiny programming language for absolute beginners. It reads like
plain English — no curly braces, no semicolons, no `main()`, and no imports
just to print something. A whole program can be a single line:

```
say "Hello!"
```

When something goes wrong, Ezy explains it in friendly language and suggests how
to fix it, instead of showing a scary error.

---

## Install & run

You only need **Python 3.8+**. There is nothing to install.

```bash
# Run a program file
python ezy.py examples/hello.ezy

# Start the interactive playground (REPL) — just type code and press Enter
python ezy.py
```

> On Windows, if `python` opens the Microsoft Store, use the launcher instead:
> `py ezy.py examples/hello.ezy`

### Run all the examples and check they work

```bash
python run_tests.py
```

---

## How it works (the three stages)

Ezy is a classic interpreter built in three clear stages. Each is its own file:

1. **`lexer.py` — the Lexer.** Turns your source text into a list of *tokens*
   (little labelled words like `say`, `"Hello"`, `+`). It also figures out the
   indentation and emits INDENT/DEDENT markers so blocks work, being forgiving
   about tabs vs spaces.
2. **`parser.py` — the Parser.** Turns the flat token list into an *Abstract
   Syntax Tree* (AST) — a nested structure that captures what each line means.
   It also handles math precedence so `2 + 3 * 4` is `14`, not `20`.
3. **`interpreter.py` — the Interpreter.** Walks the AST and actually runs it:
   storing variables, printing, looping, calling functions. All the friendly
   type-checking lives here.

`ezy.py` glues them together and prints errors nicely. `errors.py` defines the
friendly `EzyError`. `ast_nodes.py` defines the tree node types.

```
source text → [lexer] → tokens → [parser] → AST → [interpreter] → output
```

---

## Syntax cheat-sheet

### Printing and input
```
say "Hello!"
say "The answer is " + text of 42

ask name "What is your name? "
say "Hi " + name
```
`ask` always stores the answer as **text**. Use `number of name` to turn it
into a number.

### Variables
```
let score be 10
change score to score + 5
```
`let X be …` creates or updates a variable. `change X to …` reads the same but
is meant for updating one you already have.

### Values and math
```
let n be 7              # a number (7 or 3.5)
let word be "hi"        # text, in double quotes
let won be yes          # a boolean: yes or no

let total be (2 + 3) * 4    # + - * /  and  ( ) for grouping
```
`+` adds two numbers **or** joins two pieces of text. Mixing a number and text
is a friendly error — convert first with `text of`.

### Converting and measuring
```
text of 42          # → "42"
number of "3.5"     # → 3.5
length of "hello"   # → 5
```

### Comparing (in words)
```
a is b                a is not b
a is bigger than b    a is smaller than b
a is at least b       a is at most b
```
(`is greater than` / `is less than` work too.) Combine with `and`, `or`, `not`.

### Choices
```
if score is bigger than 5
    say "You win!"
otherwise if score is 5
    say "So close!"
otherwise
    say "Try again"
```

### Loops
```
repeat 3 times
    say "Loop!"

let count be 1
repeat while count is at most 5
    say count
    change count to count + 1
```

### Functions
```
make greet with person
    say "Hi " + person

greet with "Sam"          # call it (the word 'with' is optional: greet "Sam")

make double with n
    give back n * 2       # functions can give a value back

let result be double with 21
say text of result        # → 42
```

### Random numbers
```
let dice be random with 1, 6
```

### Comments
```
# Anything after a # is ignored.
say "hi"   # you can also put one at the end of a line
```

---

## Examples

The `examples/` folder has five ready-to-run programs:

| File | What it shows |
|------|---------------|
| `hello.ezy` | Printing and asking for input |
| `loop_demo.ezy` | `repeat N times` and `repeat while` |
| `function_demo.ezy` | Defining and calling functions, `give back` |
| `guessing_game.ezy` | A real little game: loops, conditions, randomness |
| `calculator.ezy` | Reading input, converting to numbers, branching |

Try one:
```bash
python ezy.py examples/guessing_game.ezy
```

---

## A taste of the friendly errors

```
say "Score: " + score
```
```
Oops! Something went wrong on line 1.
  You tried to add text and a number together with '+', and Ezy isn't sure
  what you meant.
  Hint: To stick text and a number together, turn the number into text first,
  e.g.  "Score: " + text of score
```

That's Ezy. Have fun! 

---

## License

[MIT](LICENSE) — free to use, modify, and share.
