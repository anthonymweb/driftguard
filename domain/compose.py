"""Thin wrappers around the `docker compose` CLI used by the target modules.

Every helper pins the project via `-f <project_dir>/compose.yaml` so the
invoked project never depends on the current working directory (the lab's
`demcommerce/deploy/` and `civic-services-portal/deploy/` would otherwise
both derive the project name `deploy`).  These helpers carry no policy:
they build the exact argv and propagate failures (`check=True`) except
`reload_nginx`, whose absent container is an expected, tolerated state.
"""
import subprocess
from pathlib import Path


def _files(project_dir: Path, override: Path | None = None) -> list[str]:
    """The `-f` flags selecting the project's compose file(s)."""
    files = ["-f", str(Path(project_dir) / "compose.yaml")]
    if override is not None:
        files += ["-f", str(override)]
    return files


def run(project_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run `docker compose -f <project_dir>/compose.yaml <args...>`."""
    return subprocess.run(
        ["docker", "compose", *_files(project_dir), *args], check=check)


def up(project_dir: Path, override: Path | None = None) -> None:
    """Start the project detached, optionally layering an override file."""
    subprocess.run(
        ["docker", "compose", *_files(project_dir, override), "up", "-d"],
        check=True)


def down(project_dir: Path) -> None:
    """Stop and remove the project's containers."""
    run(project_dir, "down")


def reload_nginx(project_dir: Path) -> None:
    """Reload nginx in its container; a missing container must not raise."""
    run(project_dir, "exec", "-T", "nginx", "nginx", "-s", "reload",
        check=False)


def recreate(project_dir: Path, override: Path | None = None) -> None:
    """Force-recreate the project's containers (`up -d --force-recreate`)."""
    subprocess.run(
        ["docker", "compose", *_files(project_dir, override),
         "up", "-d", "--force-recreate"],
        check=True)
