E-Lang (English Language Programming)
====================================

E-Lang is an experimental programming language whose syntax is based on controlled natural English.
Code is written as readable sentences like:

```text
let counter be 1
while counter is less than 10 do
  say "Counter is " plus counter
  add 1 to counter
end
```

The goal is to make programming approachable for beginners and non-technical people by:

- Using **subject–verb–object** sentence patterns.
- Avoiding most symbolic syntax such as `{}`, `()`, `==`, `;`.
- Favoring **plain English keywords** and phrases.
- Producing **plain-English error messages**.

This repository contains:

- The **language specification** in `docs/elang-grammar.md`.
- A **reference interpreter** written in Python in the `elang/` package.
- **Example programs** in `examples/elang/`.
- **Tests** in `tests/`.

Quick concept examples
----------------------

- Variables:

  ```text
  let x be 5
  set name to "Alice"
  ```

- Conditions:

  ```text
  if x is greater than 3 then
    say "x is big"
  otherwise
    say "x is small"
  end
  ```

- Loops:

  ```text
  repeat 5 times
    say "Hello"
  end
  ```

- Functions:

  ```text
  define a function called greet that takes name and does
    say "Hello " plus name
  end

  call greet with "Charlie"
  ```

Project layout
--------------

- `elang/`: Python interpreter for E-Lang (lexer, parser, AST, runtime).
- `docs/elang-grammar.md`: Grammar and language reference.
- `examples/elang/`: Sample E-Lang programs (Hello World, FizzBuzz, calculator, list sorter).
- `tests/`: Unit tests for the interpreter and language features.

Requirements
------------

- Python 3.10+ (no external runtime dependencies).

After the interpreter is implemented you will be able to run a program with:

```bash
python -m elang path/to/program.elang
```

Status
------

This is a work in progress. The first version focuses on:

- Variables, conditionals, loops, functions, lists.
- Basic arithmetic and boolean logic.
- Simple text output.
- Clear, natural-language error messages.

