#!/usr/bin/env bash
#
# DriftGuard controlled test domain — one-command setup.
#
# Pulls the images, builds the two front-end bundles, starts the domain and
# verifies it. Idempotent: re-run it any time to repair or refresh the
# environment. Safe to run before a demonstration.
#
#   ./bootstrap.sh          set up and verify
#   ./bootstrap.sh --up     set up, verify, and leave the domain running
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m    warning: %s\033[0m\n' "$*"; }
die()  { printf '\033[31m    error: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- prerequisites
say "Checking prerequisites"
command -v docker >/dev/null 2>&1 || die "docker is not installed"
docker compose version >/dev/null 2>&1 || die "docker compose v2 is not available"
docker info >/dev/null 2>&1 || die "the docker daemon is not reachable"
command -v python3 >/dev/null 2>&1 || die "python3 is not installed"
python3 - <<'EOF' || exit 1
import sys
if sys.version_info < (3, 12):
    sys.exit("python 3.12+ is required")
EOF
printf '    docker %s | python %s\n' "$(docker --version | cut -d' ' -f3)" \
       "$(python3 -c 'import platform; print(platform.python_version())')"

# The e-commerce application directory has a name that is easy to mistype by one
# letter, so it is located by its contents rather than by being spelled out.
demo_app() {
    local d
    for d in "$REPO_ROOT"/demo*ommerce; do
        [ -d "$d/frontend" ] && [ -d "$d/backend" ] && { printf '%s' "$d"; return 0; }
    done
    return 1
}
DEMO_APP="$(demo_app)" || die "could not locate the e-commerce application directory"

# ---------------------------------------------------------------------- images
say "Pulling the container images"
for image in nginx:1.27-alpine bkimminich/juice-shop:latest erev0s/vampi:latest python:3.12-slim; do
    printf '    %s\n' "$image"
    docker pull "$image" >/dev/null || warn "could not pull $image — the build may fail without it"
done

# ------------------------------------------------------------ front-end bundles
say "Building the front-end bundles"
build_bundle() {
    local dir="$1"
    command -v npm >/dev/null 2>&1 || die "npm is not installed (needed to build $dir)"
    # `npm ci` always reinstalls from the lockfile, which is deterministic and
    # picks up platform-specific optional dependencies (a leftover node_modules
    # can be missing them and break the build in confusing ways).
    (cd "$dir" && npm ci --no-audit --no-fund >/dev/null)
    (cd "$dir" && npm run build >/dev/null)
    [ -f "$dir/dist/index.html" ] || die "the build did not produce $dir/dist/index.html"
    printf '    %s\n' "${dir#$REPO_ROOT/}"
}
build_bundle "$DEMO_APP/frontend"
build_bundle "$REPO_ROOT/civic-services-portal"

# ------------------------------------------------------------------- start up
say "Starting the domain (this can take a couple of minutes)"
python3 domain.py up

say "Verifying every target"
if python3 domain.py verify; then
    printf '\n\033[32m    the domain is up and every probe agrees with the recorded state\033[0m\n'
else
    die "verification failed — see the mismatches above"
fi

cat <<'NEXT'

    Next steps:

      python3 domain.py status                 the five targets and their scenarios
      python3 domain.py on <target> <scenario> switch a drift on
      python3 domain.py off <target> <scenario> switch it back off
      python3 domain.py truth                  the ground-truth classification matrix
      python3 sequence.py                      the full nine-scan sequence

    The operator guide is in docs/domain.md.
NEXT
