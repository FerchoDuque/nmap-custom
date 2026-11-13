#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

step() {
  echo "==> $1"
}

step "Backend tests (api + core)"
(
  cd "$ROOT/backend"
  export PYTHONPATH=.
  export DATABASE_URL="sqlite:///:memory:"
  python -m pytest tests/api tests/core -q
)

step "Frontend lint"
(
  cd "$ROOT/frontend"
  npm run lint
)

step "Frontend typecheck"
(
  cd "$ROOT/frontend"
  npm run typecheck
)

step "Frontend tests"
(
  cd "$ROOT/frontend"
  npm run test:run
)

if [ "$SKIP_BUILD" -eq 0 ]; then
  step "Frontend build"
  (
    cd "$ROOT/frontend"
    npm run build
  )
fi

echo "All checks passed."
