"""dataguard serve — CLI command to start the web dashboard.

Starts the FastAPI server with uvicorn and automatically
opens the dashboard in the default web browser.
"""

from __future__ import annotations

import threading
import webbrowser
from typing import Annotated

import typer
import uvicorn


def serve_command(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host address to bind to."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port number to listen on."),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload for development."),
    ] = False,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not open browser automatically."),
    ] = False,
) -> None:
    """Start the DataGuard web dashboard.

    Launches a local web server and opens the dashboard in your browser.
    Upload your data file and rules file, then click Run Validation.

    \b
    Examples:
        dataguard serve
        dataguard serve --port 9000
        dataguard serve --no-browser
    """
    url = f"http://{host}:{port}"

    typer.echo(f"\n  DataGuard Web Dashboard")
    typer.echo(f"  Running at: {url}")
    typer.echo(f"  Press Ctrl+C to stop.\n")

    if not no_browser:
        # Open browser after a short delay to let the server start.
        threading.Timer(
            interval=1.2,
            function=lambda: webbrowser.open(url),
        ).start()

    uvicorn.run(
        "dataguard.delivery.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="warning",  # suppress uvicorn's own logs; we use our logger
    )
