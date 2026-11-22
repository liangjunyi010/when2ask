#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  uv python install 3.11
  if [ ! -d .venv ]; then uv venv --python 3.11 --seed .venv; fi
  installer=(uv pip install --python .venv/bin/python)
else
  if [ ! -d .venv ]; then python3.11 -m venv .venv; fi
  installer=(.venv/bin/python -m pip install)
fi
"${installer[@]}" 'pip==26.2.2' 'setuptools==84.2.1' 'wheel==0.48.0' 'numpy==2.4.6'
if [ "$(uname -s)" = Darwin ]; then
  # A self-referential macro avoids bundled legacy zlib replacing POSIX fdopen.
  export CFLAGS="${CFLAGS:-} -Dfdopen=fdopen"
  if [ -n "${WHEN2ASK_SDKROOT:-}" ]; then
    export SDKROOT="$WHEN2ASK_SDKROOT"
  elif [ -d /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk ]; then
    export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
  fi
fi
"${installer[@]}" --no-build-isolation 'pybullet==3.2.7'
"${installer[@]}" --no-build-isolation --editable '.[test,figures]'
.venv/bin/python script/benchmark.py doctor
