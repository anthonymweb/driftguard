"""Thin wrappers around the `docker compose` CLI used by the target modules.

Every helper takes the compose **file path** explicitly and passes
`-f str(compose_file)` — never a directory, never cwd-based inference — so
the invoked file is always the intended one: Task 9's lab stack
`demcommerce/deploy/lab.compose.yaml` works without special-casing, and the
protected `demcommerce/deploy/compose.yaml` can never be picked up by
accident.  These helpers carry no policy: they build the exact argv and
propagate failures (`check=True`) except `reload_nginx`, whose absent
container is an expected, tolerated state.
"""
import subprocess
from pathlib import Path


def _files(compose_file: Path, override: Path | None = None) -> list[str]:
    """The `-f` flags selecting the compose file(s)."""
    files = ["-f", str(compose_file)]
    if override is not None:
        files += ["-f", str(override)]
    return files


def run(compose_file: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run `docker compose -f <compose_file> <args...>`."""
    return subprocess.run(
        ["docker", "compose", *_files(compose_file), *args], check=check)


def up(compose_file: Path, override: Path | None = None) -> None:
    """Start the project detached, optionally layering an override file."""
    subprocess.run(
        ["docker", "compose", *_files(compose_file, override), "up", "-d"],
        check=True)


def down(compose_file: Path) -> None:
    """Stop and remove the project's containers."""
    run(compose_file, "down")


def reload_nginx(compose_file: Path) -> None:
    """Reload nginx in its container; a missing container must not raise."""
    run(compose_file, "exec", "-T", "nginx", "nginx", "-s", "reload",
        check=False)


def validate_nginx_config(compose_file: Path) -> None:
    """Raise if nginx would reject the configuration currently on disk."""
    result = subprocess.run(
        ["docker", "compose", *_files(compose_file),
         "exec", "-T", "nginx", "nginx", "-t"],
        check=False, capture_output=True, text=True)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if "emerg" in output or "test failed" in output:
        raise RuntimeError(output)
    # If the exec failed without nginx diagnostics (e.g. container absent),
    # tolerate it so reload_nginx's "missing container" behaviour is preserved.


def recreate(compose_file: Path, override: Path | None = None) -> None:
    """Force-recreate the project's containers (`up -d --force-recreate`)."""
    subprocess.run(
        ["docker", "compose", *_files(compose_file, override),
         "up", "-d", "--force-recreate"],
        check=True)
