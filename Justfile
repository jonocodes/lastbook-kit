# lastbook-kit. Run `nix develop` (or `direnv allow`) first on NixOS.

default:
    @just --list

# Install the Python environment
sync:
    uv sync

# All tests. The Small-library ones skip unless Small is in the data home
test *args:
    uv run pytest {{args}}

# Only the fast tests
test-fast *args:
    uv run pytest -m "not small" {{args}}

# Serve a data folder (default: the Small library in the data home)
serve *args:
    uv run lbx serve {{args}}

# Get a library into the data home (small, medium or all)
fetch pack="small" *args:
    uv run lbx fetch {{pack}} {{args}}

# Build the Nix package
nix-build:
    nix build .#lbx
