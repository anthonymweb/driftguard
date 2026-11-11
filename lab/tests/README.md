# Tests

- **Tests must never write to the repository's live state or config paths.** The registered target modules keep their live state and rendered nginx config at fixed, gitignored paths inside the worktree; a test that reaches them can silently corrupt the authoritative ground truth of a research run.
- **Do not run `git clean -fdx` in this worktree.** It destroys live domain artifacts (built front-end bundles, state files, rendered configs).
- When exercising a target module, redirect `STATE_PATH`/`CONFIG_PATH` to a temporary directory and mock external side effects (compose, certs, waits, subprocess, network). `tests/test_live_path_guard.py` asserts the live paths stay untouched.
