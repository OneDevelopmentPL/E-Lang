from __future__ import annotations

from typing import List, Optional

from . import ast
from .errors import ELangSyntaxError
from .lexer import Lexer, Token


class Parser:
    """Recursive-descent parser for E-Lang."""

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.current = 0

    @classmethod
    def from_source(cls, source: str) -> "Parser":
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        return cls(tokens)

    # Entry point ---------------------------------------------------------

    def parse(self) -> ast.Program:
        statements: List[ast.Stmt] = []
        while not self._is_at_end():
            self._skip_newlines()
            if self._is_at_end():
                break
            statements.append(self._statement())
            # Optional newline after each statement.
            self._match("NEWLINE")
        return ast.Program(statements)

    # Statements ----------------------------------------------------------

    def _statement(self) -> ast.Stmt:
        if self._match("LET"):
            return self._let_stmt()
        if self._match("SET"):
            return self._set_stmt()
        if self._match("IF"):
            return self._if_stmt()
        if self._match("WHILE"):
            return self._while_stmt()
        if self._match("REPEAT"):
            return self._repeat_stmt()
        if self._check("DEFINE"):
            return self._func_def()
        if self._match("WHEN"):
            return self._when_stmt()
        if self._match("SAY"):
            expr = self._expression()
            return ast.Say(expr)
        if self._match("DISPLAY"):
            self._consume("THE", "I expected 'the' after 'display'")
            self._consume("VALUE", "I expected 'value' after 'display the'")
            self._consume("OF", "I expected 'of' after 'display the value'")
            expr = self._expression()
            return ast.DisplayValue(expr)
        if self._match("CREATE"):
            # Either "create window ..." or "create a list ..."
            if self._check("WINDOW"):
                return self._create_window_stmt()
            return self._create_list_stmt()
        if self._match("SHOW"):
            return self._show_widget_stmt()
        if self._match("ADD"):
            # Either math update ("add 1 to x") or GUI add
            if self._check("BUTTON") or self._check("LABEL") or self._check("ENTRY"):
                return self._add_gui_stmt()
            return self._math_update_stmt(previous_kind="ADD")
        if self._match("SUBTRACT", "MULTIPLY", "DIVIDE"):
            return self._math_update_stmt(previous_kind=self._previous().type)
        if self._match("RETURN"):
            expr = self._expression()
            return ast.Return(expr)
        # Expression statement (typically a call).
        expr = self._expression()
        return ast.ExprStmt(expr)

    def _let_stmt(self) -> ast.Let:
        name = self._consume("IDENT", "I expected a name after 'let'").lexeme
        self._consume("BE", "I expected 'be' after the name")
        expr = self._expression()
        return ast.Let(name, expr)

    def _set_stmt(self) -> ast.Stmt:
        name = self._consume("IDENT", "I expected a name after 'set'").lexeme

        # GUI property forms:
        # - set mygui title to "Title"
        # - set testbutton text to "text"
        # - set mygui size to x equals 300, y equals 300
        if self._check("TITLE") or self._check("TEXT") or self._check("SIZE"):
            prop_token = self._advance()
            prop = prop_token.lexeme.lower()

            if prop == "size":
                return self._set_size_stmt(window_name=name)

            self._consume("TO", "I expected 'to' after the property name")
            expr = self._expression()
            return ast.SetGuiProperty(name, prop, expr)

        # Fallback: standard variable assignment.
        self._consume("TO", "I expected 'to' after the name")
        expr = self._expression()
        return ast.Set(name, expr)

    def _if_stmt(self) -> ast.If:
        condition = self._expression()
        self._consume("THEN", "I expected 'then' after the condition in an if sentence")
        self._consume("NEWLINE", "I expected a new line after 'then'")
        then_branch: List[ast.Stmt] = []
        else_branch: Optional[List[ast.Stmt]] = None

        while True:
            self._skip_newlines()
            if self._check("END") or self._check("OTHERWISE") or self._is_at_end():
                break
            then_branch.append(self._statement())
            self._match("NEWLINE")

        if self._match("OTHERWISE"):
            self._consume("NEWLINE", "I expected a new line after 'otherwise'")
            else_branch = []
            while True:
                self._skip_newlines()
                if self._check("END") or self._is_at_end():
                    break
                else_branch.append(self._statement())
                self._match("NEWLINE")

        self._consume("END", "I expected 'end' to finish the if sentence")
        return ast.If(condition, then_branch, else_branch)

    def _while_stmt(self) -> ast.While:
        condition = self._expression()
        self._consume("DO", "I expected 'do' after the while condition")
        self._consume("NEWLINE", "I expected a new line after 'do'")
        body: List[ast.Stmt] = []
        while True:
            self._skip_newlines()
            if self._check("END") or self._is_at_end():
                break
            body.append(self._statement())
            self._match("NEWLINE")
        self._consume("END", "I expected 'end' to finish the while loop")
        return ast.While(condition, body)

    def _repeat_stmt(self) -> ast.RepeatTimes:
        count_expr = self._expression()
        self._consume("TIMES", "I expected 'times' after the repeat count")
        self._consume("NEWLINE", "I expected a new line after 'times'")
        body: List[ast.Stmt] = []
        while True:
            self._skip_newlines()
            if self._check("END") or self._is_at_end():
                break
            body.append(self._statement())
            self._match("NEWLINE")
        self._consume("END", "I expected 'end' to finish the repeat loop")
        return ast.RepeatTimes(count_expr, body)

    def _func_def(self) -> ast.FunctionDef:
        self._consume("DEFINE", "I expected 'define' at the start of a function definition")
        self._consume("A", "I expected 'a' after 'define'")
        self._consume("FUNCTION", "I expected 'function' after 'define a'")
        self._consume("CALLED", "I expected 'called' after 'define a function'")
        name = self._consume("IDENT", "I expected the function name after 'called'").lexeme

        params: List[str] = []
        if self._match("THAT"):
            self._consume("TAKES", "I expected 'takes' after 'that'")
            params.append(self._consume("IDENT", "I expected a parameter name").lexeme)
            while True:
                if self._match("COMMA"):
                    params.append(self._consume("IDENT", "I expected a parameter name").lexeme)
                    continue
                # Handle 'and' carefully so we do not consume the 'and' in 'and does'.
                if self._check("AND"):
                    next_token = self._peek_next()
                    if next_token.type == "IDENT":
                        self._advance()  # consume AND
                        params.append(
                            self._consume("IDENT", "I expected a parameter name").lexeme
                        )
                        continue
                break

        self._consume("AND", "I expected 'and' before 'does'")
        self._consume("DOES", "I expected 'does' after 'and'")
        self._consume("NEWLINE", "I expected a new line after the function header")

        body: List[ast.Stmt] = []
        while True:
            self._skip_newlines()
            if self._check("END") or self._is_at_end():
                break
            body.append(self._statement())
            self._match("NEWLINE")

        self._consume("END", "I expected 'end' to finish the function")
        return ast.FunctionDef(name, params, body)

    def _create_list_stmt(self) -> ast.CreateList:
        self._consume("A", "I expected 'a' after 'create'")
        self._consume("LIST", "I expected 'list' after 'create a'")
        self._consume("CALLED", "I expected 'called' after 'create a list'")
        name = self._consume("IDENT", "I expected the list name after 'called'").lexeme
        self._consume("CONTAINING", "I expected 'containing' after the list name")

        items: List[ast.Expr] = []
        items.append(self._expression())
        while True:
            if self._match("COMMA") or self._match("AND"):
                items.append(self._expression())
            else:
                break
        return ast.CreateList(name, items)

    def _create_window_stmt(self) -> ast.CreateWindow:
        # We have already consumed 'create', and next token is 'window'.
        self._consume("WINDOW", "I expected 'window' after 'create'")
        self._consume("WITH", "I expected 'with' after 'create window'")
        self._consume("NAME", "I expected 'name' after 'with'")
        name = self._consume("IDENT", "I expected the window name").lexeme
        return ast.CreateWindow(name)

    def _add_gui_stmt(self) -> ast.Stmt:
        # We have already consumed 'add'.
        if self._match("BUTTON"):
            kind = "button"
        elif self._match("LABEL"):
            kind = "label"
        elif self._match("ENTRY"):
            kind = "entry"
        else:
            raise self._error(self._peek(), "I expected 'button', 'label', or 'entry' after 'add'")

        self._consume("TO", "I expected 'to' after the control type")
        window_name = self._consume(
            "IDENT", "I expected the window name after 'to'"
        ).lexeme
        self._consume("WITH", "I expected 'with' after the window name")
        self._consume("NAME", "I expected 'name' after 'with'")
        widget_name = self._consume(
            "IDENT", "I expected the control name after 'name'"
        ).lexeme

        if kind == "button":
            return ast.AddButton(window_name=window_name, button_name=widget_name)
        if kind == "entry":
            return ast.AddEntry(window_name=window_name, entry_name=widget_name)
        return ast.AddLabel(window_name=window_name, label_name=widget_name)

    def _set_size_stmt(self, window_name: str) -> ast.SetGuiSize:
        # Grammar: set WINDOW size to x equals 300, y equals 300
        self._consume("TO", "I expected 'to' after 'size'")
        x_tok = self._consume("IDENT", "I expected 'x' after 'size to'")
        if x_tok.lexeme.lower() != "x":
            raise self._error(x_tok, "I expected 'x' after 'size to'")
        # allow either 'equals' or 'is equal to'
        if self._match("EQUALS"):
            pass
        elif self._match("IS"):
            self._consume("EQUAL", "I expected 'equal' after 'is'")
            self._consume("TO", "I expected 'to' after 'equal'")
        else:
            self._consume("EQUALS", "I expected 'equals' after 'x'")
        x_token = self._consume("NUMBER", "I expected a number for the x value")
        # comma between coordinates
        if self._check("COMMA"):
            self._advance()
        y_tok = self._consume("IDENT", "I expected 'y' after the x value")
        if y_tok.lexeme.lower() != "y":
            raise self._error(y_tok, "I expected 'y' after the x value")
        if self._match("EQUALS"):
            pass
        elif self._match("IS"):
            self._consume("EQUAL", "I expected 'equal' after 'is'")
            self._consume("TO", "I expected 'to' after 'equal'")
        else:
            self._consume("EQUALS", "I expected 'equals' after 'y'")
        y_token = self._consume("NUMBER", "I expected a number for the y value")
        return ast.SetGuiSize(window_name, int(x_token.lexeme), int(y_token.lexeme))

    def _show_widget_stmt(self) -> ast.ShowWidget:
        # show mygui
        # show testbutton in x equals 10, y equals 20
        name = self._consume("IDENT", "I expected a widget or window name after 'show'").lexeme
        if not self._match("IN"):
            return ast.ShowWidget(name=name)
        x_tok = self._consume("IDENT", "I expected 'x' after 'in'")
        if x_tok.lexeme.lower() != "x":
            raise self._error(x_tok, "I expected 'x' after 'in'")
        # again support 'equals' or 'is equal to'
        if self._match("EQUALS"):
            pass
        elif self._match("IS"):
            self._consume("EQUAL", "I expected 'equal' after 'is'")
            self._consume("TO", "I expected 'to' after 'equal'")
        else:
            self._consume("EQUALS", "I expected 'equals' after 'x'")
        x_expr = self._expression()
        if self._check("COMMA"):
            self._advance()
        y_tok = self._consume("IDENT", "I expected 'y' after the x expression")
        if y_tok.lexeme.lower() != "y":
            raise self._error(y_tok, "I expected 'y' after the x expression")
        if self._match("EQUALS"):
            pass
        elif self._match("IS"):
            self._consume("EQUAL", "I expected 'equal' after 'is'")
            self._consume("TO", "I expected 'to' after 'equal'")
        else:
            self._consume("EQUALS", "I expected 'equals' after 'y'")
        y_expr = self._expression()
        return ast.ShowWidget(name=name, x=x_expr, y=y_expr)

    def _math_update_stmt(self, previous_kind: str) -> ast.MathUpdate:
        kind = previous_kind  # Already consumed the verb token.
        if kind in ("ADD", "SUBTRACT"):
            expr = self._expression()
            if kind == "ADD":
                self._consume("TO", "I expected 'to' after the value in 'add'")
            else:
                self._consume("FROM", "I expected 'from' after the value in 'subtract'")
            target = self._consume("IDENT", "I expected a variable name").lexeme
        else:
            # MULTIPLY or DIVIDE
            target = self._consume("IDENT", "I expected a variable name").lexeme
            self._consume("BY", "I expected 'by' after the variable name")
            expr = self._expression()
        return ast.MathUpdate(kind, target, expr)

    # Expressions ----------------------------------------------------------

    def _expression(self) -> ast.Expr:
        return self._or()

    def _or(self) -> ast.Expr:
        expr = self._and()
        while self._match("OR"):
            op = self._previous().type
            right = self._and()
            expr = ast.Binary(expr, op, right)
        return expr

    def _and(self) -> ast.Expr:
        expr = self._not()
        while self._match("AND"):
            op = self._previous().type
            right = self._not()
            expr = ast.Binary(expr, op, right)
        return expr

    def _not(self) -> ast.Expr:
        if self._match("NOT"):
            op = self._previous().type
            right = self._not()
            return ast.Unary(op, right)
        return self._comparison()

    def _comparison(self) -> ast.Expr:
        left = self._sum()

        # Handle comparison operators following the comp_op patterns.
        if self._match("IS"):
            # Possible multi-word comparison.
            if self._match("NOT"):
                if self._match("EQUAL"):
                    self._consume("TO", "I expected 'to' after 'not equal'")
                    op = "IS_NOT_EQUAL"
                elif self._match("GREATER"):
                    self._consume("THAN", "I expected 'than' after 'greater'")
                    op = "IS_NOT_GREATER"
                elif self._match("LESS"):
                    self._consume("THAN", "I expected 'than' after 'less'")
                    op = "IS_NOT_LESS"
                else:
                    raise self._error(self._peek(), "I expected 'equal', 'greater', or 'less' after 'is not'")
            else:
                if self._match("EQUAL"):
                    self._consume("TO", "I expected 'to' after 'equal'")
                    op = "IS_EQUAL"
                elif self._match("GREATER"):
                    self._consume("THAN", "I expected 'than' after 'greater'")
                    op = "IS_GREATER"
                elif self._match("LESS"):
                    self._consume("THAN", "I expected 'than' after 'less'")
                    op = "IS_LESS"
                else:
                    # Bare 'is' means equality.
                    op = "IS_EQUAL"
        elif self._match("EQUALS"):
            op = "IS_EQUAL"
        else:
            return left

        right = self._sum()
        return ast.Binary(left, op, right)

    def _sum(self) -> ast.Expr:
        expr = self._product()
        while self._match("PLUS", "MINUS"):
            op = self._previous().type
            right = self._product()
            expr = ast.Binary(expr, op, right)
        return expr

    def _product(self) -> ast.Expr:
        expr = self._unary()
        while True:
            if self._match("TIMES", "MULTIPLIED"):
                if self._previous().type == "MULTIPLIED":
                    self._consume("BY", "I expected 'by' after 'multiplied'")
                op = "TIMES"
                right = self._unary()
                expr = ast.Binary(expr, op, right)
            elif self._match("DIVIDED"):
                self._consume("BY", "I expected 'by' after 'divided'")
                op = "DIVIDED"
                right = self._unary()
                expr = ast.Binary(expr, op, right)
            elif self._match("OVER"):
                op = "DIVIDED"
                right = self._unary()
                expr = ast.Binary(expr, op, right)
            elif self._match("MODULO"):
                op = "MODULO"
                right = self._unary()
                expr = ast.Binary(expr, op, right)
            else:
                break
        return expr

    def _unary(self) -> ast.Expr:
        # For now there are no numeric unary operators; NOT is handled earlier.
        return self._primary()

    def _primary(self) -> ast.Expr:
        # Literals
        if self._match("NUMBER"):
            value = int(self._previous().lexeme)
            return ast.Literal(value)
        if self._match("STRING"):
            return ast.Literal(self._previous().lexeme)
        if self._match("TRUE"):
            return ast.Literal(True)
        if self._match("FALSE"):
            return ast.Literal(False)
        if self._match("NOTHING"):
            return ast.Literal(None)

        # List access / length expressions
        if self._match("GET"):
            return self._list_access()
        if self._match("LENGTH"):
            self._consume("OF", "I expected 'of' after 'length'")
            list_expr = self._expression()
            return ast.LengthOf(list_expr)

        if self._match("TEXT"):
            self._consume("OF", "I expected 'of' after 'text'")
            name = self._consume("IDENT", "I expected a control name after 'text of'").lexeme
            return ast.TextOf(name)

        # Call expressions
        if self._match("CALL"):
            return self._call_expr()

        # Variable
        if self._match("IDENT"):
            name = self._previous().lexeme
            return ast.Variable(name)

        token = self._peek()
        raise self._error(token, "I did not understand this part of the sentence")

    def _call_expr(self) -> ast.Call:
        name = self._consume("IDENT", "I expected the function name after 'call'").lexeme
        args: List[ast.Expr] = []
        if self._match("WITH"):
            args.append(self._expression())
            while self._match("COMMA") or self._match("AND"):
                args.append(self._expression())
        return ast.Call(name, args)

    def _list_access(self) -> ast.ListAccess:
        self._consume("THE", "I expected 'the' after 'get'")
        if self._match("FIRST"):
            self._consume("ITEM", "I expected 'item' after 'first'")
            self._consume("FROM", "I expected 'from' after 'first item'")
            list_expr = self._expression()
            index_expr = ast.Literal(0)  # 0-based internally, but conceptually 'first'.
            return ast.ListAccess(list_expr, index_expr)
        if self._match("LAST"):
            self._consume("ITEM", "I expected 'item' after 'last'")
            self._consume("FROM", "I expected 'from' after 'last item'")
            list_expr = self._expression()
            # Use a sentinel to mean "last", interpreter will handle -1.
            index_expr = ast.Literal(-1)
            return ast.ListAccess(list_expr, index_expr)

        # Positional access: get the item at position N from list
        self._consume("ITEM", "I expected 'item' after 'the'")
        self._consume("AT", "I expected 'at' after 'item'")
        self._consume("POSITION", "I expected 'position' after 'at'")
        index_expr = self._expression()
        self._consume("FROM", "I expected 'from' after the position")
        list_expr = self._expression()
        return ast.ListAccess(list_expr, index_expr)

    def _when_stmt(self) -> ast.OnClick:
        widget_name = self._consume("IDENT", "I expected a control name after 'when'").lexeme
        self._consume("IS", "I expected 'is' after the control name")
        self._consume("CLICKED", "I expected 'clicked' after 'is'")
        self._consume("THEN", "I expected 'then' after 'is clicked'")
        # Inline form: "when btn is clicked then call foo with 1"
        if not self._match("NEWLINE"):
            self._consume("CALL", "I expected 'call' after 'then' in an inline when")
            call_expr = self._call_expr()
            return ast.OnClick(widget_name, [ast.ExprStmt(call_expr)])

        # Block form:
        body: List[ast.Stmt] = []
        while True:
            self._skip_newlines()
            if self._check("END") or self._is_at_end():
                break
            body.append(self._statement())
            self._match("NEWLINE")

        self._consume("END", "I expected 'end' to finish the when block")
        return ast.OnClick(widget_name, body)

    # Helpers ------------------------------------------------------------

    def _skip_newlines(self) -> None:
        """Consume any number of NEWLINE tokens to allow blank lines."""
        while self._match("NEWLINE"):
            pass

    # Utility methods ------------------------------------------------------

    def _match(self, *types: str) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, type_: str, message: str) -> Token:
        if self._check(type_):
            return self._advance()
        raise self._error(self._peek(), message)

    def _check(self, type_: str) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == type_

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == "EOF"

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _peek_next(self) -> Token:
        if self.current + 1 >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.current + 1]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> ELangSyntaxError:
        return ELangSyntaxError(message, line=token.line, column=token.column)
