#!/bin/bash
# Start the webcam head-tracking sidecar for ProjectRetro.
# Finds a Python with opencv-python + numpy: a local venv, the sibling pokewarp
# venv, or system python3. Grant camera access to your terminal when asked.
cd "$(dirname "$0")"
PY=""
for CAND in "./venv/bin/python" "../../venv/bin/python" \
            "/Users/jbo/Projects/pokewarp/venv/bin/python" "$(command -v python3)"; do
  if [ -x "$CAND" ] && "$CAND" -c "import cv2, numpy" >/dev/null 2>&1; then PY="$CAND"; break; fi
done
if [ -z "$PY" ]; then
  echo "No Python with opencv-python + numpy found. Set one up with:"
  echo "  python3 -m venv headtracking/venv && headtracking/venv/bin/pip install -r headtracking/requirements.txt"
  exit 1
fi
exec "$PY" headtrack_server.py "$@" \
  2> >(grep -v -E "objc\[|SDL2 binaries|This may cause|One of the duplicates|setPreferableTarget|Targets are not supported" >&2)
