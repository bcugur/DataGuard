"""DataGuard CLI — entry point.

Registers all sub-commands and exposes the ``app`` object used by the
``dataguard`` console script defined in pyproject.toml.

Usage:
    dataguard --help
    dataguard validate --source data.csv --rules rules.yaml
    dataguard serve
"""

from __future__ import annotations

import typer

from dataguard import __version__
from dataguard.delivery.cli.commands.serve import serve_command
from dataguard.delivery.cli.commands.validate import validate_command

# ---------------------------------------------------------------------------
# Typer application
# ---------------------------------------------------------------------------
app = typer.Typer(
    name="dataguard",
    help=(
        "DataGuard — Data Quality Platform.\n\n"
        "Validate datasets against configurable quality rules "
        "and generate structured reports.\n\n"
        "Use [bold cyan]dataguard serve[/bold cyan] to open the web dashboard."
    ),
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    """Print version and exit when --version is passed."""
    if value:
        typer.echo(f"DataGuard v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(  # noqa: FBT001
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show DataGuard version and exit.",
    ),
) -> None:
    """DataGuard — Data Quality Platform."""


# ── Register commands ──────────────────────────────────────────────────────
app.command(
    name="validate",
    help="Validate a data file against a YAML rule set.",
)(validate_command)

app.command(
    name="serve",
    help="Start the web dashboard (opens browser automatically).",
)(serve_command)


if __name__ == "__main__":
    app()
