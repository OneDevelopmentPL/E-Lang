from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from . import ast
from .errors import ELangError, ELangNameError, ELangRuntimeError, ELangTypeError
from .parser import Parser


@dataclass
class FunctionValue:
    name: str
    params: List[str]
    body: List[ast.Stmt]
    closure: "Environment"


class Environment:
    def __init__(self, parent: Optional["Environment"] = None) -> None:
        self.values: Dict[str, Any] = {}
        self.parent = parent

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def assign(self, name: str, value: Any) -> None:
        if name in self.values:
            self.values[name] = value
        elif self.parent is not None:
            self.parent.assign(name, value)
        else:
            # If the name does not exist yet, create it in the current scope.
            self.values[name] = value

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise ELangNameError(f"I could not find a variable or function called \"{name}\"")


class ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class Interpreter:
    def __init__(self) -> None:
        self.global_env = Environment()
        self._install_builtins(self.global_env)
        self.output: List[str] = []
        self._gui: Optional["GuiManager"] = None

    # Public API ----------------------------------------------------------

    def run(self, source: str) -> Tuple[Environment, str]:
        parser = Parser.from_source(source)
        program = parser.parse()
        self._execute_block(program.statements, self.global_env)
        return self.global_env, "".join(self.output)

    # Built-ins -----------------------------------------------------------

    def _install_builtins(self, env: Environment) -> None:
        # Simple built-in functions to make the language feel richer.
        env.define(
            "join_with",
            lambda lst, sep: sep.join(str(x) for x in lst),
        )
        env.define(
            "sort_ascending",
            lambda lst: sorted(lst),
        )
        env.define(
            "sort_descending",
            lambda lst: sorted(lst, reverse=True),
        )

        def to_number(value: Any) -> Any:
            if isinstance(value, (int, float)):
                return value
            try:
                return int(str(value))
            except Exception as exc:  # noqa: BLE001
                raise ELangTypeError(
                    "I could not turn this into a whole number"
                ) from exc

        env.define("to_number", to_number)

    # Statement execution -------------------------------------------------

    def _execute_block(self, statements: List[ast.Stmt], env: Environment) -> None:
        for stmt in statements:
            self._execute(stmt, env)

    def _execute(self, stmt: ast.Stmt, env: Environment) -> None:
        if isinstance(stmt, ast.Let):
            value = self._eval(stmt.expr, env)
            env.define(stmt.name, value)
        elif isinstance(stmt, ast.Set):
            value = self._eval(stmt.expr, env)
            env.assign(stmt.name, value)
        elif isinstance(stmt, ast.Say):
            value = self._eval(stmt.expr, env)
            self.output.append(str(value) + "\n")
        elif isinstance(stmt, ast.DisplayValue):
            value = self._eval(stmt.expr, env)
            self.output.append(str(value) + "\n")
        elif isinstance(stmt, ast.If):
            if self._truthy(self._eval(stmt.condition, env)):
                self._execute_block(stmt.then_branch, Environment(env))
            elif stmt.else_branch is not None:
                self._execute_block(stmt.else_branch, Environment(env))
        elif isinstance(stmt, ast.While):
            while self._truthy(self._eval(stmt.condition, env)):
                self._execute_block(stmt.body, Environment(env))
        elif isinstance(stmt, ast.RepeatTimes):
            count_val = self._eval(stmt.count_expr, env)
            if not isinstance(count_val, int):
                raise ELangTypeError("I expected a whole number for the repeat count")
            for _ in range(count_val):
                self._execute_block(stmt.body, Environment(env))
        elif isinstance(stmt, ast.FunctionDef):
            func_value = FunctionValue(stmt.name, stmt.params, stmt.body, env)
            env.define(stmt.name, func_value)
        elif isinstance(stmt, ast.Return):
            value = self._eval(stmt.expr, env)
            raise ReturnSignal(value)
        elif isinstance(stmt, ast.CreateList):
            items = [self._eval(e, env) for e in stmt.items]
            env.define(stmt.name, list(items))
        elif isinstance(stmt, ast.MathUpdate):
            self._execute_math_update(stmt, env)
        elif isinstance(stmt, ast.ExprStmt):
            # Evaluate for side effects (e.g., calling a function).
            self._eval(stmt.expr, env)
        elif isinstance(stmt, ast.CreateWindow):
            self._ensure_gui().create_window(stmt.name)
        elif isinstance(stmt, ast.AddButton):
            self._ensure_gui().add_button(stmt.window_name, stmt.button_name)
        elif isinstance(stmt, ast.AddLabel):
            self._ensure_gui().add_label(stmt.window_name, stmt.label_name)
        elif isinstance(stmt, ast.AddEntry):
            self._ensure_gui().add_entry(stmt.window_name, stmt.entry_name)
        elif isinstance(stmt, ast.SetGuiProperty):
            self._ensure_gui().set_property(
                stmt.target_name, stmt.property_name, self._eval(stmt.expr, env)
            )
        elif isinstance(stmt, ast.SetGuiSize):
            self._ensure_gui().set_size(stmt.window_name, stmt.width, stmt.height)
        elif isinstance(stmt, ast.ShowWidget):
            x_val = self._eval(stmt.x, env) if stmt.x is not None else None
            y_val = self._eval(stmt.y, env) if stmt.y is not None else None
            self._ensure_gui().show(stmt.name, x_val, y_val)
        elif isinstance(stmt, ast.OnClick):
            self._ensure_gui().register_on_click(stmt.widget_name, stmt.body)
        else:
            raise ELangRuntimeError(f"I do not know how to execute statement type {type(stmt)!r}")

    def _execute_math_update(self, stmt: ast.MathUpdate, env: Environment) -> None:
        current = env.get(stmt.target)
        value = self._eval(stmt.expr, env)
        if not isinstance(current, (int, float)) or not isinstance(value, (int, float)):
            raise ELangTypeError("I expected numbers for this math operation")

        if stmt.kind == "ADD":
            result = current + value
        elif stmt.kind == "SUBTRACT":
            result = current - value
        elif stmt.kind == "MULTIPLY":
            result = current * value
        elif stmt.kind == "DIVIDE":
            if value == 0:
                raise ELangRuntimeError("I cannot divide by zero")
            result = current / value
        else:
            raise ELangRuntimeError(f"I do not recognise this math operation: {stmt.kind}")

        env.assign(stmt.target, result)

    # Expression evaluation -----------------------------------------------

    def _eval(self, expr: ast.Expr, env: Environment) -> Any:
        if isinstance(expr, ast.Literal):
            return expr.value
        if isinstance(expr, ast.Variable):
            return env.get(expr.name)
        if isinstance(expr, ast.Unary):
            right = self._eval(expr.right, env)
            if expr.op == "NOT":
                return not self._truthy(right)
            raise ELangRuntimeError(f"I do not recognise this unary operator: {expr.op}")
        if isinstance(expr, ast.Binary):
            return self._eval_binary(expr, env)
        if isinstance(expr, ast.Call):
            return self._eval_call(expr, env)
        if isinstance(expr, ast.ListAccess):
            return self._eval_list_access(expr, env)
        if isinstance(expr, ast.LengthOf):
            value = self._eval(expr.list_expr, env)
            if not isinstance(value, (list, str)):
                raise ELangTypeError("I can only take the length of a list or text")
            return len(value)
        if isinstance(expr, ast.TextOf):
            return self._ensure_gui().get_text(expr.name)
        raise ELangRuntimeError(f"I do not know how to evaluate expression type {type(expr)!r}")

    def _eval_binary(self, expr: ast.Binary, env: Environment) -> Any:
        left = self._eval(expr.left, env)
        right = self._eval(expr.right, env)
        op = expr.op

        if op == "PLUS":
            # Support concatenating strings and numbers conveniently.
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            self._ensure_numbers(left, right, "add")
            return left + right
        if op == "MINUS":
            self._ensure_numbers(left, right, "subtract")
            return left - right
        if op == "TIMES":
            self._ensure_numbers(left, right, "multiply")
            return left * right
        if op == "DIVIDED":
            self._ensure_numbers(left, right, "divide")
            if right == 0:
                raise ELangRuntimeError("I cannot divide by zero")
            return left / right
        if op == "MODULO":
            self._ensure_numbers(left, right, "take the remainder of")
            if right == 0:
                raise ELangRuntimeError("I cannot take the remainder with zero")
            return left % right

        # Logical operators
        if op == "AND":
            return self._truthy(left) and self._truthy(right)
        if op == "OR":
            return self._truthy(left) or self._truthy(right)

        # Comparisons
        if op == "IS_EQUAL":
            return left == right
        if op == "IS_NOT_EQUAL":
            return left != right
        if op == "IS_GREATER":
            self._ensure_numbers(left, right, "compare with 'is greater than'")
            return left > right
        if op == "IS_NOT_GREATER":
            self._ensure_numbers(left, right, "compare with 'is not greater than'")
            return not (left > right)
        if op == "IS_LESS":
            self._ensure_numbers(left, right, "compare with 'is less than'")
            return left < right
        if op == "IS_NOT_LESS":
            self._ensure_numbers(left, right, "compare with 'is not less than'")
            return not (left < right)

        raise ELangRuntimeError(f"I do not recognise this operator: {op}")

    def _eval_call(self, expr: ast.Call, env: Environment) -> Any:
        callee_value = env.get(expr.callee)
        args = [self._eval(a, env) for a in expr.args]

        # Built-in Python-callable
        if callable(callee_value) and not isinstance(callee_value, FunctionValue):
            try:
                return callee_value(*args)
            except TypeError as exc:
                raise ELangRuntimeError(
                    f"I could not call the built-in '{expr.callee}' with these arguments"
                ) from exc

        if not isinstance(callee_value, FunctionValue):
            raise ELangTypeError(f"'{expr.callee}' is not a function I can call")

        func = callee_value
        if len(args) != len(func.params):
            raise ELangRuntimeError(
                f"The function '{func.name}' expected {len(func.params)} value(s) but got {len(args)}"
            )

        local_env = Environment(func.closure)
        for name, value in zip(func.params, args):
            local_env.define(name, value)

        try:
            self._execute_block(func.body, local_env)
        except ReturnSignal as signal:
            return signal.value
        return None

    def _eval_list_access(self, expr: ast.ListAccess, env: Environment) -> Any:
        list_val = self._eval(expr.list_expr, env)
        if not isinstance(list_val, list):
            raise ELangTypeError("I can only get items from a list")
        index_val = self._eval(expr.index_expr, env)
        if not isinstance(index_val, int):
            raise ELangTypeError("I expected a whole number for the list position")

        if index_val == -1:
            # 'last item'
            if not list_val:
                raise ELangRuntimeError("I cannot get the last item of an empty list")
            return list_val[-1]

        # User positions are 1-based; convert to 0-based.
        if index_val <= 0 or index_val > len(list_val):
            raise ELangRuntimeError(
                f"There is no item at position {index_val}; valid positions are from 1 to {len(list_val)}"
            )
        return list_val[index_val - 1]

    # Helpers -------------------------------------------------------------

    @staticmethod
    def _truthy(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def _ensure_numbers(left: Any, right: Any, context: str) -> None:
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise ELangTypeError(f"I expected numbers to {context}")

    # GUI support ----------------------------------------------------------

    def _ensure_gui(self) -> "GuiManager":
        if self._gui is None:
            self._gui = GuiManager(self)
        return self._gui


class GuiManager:
    """
    Very small wrapper around Tkinter so E-Lang programs can create
    simple windows, buttons, labels, and text inputs.
    """

    def __init__(self, owner: Interpreter) -> None:
        try:
            import tkinter as tk
            from tkinter import messagebox
        except Exception as exc:  # noqa: BLE001
            raise ELangRuntimeError(
                "I tried to create a graphical window, but Tkinter is not available."
            ) from exc

        self._owner = owner
        self._tk = tk
        self._messagebox = messagebox
        self._root: Optional[tk.Tk] = None
        self._widgets: Dict[str, Any] = {}
        self._handlers: Dict[str, List[ast.Stmt]] = {}

    def _get_root(self) -> "tk.Tk":  # type: ignore[name-defined]
        if self._root is None:
            self._root = self._tk.Tk()
        return self._root

    def create_window(self, name: str) -> None:
        root = self._get_root()
        self._widgets[name] = root

    def _get_widget(self, name: str) -> Any:
        if name not in self._widgets:
            raise ELangRuntimeError(f"I could not find a window or widget called \"{name}\"")
        return self._widgets[name]

    def add_button(self, window_name: str, button_name: str) -> None:
        parent = self._get_widget(window_name)
        button = self._tk.Button(parent)
        self._widgets[button_name] = button
        self._maybe_bind_click(button_name, button)

    def add_label(self, window_name: str, label_name: str) -> None:
        parent = self._get_widget(window_name)
        label = self._tk.Label(parent)
        self._widgets[label_name] = label

    def add_entry(self, window_name: str, entry_name: str) -> None:
        parent = self._get_widget(window_name)
        entry = self._tk.Entry(parent)
        self._widgets[entry_name] = entry

    def set_property(self, target_name: str, property_name: str, value: Any) -> None:
        widget = self._get_widget(target_name)
        prop = property_name.lower()
        if prop == "title":
            # Only meaningful on the main window.
            if hasattr(widget, "title"):
                widget.title(str(value))
            else:
                raise ELangRuntimeError(
                    f"I can only set the title of a window, not of '{target_name}'"
                )
        elif prop == "text":
            if isinstance(widget, self._tk.Entry):
                widget.delete(0, self._tk.END)
                widget.insert(0, str(value))
            elif hasattr(widget, "config"):
                widget.config(text=str(value))
            else:
                raise ELangRuntimeError(
                    f"I can only set the text of things like buttons, labels, and inputs, not of '{target_name}'"
                )
        else:
            raise ELangRuntimeError(
                f"I do not know how to change the property '{property_name}' on '{target_name}'"
            )

    def set_size(self, window_name: str, width: int, height: int) -> None:
        widget = self._get_widget(window_name)
        if hasattr(widget, "geometry"):
            widget.geometry(f"{width}x{height}")
        else:
            raise ELangRuntimeError(
                f"I can only change the size of a window, not of '{window_name}'"
            )

    def show(self, name: str, x: Optional[Any], y: Optional[Any]) -> None:
        widget = self._get_widget(name)
        tk = self._tk

        if isinstance(widget, tk.Tk):
            # Showing the window starts the event loop. It should normally
            # be the last action in the program.
            widget.mainloop()
            return

        # Child widgets: place at coordinates or pack by default.
        if x is not None and y is not None:
            try:
                x_int = int(x)
                y_int = int(y)
            except (TypeError, ValueError) as exc:
                raise ELangTypeError(
                    "I expected whole numbers for the x and y positions"
                ) from exc
            widget.place(x=x_int, y=y_int)
        else:
            widget.pack()

    def register_on_click(self, widget_name: str, body: List[ast.Stmt]) -> None:
        self._handlers[widget_name] = body
        widget = self._widgets.get(widget_name)
        if widget is not None:
            self._maybe_bind_click(widget_name, widget)

    def _maybe_bind_click(self, widget_name: str, widget: Any) -> None:
        tk = self._tk
        if isinstance(widget, tk.Button):
            widget.config(command=lambda n=widget_name: self._handle_click(n))

    def _handle_click(self, widget_name: str) -> None:
        body = self._handlers.get(widget_name)
        if not body:
            return
        try:
            self._owner._execute_block(body, self._owner.global_env)
        except ELangError as exc:
            self._messagebox.showerror("E-Lang error", f"Something went wrong: {exc}")

    def get_text(self, widget_name: str) -> str:
        widget = self._get_widget(widget_name)
        tk = self._tk
        if isinstance(widget, tk.Entry):
            return widget.get()
        if hasattr(widget, "cget"):
            try:
                return str(widget.cget("text"))
            except Exception:  # noqa: BLE001
                pass
        raise ELangRuntimeError(
            "I can only read the text of input fields, buttons, and labels"
        )


def run_source(source: str) -> Tuple[Environment, str]:
    """
    Convenience function for running a snippet of E-Lang code.

    Returns the final environment and all printed output as a single string.
    """
    interpreter = Interpreter()
    return interpreter.run(source)


def run_file(path: str) -> str:
    """
    Run an E-Lang file from disk and return the captured output string.
    """
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    _, output = run_source(source)
    # Also echo to stdout so CLI usage is straightforward.
    print(output, end="")
    return output

