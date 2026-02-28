from __future__ import annotations

from elang.interpreter import run_source


def eval_and_get_env(source: str):
    env, output = run_source(source)
    return env, output.strip().splitlines()


def test_hello_world_output():
    source = 'say "Hello World"\n'
    _, lines = eval_and_get_env(source)
    assert lines == ["Hello World"]


def test_variables_and_math():
    source = """
    let x be 5
    add 3 to x
    multiply x by 2
    say x
    """
    _, lines = eval_and_get_env(source)
    # ((5 + 3) * 2) = 16
    assert lines[-1] == "16"


def test_if_else():
    source = """
    let x be 5
    if x is greater than 3 then
      say "big"
    otherwise
      say "small"
    end
    """
    _, lines = eval_and_get_env(source)
    assert "big" in lines


def test_functions_and_return():
    source = """
    define a function called square that takes x and does
      return x times x
    end

    say call square with 4
    """
    _, lines = eval_and_get_env(source)
    assert lines[-1] == "16"


def test_lists_and_length():
    source = """
    create a list called numbers containing 1, 2, 3
    set count to length of numbers
    say count
    """
    _, lines = eval_and_get_env(source)
    assert lines[-1] == "3"

