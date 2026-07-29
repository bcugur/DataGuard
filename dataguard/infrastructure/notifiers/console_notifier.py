"""ConsoleNotifier — INotifier implementation using rich for terminal output.

Renders a beautiful, colour-coded validation report table directly in the
terminal. Uses the ``rich`` library for formatting; no ANSI codes are
written manually.

Output structure:
    ┌─ Header: source file, timestamp, overall status ─────────────────┐
    │  Per-rule table: rule, column, status, score, threshold, message  │
    └─ Footer: overall score, pass/fail summary ────────────────────────┘
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from dataguard.domain.entities.report import ValidationReport
from dataguard.domain.ports.notifier_port import INotifier
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

# Colour constants — defined once, used throughout.
_COLOUR_PASS = "bold green"
_COLOUR_FAIL = "bold red"
_COLOUR_WARN = "bold yellow"
_COLOUR_SKIP = "dim"
_COLOUR_INFO = "bold cyan"

# ASCII-safe status icons (no emoji — Windows cp1254 compatible)
_STATUS_ICON = {
    "passed": "[OK]",
    "failed": "[!!]",
    "skipped": "[--]",
}

_SEVERITY_COLOUR = {
    "error": _COLOUR_FAIL,
    "warning": _COLOUR_WARN,
    "info": _COLOUR_INFO,
}


class ConsoleNotifier(INotifier):
    """Prints a formatted validation report to the terminal using rich.

    Args:
        console: rich Console instance. If None, a default stdout Console
            is created. Inject a custom Console in tests for capture.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(
            highlight=False,
            force_terminal=True,
            safe_box=True,  # use ASCII box-drawing when Unicode is unsafe
        )

    def notify(self, report: ValidationReport) -> None:
        """Render and print the validation report to the terminal.

        Args:
            report: The fully populated ValidationReport aggregate.
        """
        self._console.print()
        self._print_header(report)
        self._print_results_table(report)
        self._print_footer(report)
        self._console.print()

    # ── Private rendering methods ──────────────────────────────────────────

    def _print_header(self, report: ValidationReport) -> None:
        """Print the validation run header panel."""
        status_colour = _COLOUR_PASS if report.overall_status == "passed" else _COLOUR_FAIL
        status_label = "PASSED" if report.overall_status == "passed" else "FAILED"
        status_text = f"[{status_colour}]{status_label}[/{status_colour}]"

        header_content = (
            f"[bold]Source:[/bold]     {report.source_name}\n"
            f"[bold]Rules:[/bold]      {report.rules_path}\n"
            f"[bold]Run at:[/bold]     {report.executed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"[bold]Report ID:[/bold]  {report.report_id}\n"
            f"[bold]Status:[/bold]     {status_text}"
        )
        self._console.print(
            Panel(
                header_content,
                title="[bold cyan]DataGuard Validation Report[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def _print_results_table(self, report: ValidationReport) -> None:
        """Print the per-rule results table."""
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            border_style="bright_black",
            row_styles=["", "dim"],  # alternating row shading
            expand=True,
        )

        table.add_column("Rule", style="bold", min_width=20)
        table.add_column("Column", min_width=12)
        table.add_column("Status", justify="center", min_width=10)
        table.add_column("Score", justify="right", min_width=8)
        table.add_column("Threshold", justify="right", min_width=10)
        table.add_column("Severity", justify="center", min_width=10)
        table.add_column("Message", min_width=30)

        for result in report.results:
            icon = _STATUS_ICON.get(result.status, "?")
            status_colour = (
                _COLOUR_PASS if result.passed else
                _COLOUR_SKIP if result.status == "skipped" else
                _COLOUR_FAIL
            )
            severity_colour = _SEVERITY_COLOUR.get(result.severity, "white")

            score_text = Text(f"{result.score:.3f}", style=status_colour)
            threshold_text = Text(f"{result.threshold:.3f}", style="dim")

            table.add_row(
                result.rule_name,
                result.column or "—",
                f"[{status_colour}]{icon} {result.status.upper()}[/{status_colour}]",
                score_text,
                threshold_text,
                f"[{severity_colour}]{result.severity.upper()}[/{severity_colour}]",
                result.message,
            )

        self._console.print(table)

    def _print_footer(self, report: ValidationReport) -> None:
        """Print the aggregate summary footer."""
        score_colour = _COLOUR_PASS if report.overall_score >= 0.8 else _COLOUR_FAIL
        footer_content = (
            f"[bold]Overall Score:[/bold]  [{score_colour}]{report.overall_score:.3f}[/{score_colour}]\n"
            f"[bold]Rules:[/bold]          "
            f"[green]{report.passed_rules} passed[/green]  "
            f"[red]{report.failed_rules} failed[/red]  "
            f"[dim]{report.skipped_rules} skipped[/dim]  "
            f"/ {report.total_rules} total"
        )
        overall_colour = "green" if report.overall_status == "passed" else "red"
        overall_label = "VALIDATION PASSED" if report.overall_status == "passed" else "VALIDATION FAILED"
        self._console.print(
            Panel(
                footer_content,
                title=f"[bold {overall_colour}]{overall_label}[/bold {overall_colour}]",
                border_style=overall_colour,
                padding=(1, 2),
            )
        )
