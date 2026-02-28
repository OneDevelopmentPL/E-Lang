from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from elang.errors import ELangError
from elang.interpreter import run_source


KEYWORDS = {
    "let",
    "set",
    "if",
    "then",
    "otherwise",
    "end",
    "while",
    "do",
    "repeat",
    "times",
    "define",
    "function",
    "called",
    "that",
    "takes",
    "and",
    "does",
    "call",
    "with",
    "say",
    "display",
    "create",
    "list",
    "containing",
    "get",
    "first",
    "last",
    "item",
    "from",
    "length",
    "add",
    "subtract",
    "multiply",
    "divide",
    "return",
    "true",
    "false",
    "nothing",
    "not",
    "greater",
    "less",
    "equal",
    "equals",
    "is",
    "or",
    "plus",
    "minus",
    "multiplied",
    "by",
    "divided",
    "over",
    "modulo",
}


class ELangGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("E-Lang Playground")
        self._apply_icon()

        self.geometry("900x600")

        self._create_widgets()
        self.current_path: str | None = None

    def _apply_icon(self) -> None:
        # Try to set a custom icon if an image is available.
        try:
            # Icon is generated into the assets directory managed by Cursor.
            icon_path = os.path.expanduser(
                "~/.cursor/projects/Users-iwo-Documents-GitHub-E-Lang/assets/elang-icon.png"
            )
            if os.path.exists(icon_path):
                icon_image = tk.PhotoImage(file=icon_path)
                self.iconphoto(False, icon_image)
        except Exception:
            # Failing to load an icon is harmless; ignore.
            pass

    def _create_widgets(self) -> None:
        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Run", command=self.run_code)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        # Editor and output panes
        main_pane = tk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        self.editor = tk.Text(main_pane, wrap=tk.NONE, undo=True)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.bind("<KeyRelease>", self._on_key_release)

        self.output = tk.Text(main_pane, wrap=tk.WORD, height=10, bg="#111", fg="#eee")
        self.output.configure(state=tk.DISABLED)

        main_pane.add(self.editor)
        main_pane.add(self.output)

        # Syntax highlighting tags
        self.editor.tag_configure("keyword", foreground="#0066cc")
        self.editor.tag_configure("comment", foreground="#888888")
        self.editor.tag_configure("string", foreground="#aa5500")

    # File operations -----------------------------------------------------

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("E-Lang files", "*.elang"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                contents = f.read()
        except OSError as exc:
            messagebox.showerror("Error", f"Could not open file:\n{exc}")
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", contents)
        self.current_path = path
        self._highlight_all()

    def save_file(self) -> None:
        if self.current_path is None:
            self.save_file_as()
            return
        self._save_to_path(self.current_path)

    def save_file_as(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".elang",
            filetypes=[("E-Lang files", "*.elang"), ("All files", "*.*")],
        )
        if not path:
            return
        self._save_to_path(path)
        self.current_path = path

    def _save_to_path(self, path: str) -> None:
        try:
            contents = self.editor.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(contents)
        except OSError as exc:
            messagebox.showerror("Error", f"Could not save file:\n{exc}")

    # Running code --------------------------------------------------------

    def run_code(self) -> None:
        source = self.editor.get("1.0", tk.END)
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        try:
            _, out = run_source(source)
            if out.strip():
                self.output.insert(tk.END, out)
            else:
                self.output.insert(tk.END, "(no output)\n")
        except ELangError as e:
            self.output.insert(tk.END, f"Something went wrong: {e}\n")
        finally:
            self.output.configure(state=tk.DISABLED)

    # Syntax highlighting -------------------------------------------------

    def _on_key_release(self, event: tk.Event) -> None:  # type: ignore[override]
        # Lightweight re-highlight on every keypress.
        self._highlight_all()

    def _highlight_all(self) -> None:
        text = self.editor.get("1.0", tk.END)

        # Clear old tags.
        for tag in ("keyword", "comment", "string"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        lines = text.splitlines(keepends=True)
        index = 0

        for line_no, line in enumerate(lines, start=1):
            start_index = f"{line_no}.0"

            # Comments: lines that contain 'note:' after optional whitespace.
            stripped = line.lstrip()
            offset = len(line) - len(stripped)
            if stripped.lower().startswith("note:"):
                comment_start = f"{line_no}.{offset}"
                comment_end = f"{line_no}.{len(line.rstrip())}"
                self.editor.tag_add("comment", comment_start, comment_end)
                continue

            # Strings: naive highlighting between double quotes on a line.
            col = 0
            while col < len(line):
                if line[col] == '"':
                    start_col = col
                    col += 1
                    while col < len(line) and line[col] != '"':
                        col += 1
                    if col < len(line) and line[col] == '"':
                        string_start = f"{line_no}.{start_col}"
                        string_end = f"{line_no}.{col + 1}"
                        self.editor.tag_add("string", string_start, string_end)
                    col += 1
                else:
                    col += 1

            # Keywords: match whole words only.
            words = line.split()
            running_col = 0
            for word in words:
                lower = word.lower().strip('",')
                word_start_col = line.find(word, running_col)
                word_end_col = word_start_col + len(word)
                running_col = word_end_col
                if lower in KEYWORDS:
                    start = f"{line_no}.{word_start_col}"
                    end = f"{line_no}.{word_end_col}"
                    self.editor.tag_add("keyword", start, end)

            index += len(line)


def main() -> None:
    app = ELangGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

