from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .errors import ELangSyntaxError


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int


KEYWORDS = {
    "let": "LET",
    "set": "SET",
    "be": "BE",
    "to": "TO",
    "if": "IF",
    "then": "THEN",
    "otherwise": "OTHERWISE",
    "end": "END",
    "while": "WHILE",
    "do": "DO",
    "repeat": "REPEAT",
    "times": "TIMES",
    "define": "DEFINE",
    "a": "A",
    "function": "FUNCTION",
    "called": "CALLED",
    "that": "THAT",
    "takes": "TAKES",
    "and": "AND",
    "does": "DOES",
    "call": "CALL",
    "with": "WITH",
    "say": "SAY",
    "display": "DISPLAY",
    "the": "THE",
    "value": "VALUE",
    "of": "OF",
    "create": "CREATE",
    "list": "LIST",
    "containing": "CONTAINING",
    "get": "GET",
    "first": "FIRST",
    "last": "LAST",
    "item": "ITEM",
    "from": "FROM",
    "at": "AT",
    "position": "POSITION",
    "length": "LENGTH",
    "add": "ADD",
    "subtract": "SUBTRACT",
    "multiply": "MULTIPLY",
    "divide": "DIVIDE",
    "return": "RETURN",
    "true": "TRUE",
    "false": "FALSE",
    "nothing": "NOTHING",
    "not": "NOT",
    "greater": "GREATER",
    "less": "LESS",
    "equal": "EQUAL",
    "equals": "EQUALS",
    "than": "THAN",
    "is": "IS",
    "or": "OR",
    "plus": "PLUS",
    "minus": "MINUS",
    "multiplied": "MULTIPLIED",
    "by": "BY",
    "divided": "DIVIDED",
    "over": "OVER",
    "modulo": "MODULO",
}


class Lexer:
    """Turn an E-Lang source string into a stream of tokens."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        while not self._is_at_end():
            ch = self._peek()

            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            if ch == "\n":
                self._add_token("NEWLINE", "\\n")
                self._advance_line()
                continue

            if ch == ",":
                # Commas act as separators in lists and argument lists.
                self._add_token("COMMA", ",")
                self._advance()
                continue

            if ch == '"':
                self._string()
                continue

            if ch.isdigit():
                self._number()
                continue

            if ch.isalpha():
                # Could be identifier, keyword, or start of a comment (`note:`).
                if self._starts_with_note_comment():
                    self._skip_comment()
                else:
                    self._identifier_or_keyword()
                continue

            raise ELangSyntaxError(
                f"I found an unexpected character '{ch}'",
                line=self.line,
                column=self.column,
            )

        self.tokens.append(Token("EOF", "", self.line, self.column))
        return self.tokens

    # Internal helpers -----------------------------------------------------

    def _is_at_end(self) -> bool:
        return self.index >= self.length

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.index]

    def _peek_next(self) -> str:
        if self.index + 1 >= self.length:
            return "\0"
        return self.source[self.index + 1]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        self.column += 1
        return ch

    def _advance_line(self) -> None:
        self.index += 1
        self.line += 1
        self.column = 1

    def _add_token(self, type_: str, lexeme: str) -> None:
        self.tokens.append(Token(type_, lexeme, self.line, self.column))

    def _string(self) -> None:
        # Consume opening quote.
        start_line = self.line
        start_column = self.column
        self._advance()
        start_index = self.index

        while not self._is_at_end() and self._peek() != '"':
            ch = self._peek()
            if ch == "\n":
                # Strings must stay on one line for simplicity.
                raise ELangSyntaxError(
                    "I expected the end of the string before the end of the line",
                    line=start_line,
                    column=start_column,
                )
            self._advance()

        if self._is_at_end():
            raise ELangSyntaxError(
                "I reached the end of the file while reading a string",
                line=start_line,
                column=start_column,
            )

        # Consume closing quote.
        value = self.source[start_index : self.index]
        self._advance()
        self.tokens.append(Token("STRING", value, start_line, start_column))

    def _number(self) -> None:
        start_index = self.index
        start_column = self.column
        while self._peek().isdigit():
            self._advance()
        lexeme = self.source[start_index : self.index]
        self.tokens.append(Token("NUMBER", lexeme, self.line, start_column))

    def _identifier_or_keyword(self) -> None:
        start_index = self.index
        start_column = self.column
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        lexeme = self.source[start_index : self.index]
        lower = lexeme.lower()
        type_ = KEYWORDS.get(lower, "IDENT")
        self.tokens.append(Token(type_, lexeme, self.line, start_column))

    def _starts_with_note_comment(self) -> bool:
        """Return True if the upcoming word is `note:` (case-insensitive)."""
        # Capture from current position up to the next whitespace or newline.
        i = self.index
        word_chars = []
        while i < self.length and not self.source[i].isspace():
            word_chars.append(self.source[i])
            i += 1
        word = "".join(word_chars).lower()
        return word.startswith("note:")

    def _skip_comment(self) -> None:
        # Skip until end of line.
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()
        # NEWLINE will be handled in the main loop.

