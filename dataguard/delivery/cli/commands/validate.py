"""dataguard validate — CLI command for running a validation.

Wires together all infrastructure adapters and the use case,
then delegates execution to RunValidationUseCase.

Exit codes:
    0 — Validation passed (all error-severity rules passed)
    1 — Validation failed (at least one error-severity rule failed)
    2 — Execution error (file not found, YAML parse error, etc.)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dataguard.application.dtos.validation_request import ValidationRequest
from dataguard.application.use_cases.run_validation import RunValidationUseCase
from dataguard.infrastructure.notifiers.console_notifier import ConsoleNotifier
from dataguard.infrastructure.readers.csv_reader import CSVReader
from dataguard.infrastructure.readers.json_reader import JSONReader
from dataguard.infrastructure.repositories.file_rule_repo import FileRuleRepository
from dataguard.infrastructure.writers.json_writer import JSONReportWriter
from dataguard.shared.config import get_settings
from dataguard.shared.exceptions import DataGuardError
from dataguard.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)

_error_console = Console(stderr=True)


def _resolve_reader(source: Path) -> CSVReader | JSONReader:
    """Select the correct data reader based on the file extension.

    Args:
        source: Path to the data source file.

    Returns:
        The appropriate IDataReader implementation.

    Raises:
        typer.Exit: If no reader supports the given extension.
    """
    readers: list[CSVReader | JSONReader] = [CSVReader(), JSONReader()]
    for reader in readers:
        if reader.supports(source):
            return reader

    _error_console.print(
        f"[bold red]✗ Unsupported file format:[/bold red] '{source.suffix}'. "
        f"Supported: .csv, .json"
    )
    raise typer.Exit(code=2)


def validate_command(
    source: Annotated[
        Path,
        typer.Option(
            "--source", "-s",
            help="Path to the data file to validate (.csv or .json).",
            show_default=False,
        ),
    ],
    rules: Annotated[
        Path,
        typer.Option(
            "--rules", "-r",
            help="Path to the YAML rule definition file.",
            show_default=False,
        ),
    ],
    report_dir: Annotated[
        Path,
        typer.Option(
            "--report-dir", "-o",
            help="Directory where the JSON report will be saved.",
        ),
    ] = Path("reports"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Enable verbose (DEBUG) logging output.",
        ),
    ] = False,
) -> None:
    """Validate a data file against a set of quality rules.

    Runs all rules defined in the YAML file against the source data,
    prints a formatted report to the terminal, and saves a JSON report.

    \b
    Examples:
        dataguard validate --source data.csv --rules rules.yaml
        dataguard validate -s data.json -r rules.yaml -o ./output --verbose
    """
    # ── Configure logging ──────────────────────────────────────────────────
    log_level = "DEBUG" if verbose else get_settings().log_level
    configure_logging(level=log_level)

    try:
        # ── Build ValidationRequest (validates paths via pydantic) ─────────
        request = ValidationRequest(
            source_path=source,
            rules_path=rules,
            report_dir=report_dir,
            verbose=verbose,
        )

        # ── Wire infrastructure adapters ───────────────────────────────────
        reader = _resolve_reader(source)
        use_case = RunValidationUseCase(
            reader=reader,
            rule_repository=FileRuleRepository(),
            report_writer=JSONReportWriter(),
            notifier=ConsoleNotifier(),
        )

        # ── Execute ────────────────────────────────────────────────────────
        response = use_case.execute(request)

        # ── Report path confirmation ───────────────────────────────────────
        Console().print(
            f"\n[dim]Report saved:[/dim] [cyan]{response.report_path}[/cyan]\n"
        )

        # ── Exit code ──────────────────────────────────────────────────────
        raise typer.Exit(code=0 if response.succeeded else 1)

    except DataGuardError as exc:
        _error_console.print(f"\n[bold red]✗ Error:[/bold red] {exc}\n")
        logger.debug("DataGuardError detail: %s | context=%s", exc.message, exc.context)
        raise typer.Exit(code=2) from exc

    except typer.Exit:
        raise  # re-raise exit codes transparently

    except Exception as exc:
        _error_console.print(
            f"\n[bold red]✗ Unexpected error:[/bold red] {exc}\n"
            f"Run with [yellow]--verbose[/yellow] for details.\n"
        )
        logger.exception("Unexpected error during validation.")
        raise typer.Exit(code=2) from exc
