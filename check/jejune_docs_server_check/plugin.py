import os
import urllib.error
import urllib.request

import click

from jejune_cli.plugin import JejunePlugin

_DEFAULT_PORT = "8765"
_CONFIG_VAR = "DOCS_SERVER_PORT"


def _check_availability() -> tuple[bool, str]:
    port = os.environ.get(_CONFIG_VAR, _DEFAULT_PORT)
    url = f"http://localhost:{port}/catalog"
    try:
        urllib.request.urlopen(url, timeout=2)
        return True, f"responding on :{port}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, str(exc)


@click.group("docs-server")
def docs_server_group():
    """Commands for the jejune docs-server UI component."""


@docs_server_group.command("status-availability")
def status_availability():
    """Show docs-server availability status (mirrors the doctor Status column)."""
    ok, _ = _check_availability()
    if ok:
        click.echo(f"docs-server: {click.style('ok', fg='green')}")
    else:
        click.echo(f"docs-server: {click.style('error', fg='red')}")


@docs_server_group.command("hint-availability")
def hint_availability():
    """Show how to start the docs-server container."""
    ok, _ = _check_availability()
    if ok:
        click.echo(click.style("docs-server is reachable", fg="green"))
    else:
        click.echo("run `docker compose --env-file deployment.env up -d`")


plugin = JejunePlugin(
    name="docs-server",
    group=docs_server_group,
    config_vars=[_CONFIG_VAR],
    config_hint=f"Set {_CONFIG_VAR} to the port exposed by the docs-server container (default {_DEFAULT_PORT}).",
    avail_hint="Run `docker compose up -d` in your SomeMac deployment directory.",
    check_availability=_check_availability,
    stage="extension",
)
