#!/usr/bin/env bash
# Run this on the Linux/BOSS presentation machine before the final.
# It does not edit the SANCHAY repository, access a live endpoint, or upload data.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: bash SSM_LINUX_PREFLIGHT.sh /path/to/sanchay" >&2
  exit 2
fi

REPOSITORY_ROOT="$(cd "$1" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
EXPECTED_COMMIT="${SANCHAY_EXPECTED_COMMIT:-}"
export PYTHONDONTWRITEBYTECODE=1

# Set SANCHAY_EXPECTED_COMMIT only after the team has verified the exact
# Stage 1 repository and commit through the portal or written organizer advice.

if [ "$(uname -s)" != "Linux" ]; then
  echo "Refusing final preflight: run this from a Linux/BOSS environment, not $(uname -s)." >&2
  exit 2
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 2
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
  echo "SANCHAY requires Python 3.9 or later." >&2
  exit 2
fi

if [ ! -f "$REPOSITORY_ROOT/pyproject.toml" ] || [ ! -d "$REPOSITORY_ROOT/tests" ]; then
  echo "Not a SANCHAY repository: $REPOSITORY_ROOT" >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1 || ! git -C "$REPOSITORY_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Refusing final preflight: expected a Git checkout at $REPOSITORY_ROOT." >&2
  exit 2
fi

# A Windows checkout rehearsed through WSL can differ only by CRLF conversion.
# Normalising that representation does not hide content changes; staged or
# substantive tracked changes still stop the run.
if ! git -c core.autocrlf=true -C "$REPOSITORY_ROOT" diff --quiet || ! git -c core.autocrlf=true -C "$REPOSITORY_ROOT" diff --cached --quiet; then
  echo "Refusing final preflight: SANCHAY has tracked source changes. Rehearse the selected frozen checkout." >&2
  exit 2
fi

SOURCE_COMMIT="$(git -C "$REPOSITORY_ROOT" rev-parse HEAD)"
if [ -n "$EXPECTED_COMMIT" ]; then
  if ! PINNED_COMMIT="$(git -C "$REPOSITORY_ROOT" rev-parse --verify "${EXPECTED_COMMIT}^{commit}" 2>/dev/null)"; then
    echo "Refusing final preflight: SANCHAY_EXPECTED_COMMIT is not available in this checkout." >&2
    exit 2
  fi
  if [ "$SOURCE_COMMIT" != "$PINNED_COMMIT" ]; then
    echo "Refusing final preflight: HEAD does not match SANCHAY_EXPECTED_COMMIT." >&2
    exit 2
  fi
  COMMIT_STATE="matches the supplied commit pin"
else
  COMMIT_STATE="no commit pin supplied"
fi

cd "$REPOSITORY_ROOT"

echo "Linux platform: $(. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME:-Linux}")"
echo "Python platform: $($PYTHON_BIN --version 2>&1)"
echo "Source commit: ${SOURCE_COMMIT:0:12} (no tracked local changes; ${COMMIT_STATE})"

echo "[1/3] Unit and integration suite"
"$PYTHON_BIN" -m unittest discover tests

echo "[2/3] Disposable final-round safety rehearsal"
"$PYTHON_BIN" -m sanchay.demo --prove

echo "[3/3] Synthetic capacity-risk gate rehearsal"
"$PYTHON_BIN" -m sanchay.demo --risk-prove

echo "PASS - Linux preflight completed. Use the live-demo commands in FINAL_ROUND_RUNBOOK.md next."
