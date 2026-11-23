# lastbook-kit. Run `nix develop` (or `direnv allow`) first on NixOS.

# Where libraries live for development and tests
export LASTBOOK_KIT_DATA := env_var_or_default("LASTBOOK_KIT_DATA", env_var("HOME") / ".cache/lastbook-kit")

default:
    @just --list

# Install the Python environment
sync:
    uv sync

# Fast tests, plus the Small-library tests if Small is in LASTBOOK_KIT_DATA
test *args:
    uv run pytest {{args}}

# Only the fast tests
test-fast *args:
    uv run pytest -m "not small" {{args}}

# Serve a data folder (default: the Small library in LASTBOOK_KIT_DATA)
serve data=(LASTBOOK_KIT_DATA / "small/LastbookData") *args:
    uv run lbx serve {{data}} {{args}}

# Build the Nix package
nix-build:
    nix build .#lbx
