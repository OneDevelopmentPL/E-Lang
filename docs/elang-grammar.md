# E-Lang Grammar and Language Reference

This document defines the **controlled English** used by E-Lang.
It is intentionally small and precise so that programs are readable
as plain English while still being easy to parse.

E-Lang files use the extension `.elang`.

Comments
--------

- A comment starts with `note:` and continues to the end of the line.

  ```text
  note: this is a comment
  let x be 5  note: inline comment is also allowed
  ```

Lexical rules
-------------

- **Identifiers**: sequences of letters, digits, and underscores, starting with a letter.
  Examples: `x`, `counter`, `total_amount`.
- **Keywords**: reserved words and phrases such as `let`, `if`, `while`, `define a function called`.
  Keywords are **case-insensitive** (`If`, `IF`, and `if` are treated the same).
- **Numbers**: decimal integers, e.g. `0`, `42`, `12345`.
- **Strings**: double-quoted text, possibly containing spaces, e.g. `"Hello world"`.
- **Booleans**: the literals `true` and `false` (case-insensitive).
- **Whitespace**: spaces and tabs are used to separate words and are otherwise ignored.
- **Newlines**: end statements; block statements (`if`, `while`, `repeat`, `define a function`)
  span multiple lines and are terminated with `end`.

Program structure
-----------------

An E-Lang program is a sequence of **statements**:

```ebnf
program        ::= { statement NEWLINE } EOF
```

Statements
----------

### Variable declarations and assignments

```ebnf
statement      ::= let_stmt
                 | set_stmt
                 | if_stmt
                 | while_stmt
                 | repeat_stmt
                 | func_def
                 | say_stmt
                 | display_stmt
                 | list_create_stmt
                 | math_update_stmt
                 | return_stmt
                 | expr_stmt

let_stmt       ::= "let" IDENT "be" expression
set_stmt       ::= "set" IDENT "to" expression
```

Examples:

```text
let x be 5
set name to "Alice"
```

### Conditionals

```ebnf
if_stmt        ::= "if" expression "then" NEWLINE
                   { statement NEWLINE }
                   [ "otherwise" NEWLINE
                     { statement NEWLINE } ]
                   "end"
```

Example:

```text
if x is greater than 3 then
  say "x is big"
otherwise
  say "x is small"
end
```

### Loops

```ebnf
repeat_stmt    ::= "repeat" expression "times" NEWLINE
                   { statement NEWLINE }
                   "end"

while_stmt     ::= "while" expression "do" NEWLINE
                   { statement NEWLINE }
                   "end"
```

Examples:

```text
repeat 5 times
  say "Hello"
end

while counter is less than 10 do
  say counter
  add 1 to counter
end
```

### Functions

```ebnf
func_def       ::= "define" "a" "function" "called" IDENT
                   [ "that" "takes" param_list ] "and" "does" NEWLINE
                   { statement NEWLINE }
                   "end"

param_list     ::= IDENT { ("," | "and") IDENT }
```

Examples:

```text
define a function called greet that takes name and does
  say "Hello " plus name
end
```

### Function calls

Function calls can be used either as **expressions** or as standalone statements.

```ebnf
call_expr      ::= "call" IDENT [ "with" arg_list ]
arg_list       ::= expression { ("," | "and") expression }
expr_stmt      ::= call_expr
```

Examples:

```text
call greet with "Alice"
set result to call add_numbers with 2 and 3
```

### Output

```ebnf
say_stmt       ::= "say" expression
display_stmt   ::= "display" "the" "value" "of" expression
```

Examples:

```text
say "Hello world"
display the value of total
```

### Lists

```ebnf
list_create_stmt ::= "create" "a" "list" "called" IDENT
                     "containing" expression { ("," | "and") expression }
```

Example:

```text
create a list called fruits containing "apple", "banana", "cherry"
```

List expressions:

```ebnf
list_access   ::= "get" "the" ("first" | "last") "item" "from" expression
                 | "get" "the" "item" "at" "position" expression "from" expression

length_expr   ::= "length" "of" expression
```

Examples:

```text
set first_fruit to get the first item from fruits
set count to length of fruits
```

### Math update statements

```ebnf
math_update_stmt ::= "add" expression "to" IDENT
                   | "subtract" expression "from" IDENT
                   | "multiply" IDENT "by" expression
                   | "divide" IDENT "by" expression
```

Examples:

```text
add 1 to counter
subtract 3 from x
multiply total by 2
divide y by 2
```

### Return

```ebnf
return_stmt   ::= "return" expression
```

Used inside functions to give back a value:

```text
define a function called square that takes x and does
  return x times x
end
```

Expressions
-----------

E-Lang expressions use English keywords instead of symbols.

```ebnf
expression    ::= or_expr
or_expr       ::= and_expr { "or" and_expr }
and_expr      ::= not_expr { "and" not_expr }
not_expr      ::= [ "not" ] comparison
comparison    ::= sum_expr [ comp_op sum_expr ]

comp_op       ::= "is" ["not"] "equal" "to"
                 | "is" "equal" "to"
                 | "equals"
                 | "is" ["not"] "greater" "than"
                 | "is" ["not"] "less" "than"
                 | "is"

sum_expr      ::= product_expr { ("plus" | "minus") product_expr }
product_expr  ::= unary_expr { ("times"
                               | "multiplied" "by"
                               | "divided" "by"
                               | "over"
                               | "modulo") unary_expr }

unary_expr    ::= primary

primary       ::= NUMBER
                 | STRING
                 | "true"
                 | "false"
                 | "nothing"
                 | IDENT
                 | list_access
                 | length_expr
                 | call_expr
```

Operator precedence (from highest to lowest):

1. Multiplication / division / modulo (`times`, `divided by`, `modulo`)
2. Addition / subtraction (`plus`, `minus`)
3. Comparisons (`is greater than`, `is less than`, `is equal to`, `equals`, `is`)
4. Logical NOT (`not`)
5. Logical AND (`and`)
6. Logical OR (`or`)

Ambiguities and restrictions
----------------------------

Natural English can be ambiguous. E-Lang resolves this by **forbidding** or
constraining some patterns:

- **Negated comparisons**

  - Allowed: `x is not equal to 5`, `x is not greater than 10`.
  - Disallowed: `x is not 5` (ambiguous). Prefer `x is not equal to 5`.

- **Chained comparisons**

  - Disallowed: `1 is less than x is less than 10`.
  - Instead, write: `1 is less than x and x is less than 10`.

- **Implicit precedence confusion**

  - `a plus b times c` is parsed as `a plus (b times c)` (normal math rules).
  - When in doubt, split into temporary variables:

    ```text
    set partial to b times c
    set result to a plus partial
    ```

- **Loose ‘is’**

  - `x is y` is allowed and means equality.
  - `x is greater than y` and `x is less than y` have their usual meanings.
  - Avoid vague phrases like `x is big`; prefer explicit comparisons
    (e.g., `x is greater than 10`), or use them only in `say` strings.

Error messages
--------------

The interpreter reports errors in plain English, for example:

- `Something went wrong: I could not find a variable called "count" on line 3.`
- `Something went wrong: I did not understand this sentence near "if x is then". I expected a comparison after "is".`

See the implementation in the `elang` package for the exact wording.

