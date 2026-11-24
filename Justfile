# lastbook-kit.
#
# On NixOS the PyPI wheels need libraries from the Nix dev shell. Outside it, recipes enter it themselves.
nixos := path_exists("/etc/NIXOS")
in_shell := env("IN_NIX_SHELL", "")
uv := if nixos == "true" { if in_shell == "" { "nix develop --command uv" } else { "uv" } } else { "uv" }

default:
    @just --list

# Install the Python environment
sync:
    {{uv}} sync

# All tests. The Small-library ones skip unless Small is in the data home
test *args:
    {{uv}} run pytest {{args}}

# Only the fast tests
test-fast *args:
    {{uv}} run pytest -m "not small" {{args}}

# Serve a data folder (default: the Small library in the data home)
serve *args:
    {{uv}} run lbx serve {{args}}

# Get a library into the data home (small, medium or all)
fetch pack="small" *args:
    {{uv}} run lbx fetch {{pack}} {{args}}

# Build the Nix package
nix-build:
    nix build .#lbx

# Drive the web interface on the Small library. Screenshots go to artifacts/screenshots/
ui:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{nixos}}" = true ] && [ -z "{{in_shell}}" ]; then exec nix develop --command just ui; fi
    (cd tests/ui && npm ci --silent --no-audit --no-fund)
    state=$(mktemp -d)
    port=$(uv run python -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
    uv run lbx serve --port "$port" --state "$state" --no-index > "$state/serve.log" 2>&1 &
    pid=$!
    trap 'kill $pid 2>/dev/null; rm -rf "$state"' EXIT
    until uv run python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$port/')" 2>/dev/null; do
        kill -0 $pid 2>/dev/null || { cat "$state/serve.log"; exit 1; }
        sleep 0.5
    done
    node tests/ui/screenshots.mjs "http://127.0.0.1:$port" artifacts/screenshots

# Move the upstream pin to a tag and run every test against it, Small included. Commit only if it all passes
bump-upstream tag:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "{{nixos}}" = true ] && [ -z "{{in_shell}}" ]; then exec nix develop --command just bump-upstream "{{tag}}"; fi
    git -C upstream fetch --tags --quiet
    git -C upstream checkout --quiet "{{tag}}"
    rev=$(git -C upstream rev-parse --short=8 HEAD)
    uv run python - "{{tag}}" "$rev" <<'PY'
    import re, sys, pathlib
    p = pathlib.Path('README.md')
    s, n = re.subn(r'pinned to Lastbook `[^`]+` \(`[0-9a-f]+`\)', f'pinned to Lastbook `{sys.argv[1]}` (`{sys.argv[2]}`)', p.read_text())
    assert n == 1, 'README: pin line not found'
    p.write_text(s)
    PY
    LBX_REQUIRE_SMALL=1 uv run pytest -ra
    just ui
    echo
    echo "upstream is at {{tag}} ($rev) and every test passed. Look at artifacts/screenshots/, then:"
    echo "  git add upstream README.md && git commit -m 'Bump upstream Lastbook to {{tag}}'"
