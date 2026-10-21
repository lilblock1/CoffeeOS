#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
status=0
for f in scripts/*.sh live-build/auto/config live-build/config/hooks/live/*.hook.chroot live-build/config/hooks/live/*.hook.binary; do
  [[ -f "$f" ]] || continue
  bash -n "$f" || status=1
done
for f in live-build/config/includes.chroot/usr/local/bin/* live-build/config/includes.chroot/usr/local/sbin/*; do
  [[ -f "$f" ]] || continue
  case "$(head -n 1 "$f")" in *python3*) python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f" || status=1;; *) bash -n "$f" || status=1;; esac
done
for f in kernel/tools/*.py; do
  python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f" || status=1
done
python3 -m unittest discover -s tests -v || status=1
exit "$status"
