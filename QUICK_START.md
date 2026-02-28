# Quick Start

## Prerequisites
- Python 3.10+ available as `python3`
- `pip` up to date

## Install (editable)
```bash
cd /path/to/this/repo/E-Lang
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## Run the sample GUI calculator
```bash
python3 -m elang /path/to/this/repo/E-Lang/examples/elang/gui_calculator.elang
```
This opens the “E-Lang Calculator” window. Enter `x` and `y`, click `=`, and see results for addition, subtraction, multiplication, and division.

## Run your own program
```bash
python3 -m elang /absolute/path/to/your_program.elang
```

## Alternative entry point
```bash
python3 /path/to/this/repo/E-Lang/run.py /path/to/this/repo/E-Lang/examples/elang/gui_calculator.elang
```

## Project map
- Interpreter code: `/path/to/this/repo/E-Lang/elang/`
- Grammar reference: `/path/to/this/repo/E-Lang/docs/elang-grammar.md`
- Examples: `/path/to/this/repo/E-Lang/examples/elang/`
- Tests: `/path/to/this/repo/E-Lang/tests/`

## Notes
- Blank lines inside blocks (`if/otherwise`, `while`, `repeat`, `when`, function bodies) are accepted by the parser.
- Error messages are natural-language; if parsing fails, check the reported line and column.
