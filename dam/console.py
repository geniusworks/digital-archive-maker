"""Rich console helpers for consistent, beautiful terminal output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# Project-wide theme
DAM_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "heading": "bold magenta",
        "muted": "dim",
        "key": "bold cyan",
        "value": "white",
    }
)

console = Console(theme=DAM_THEME)


def banner() -> None:
    """Print the Digital Archive Maker banner."""
    console.print(
        Panel.fit(
            "[bold white]Digital Archive Maker[/]\n"
            "[muted]Physical media → digital library automation[/]",
            border_style="cyan",
        )
    )


def heading(text: str) -> None:
    """Print a section heading."""
    console.print(f"\n[heading]▸ {text}[/]")


def success(text: str) -> None:
    console.print(f"[success]✓[/] {text}")


def warning(text: str) -> None:
    console.print(f"[warning]⚠[/] {text}")


def error(text: str) -> None:
    console.print(f"[error]✗[/] {text}")


def info(text: str) -> None:
    console.print(f"[info]ℹ[/] {text}")


def kv(key: str, value: str, indent: int = 2) -> None:
    """Print a key-value pair."""
    pad = " " * indent
    console.print(f"{pad}[key]{key}:[/] [value]{value}[/]")


def status_table(rows: list[tuple[str, str, str]], title: str = "") -> None:
    """Print a status table: [(name, status_emoji, detail), ...]."""
    table = Table(title=title, show_header=False, box=None, padding=(0, 1))
    table.add_column("Status", width=2)
    table.add_column("Item", style="white")
    table.add_column("Detail", style="muted")
    for name, status, detail in rows:
        table.add_row(status, name, detail)
    console.print(table)
