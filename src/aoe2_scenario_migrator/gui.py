from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .service import APP_VERSION, ConversionOptions, convert_file

SUPPORTED_SUFFIXES = {".scn", ".scx", ".scx2"}


class MigratorApp(tk.Tk):
    def __init__(self, initial_files: list[Path] | None = None):
        super().__init__()
        self.title(f"AoE2 Scenario Migrator {APP_VERSION}")
        self.geometry("1040x780")
        self.minsize(860, 650)
        self.configure(bg="#171b22")
        self.files: list[Path] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False
        self.last_output_dir: Path | None = None
        self._configure_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll_events)
        for path in initial_files or []:
            self._add_path(path)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#171b22")
        style.configure("Card.TFrame", background="#222832")
        style.configure("TLabel", background="#171b22", foreground="#e8edf2", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 24), foreground="#f6d08a")
        style.configure("Muted.TLabel", foreground="#aab4c0")
        style.configure("Card.TLabel", background="#222832", foreground="#e8edf2")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 8))
        style.configure("Accent.TButton", background="#c9772d", foreground="white")
        style.map("Accent.TButton", background=[("active", "#df8d3f"), ("disabled", "#6d5847")])
        style.configure("TCheckbutton", background="#222832", foreground="#e8edf2")
        style.map("TCheckbutton", background=[("active", "#222832")])
        style.configure("Treeview", background="#151a21", fieldbackground="#151a21", foreground="#edf1f5", rowheight=28)
        style.configure("Treeview.Heading", background="#343c48", foreground="#f7dfb3", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", "#8a4c20")])
        style.configure("Horizontal.TProgressbar", troughcolor="#10141a", background="#d08138")

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(24, 20, 24, 12))
        header.pack(fill="x")
        ttk.Label(header, text="AoE2 Scenario Migrator", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="AoK • AoC • HD  →  latest supported AoE2 DE format  |  safe repair, batch conversion, full validation",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="Add scenarios…", command=self._choose_files).pack(side="left")
        ttk.Button(toolbar, text="Add folder…", command=self._choose_folder).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Remove selected", command=self._remove_selected).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Clear", command=self._clear).pack(side="left", padx=(8, 0))
        self.count_label = ttk.Label(toolbar, text="0 files", style="Card.TLabel")
        self.count_label.pack(side="right")

        self.tree = ttk.Treeview(card, columns=("path", "status"), show="headings", selectmode="extended")
        self.tree.heading("path", text="Legacy scenario")
        self.tree.heading("status", text="Status")
        self.tree.column("path", width=720, anchor="w")
        self.tree.column("status", width=180, anchor="w")
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        settings = ttk.Frame(self, style="Card.TFrame", padding=16)
        settings.pack(fill="x", padx=24, pady=(0, 12))
        output_row = ttk.Frame(settings, style="Card.TFrame")
        output_row.pack(fill="x")
        ttk.Label(output_row, text="Output folder", style="Card.TLabel").pack(side="left")
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_row, textvariable=self.output_var)
        output_entry.pack(side="left", fill="x", expand=True, padx=12)
        ttk.Button(output_row, text="Browse…", command=self._choose_output).pack(side="left")
        ttk.Label(
            settings,
            text="Leave empty to save beside each source. Originals are never modified.",
            style="Card.TLabel",
        ).pack(anchor="w", pady=(7, 10))

        options_row = ttk.Frame(settings, style="Card.TFrame")
        options_row.pack(fill="x")
        self.overwrite_var = tk.BooleanVar(value=False)
        self.aggressive_var = tk.BooleanVar(value=False)
        self.json_var = tk.BooleanVar(value=True)
        self.html_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="Overwrite with .bak backup", variable=self.overwrite_var).pack(side="left")
        ttk.Checkbutton(options_row, text="Aggressive duplicate-ID repair", variable=self.aggressive_var).pack(side="left", padx=18)
        ttk.Checkbutton(options_row, text="JSON report", variable=self.json_var).pack(side="left")
        ttk.Checkbutton(options_row, text="HTML report", variable=self.html_var).pack(side="left", padx=18)

        footer = ttk.Frame(self, padding=(24, 0, 24, 20))
        footer.pack(fill="x")
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        action_row = ttk.Frame(footer)
        action_row.pack(fill="x")
        self.status_label = ttk.Label(action_row, text="Ready", style="Muted.TLabel")
        self.status_label.pack(side="left")
        self.open_button = ttk.Button(action_row, text="Open output folder", command=self._open_output, state="disabled")
        self.open_button.pack(side="right", padx=(8, 0))
        self.convert_button = ttk.Button(action_row, text="Convert and validate", style="Accent.TButton", command=self._start)
        self.convert_button.pack(side="right")

    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select AoE2 legacy scenarios",
            filetypes=[("AoE2 legacy scenarios", "*.scn *.scx *.scx2"), ("All files", "*.*")],
        )
        for path in paths:
            self._add_path(Path(path))

    def _choose_folder(self) -> None:
        directory = filedialog.askdirectory(title="Add all legacy scenarios from folder")
        if not directory:
            return
        for path in sorted(Path(directory).rglob("*")):
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                self._add_path(path)

    def _choose_output(self) -> None:
        directory = filedialog.askdirectory(title="Choose output folder")
        if directory:
            self.output_var.set(directory)

    def _add_path(self, path: Path) -> None:
        path = path.expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES or path in self.files:
            return
        self.files.append(path)
        self.tree.insert("", "end", iid=str(len(self.files) - 1), values=(str(path), "Queued"))
        self._refresh_count()

    def _rebuild_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, path in enumerate(self.files):
            self.tree.insert("", "end", iid=str(index), values=(str(path), "Queued"))
        self._refresh_count()

    def _remove_selected(self) -> None:
        selected = {int(item) for item in self.tree.selection()}
        self.files = [path for index, path in enumerate(self.files) if index not in selected]
        self._rebuild_tree()

    def _clear(self) -> None:
        if not self.running:
            self.files.clear()
            self._rebuild_tree()

    def _refresh_count(self) -> None:
        self.count_label.configure(text=f"{len(self.files)} file{'s' if len(self.files) != 1 else ''}")

    def _start(self) -> None:
        if self.running:
            return
        if not self.files:
            messagebox.showinfo("AoE2 Scenario Migrator", "Add at least one .scn, .scx or .scx2 file.")
            return
        output = Path(self.output_var.get()).expanduser().resolve() if self.output_var.get().strip() else None
        options = ConversionOptions(
            output_dir=output,
            overwrite=self.overwrite_var.get(),
            aggressive_repair=self.aggressive_var.get(),
            json_report=self.json_var.get(),
            html_report=self.html_var.get(),
        )
        self.running = True
        self.convert_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        threading.Thread(target=self._worker, args=(list(self.files), options), daemon=True).start()

    def _worker(self, files: list[Path], options: ConversionOptions) -> None:
        successes = 0
        outputs: list[Path] = []
        for index, path in enumerate(files):
            self.events.put(("row", (index, "Reading…")))
            try:
                report = convert_file(
                    path,
                    options,
                    progress=lambda message, i=index: self.events.put(("progress", (i, message))),
                )
                outputs.append(Path(report["output"]))
                successes += 1
                self.events.put(("row", (index, "Validated ✓")))
            except Exception as exc:  # noqa: BLE001 - GUI boundary continues the batch after one file fails.
                self.events.put(("row", (index, "Failed")))
                self.events.put(("error", f"{path.name}\n\n{exc}"))
            self.events.put(("step", index + 1))
        self.events.put(("done", (successes, len(files), outputs)))

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "row":
                    index, status = payload
                    iid = str(index)
                    if self.tree.exists(iid):
                        values = list(self.tree.item(iid, "values"))
                        values[1] = status
                        self.tree.item(iid, values=values)
                elif event == "progress":
                    _index, message = payload
                    self.status_label.configure(text=message)
                elif event == "step":
                    self.progress.configure(value=payload)
                elif event == "error":
                    messagebox.showerror("Conversion failed", str(payload))
                elif event == "done":
                    successes, total, outputs = payload
                    self.running = False
                    self.convert_button.configure(state="normal")
                    self.status_label.configure(text=f"Completed: {successes}/{total} validated")
                    if outputs:
                        self.last_output_dir = outputs[-1].parent
                        self.open_button.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _open_output(self) -> None:
        if self.last_output_dir and self.last_output_dir.exists():
            os.startfile(self.last_output_dir)

    def _close(self) -> None:
        if self.running and not messagebox.askyesno("Conversion running", "Close while conversion is still running?"):
            return
        self.destroy()


def _enable_high_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    _enable_high_dpi()
    initial = [Path(arg) for arg in (argv if argv is not None else sys.argv[1:])]
    app = MigratorApp(initial)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
