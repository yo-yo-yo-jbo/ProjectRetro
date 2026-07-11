# Head-tracked camera for ProjectRetro

Adds webcam **head-coupled perspective** to ProjectRetro: move your head and the
in-game camera eye moves with it (focus stays on the player), so you can look
around the 3D world. Because ProjectRetro is a real 3D engine, this is genuine
head tracking — not a 2D skew.

## How it works

A tiny **Python sidecar** does the vision (reusing the pokewarp OpenCV YuNet
tracker) and streams head position to the game over localhost UDP; the game
reads it and offsets the camera. No camera/vision dependency was added to the
C++/CMake build.

```
webcam ─► headtrack_server.py (YuNet) ─► UDP "hx hy hz" :45123 ─► HeadTrackingSystem
                                                                        │ (singleton)
CameraControlSystem (follows player) ─► RenderingSystem: eye += head*scale ─► lookAtLH
```

New/changed files:

| File | |
| --- | --- |
| `source/game/rendering/components/HeadTrackingSingletonComponent.h` | head position + socket + tuning scales |
| `source/game/rendering/systems/HeadTrackingSystem.{h,cpp}` | binds UDP socket, drains packets, smooths |
| `source/game/rendering/systems/RenderingSystem.cpp` | offsets the camera eye before `lookAtLH` |
| `source/game/App.cpp` | registers `HeadTrackingSystem` before rendering |
| `headtracking/headtrack_server.py` | webcam → UDP sidecar |
| build fixes (`CMakeLists.txt`, `build_utilities/*`, `modern_prefix.h`) | make the 2019 project build on modern macOS / CMake 4 |
| crash fix (`resources/MeshUtils.cpp`, `resources/MeshLoader.cpp`) | injected UV pairs are joined with `\|` instead of `-` so a negative coordinate's minus sign no longer creates an empty token that crashed `std::stof` on encounter |

The effect is **optional and safe**: if the sidecar isn't running, the socket
just receives nothing and the camera behaves normally.

## Build

Either the documented Xcode flow (`./make_project.sh` → open the Xcode project →
Run), or the command line:

```bash
brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf   # once
./build_local.sh
```

## Run

Two terminals:

```bash
# 1) the game
./run_game.sh

# 2) the head-tracking sidecar (grant camera access to your terminal when asked)
./headtracking/run_headtracking.sh
```

**See your face detection:** add `--preview` for a mirrored webcam window with
the detected face box, your neutral pose (yellow marker), and the live head
values being sent:

```bash
./headtracking/run_headtracking.sh --preview
```

Sit centered and facing the camera when you start the sidecar — your first
detected pose becomes "neutral". Then lean around.

## Tuning

Effective eye travel = `head × gain × scale`.

- **Sensitivity** (no rebuild): `--gain` on the sidecar (default `2.5`; your head
  rarely reaches the edges of frame, so this amplifies small leans). Try
  `--gain 3.5` for more, `--gain 1.5` for less.
- **Strength** (rebuild): `HEAD_LOOK_SCALE_X/Y/Z` in
  `HeadTrackingSingletonComponent.h` (world units per unit of head).
- **Smoothing**: `--ema` (higher = snappier, lower = smoother).
- **Reversed?** run the sidecar with `--no-mirror`.
- **See detection**: `--preview` (mirrored webcam + face box + values).
- **Disable** without stopping anything: set `mEnabled = false` (or just don't
  run the sidecar).

## Notes / limits
- macOS only for the sidecar's default camera path (uses the pokewarp venv:
  `opencv-python` + `numpy`).
- The CLI `run_game.sh` runs from a nested dir so the game's `../../res/` path
  resolves; the Xcode scheme handles this itself.
- Current mapping is "look-around" (eye orbits, focus fixed). A true off-axis
  window frustum is a possible upgrade.
