#!/usr/bin/env python3
"""Webcam head-tracking sidecar for ProjectRetro.

Tracks your head with the Mac webcam (OpenCV YuNet face detector) and streams a
normalized, smoothed head position to the running game over localhost UDP. The
game's HeadTrackingSystem reads it and offsets the camera eye, so moving your
head lets you look around the 3D world (head-coupled perspective).

Datagram format: ASCII "hx hy hz" where
  hx  head left/right, right = +   (mirrored so it feels natural)
  hy  head up/down,    up    = +
  hz  closeness (lean in = +)
all roughly in [-1, 1]. The first detected face defines the neutral pose.

Run it alongside the game:
    ./run_headtracking.sh          # or: python headtrack_server.py
Press Ctrl-C to stop. If the webcam can't be opened, grant camera access to
your terminal in System Settings > Privacy & Security > Camera.
"""
import argparse
import os
import socket
import sys
import time

import cv2
import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "face_detection_yunet.onnx")
DEFAULT_PORT = 45123


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--ema", type=float, default=0.4, help="smoothing 0..1")
    ap.add_argument("--gain", type=float, default=2.5,
                    help="amplify head motion (bigger = more look-around)")
    ap.add_argument("--no-mirror", action="store_true",
                    help="don't mirror X (use if look-around feels reversed)")
    ap.add_argument("--preview", action="store_true",
                    help="show the webcam + face detection in a window")
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    if not cap.isOpened():
        sys.exit("[headtrack] Could not open webcam. Grant camera access to your "
                 "terminal in System Settings > Privacy & Security > Camera.")
    detector = cv2.FaceDetectorYN.create(MODEL, "", (320, 240), 0.6, 0.3, 5000)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", args.port)
    mirror = -1.0 if not args.no_mirror else 1.0

    center = None          # neutral (nx, ny), set from the first face
    base_area = None
    sx = sy = sz = 0.0
    print(f"[headtrack] streaming head position to udp://127.0.0.1:{args.port} "
          f"(Ctrl-C to stop)")
    last_print = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.02)
                continue
            h, w = frame.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            face_box = None
            if faces is not None and len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])[:4]
                face_box = (fx, fy, fw, fh)
                nx = ((fx + fw / 2.0) / w - 0.5) * 2.0
                ny = ((fy + fh / 2.0) / h - 0.5) * 2.0
                area = fw * fh
                if center is None:
                    center, base_area = (nx, ny), area
                dx = (nx - center[0]) * mirror
                dy = -(ny - center[1])                 # up = +
                dz = float(np.clip(area / base_area - 1.0, -1.0, 1.0))
                sx += args.ema * (dx - sx)
                sy += args.ema * (dy - sy)
                sz += args.ema * (dz - sz)

            # Amplify small real head motion, then clamp so the eye offset in the
            # game stays bounded.
            gx = float(np.clip(sx * args.gain, -1.5, 1.5))
            gy = float(np.clip(sy * args.gain, -1.5, 1.5))
            gz = float(np.clip(sz * args.gain, -1.5, 1.5))
            sock.sendto(f"{gx:.4f} {gy:.4f} {gz:.4f}".encode(), dest)

            now = time.time()
            if now - last_print > 1.0:
                state = "tracking" if face_box is not None else "no face "
                print(f"\r[headtrack] {state}  sent hx={gx:+.2f} hy={gy:+.2f} "
                      f"hz={gz:+.2f}   ", end="", flush=True)
                last_print = now

            if args.preview:
                disp = cv2.flip(frame, 1)              # mirror, like a mirror
                if face_box is not None:
                    fx, fy, fw, fh = face_box
                    mx0, mx1 = int(w - (fx + fw)), int(w - fx)
                    cv2.rectangle(disp, (mx0, int(fy)), (mx1, int(fy + fh)),
                                  (0, 230, 0), 2)
                    ccx = int(w - (fx + fw / 2.0))
                    ccy = int(fy + fh / 2.0)
                    cv2.drawMarker(disp, (ccx, ccy), (0, 230, 0),
                                   cv2.MARKER_CROSS, 16, 2)
                if center is not None:
                    ncx = int((-center[0] / 2.0 + 0.5) * w)  # neutral (mirrored)
                    ncy = int((center[1] / 2.0 + 0.5) * h)
                    cv2.drawMarker(disp, (ncx, ncy), (200, 200, 0),
                                   cv2.MARKER_TILTED_CROSS, 14, 1)
                for i, txt in enumerate([
                        f"hx {gx:+.2f}  hy {gy:+.2f}  hz {gz:+.2f}",
                        f"gain {args.gain:.1f}   {'TRACKING' if face_box is not None else 'NO FACE'}"]):
                    y = 22 + i * 22
                    cv2.putText(disp, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 0, 0), 3, cv2.LINE_AA)
                    cv2.putText(disp, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (80, 255, 80), 1, cv2.LINE_AA)
                cv2.imshow("ProjectRetro head tracking (q quits)", disp)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                time.sleep(1 / 60.0)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n[headtrack] stopped")


if __name__ == "__main__":
    main()
