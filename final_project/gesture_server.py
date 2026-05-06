"""
LightControl — Python Gesture Recognition Server
=================================================
Based on: Finger Count using MediaPipe (reference)

INSTALL (run once):
    pip install mediapipe==0.10.11 opencv-python requests

USAGE:
    1. Upload esp32cam_stream.ino  → note the CAM IP
    2. Upload esp32_controller.ino → note the controller IP
    3. Paste both IPs below
    4. Run: python gesture_server.py

GESTURE MAP:
    Fist          (0 fingers)           → OFF
    Open Hand     (all 5 fingers)       → WHITE
    One Finger    (index only)          → RED
    Peace Sign    (index + middle)      → GREEN
    Three Fingers (index+middle+ring)   → BLUE
    Call Sign     (thumb + pinky only)  → RAINBOW
"""

import cv2
import mediapipe as mp
import requests
import time

# ══════════════════════════════════════════════════════════════
# CONFIG — UPDATE THESE TWO LINES WITH YOUR ACTUAL IPs
# ══════════════════════════════════════════════════════════════

ESP32_CAM_URL = "http://192.168.100.24/stream"  # ← from esp32cam Serial Monitor
ESP32_CTRL_IP = "http://192.168.100.25"         # ← from esp32_controller Serial Monitor

# How long (seconds) to hold a gesture before it triggers
GESTURE_HOLD_TIME = 0.8

# ══════════════════════════════════════════════════════════════
# MEDIAPIPE SETUP
# ══════════════════════════════════════════════════════════════

mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Named landmark constants (cleaner than raw index numbers)
FINGER_TIPS = [
    mp_hands.HandLandmark.INDEX_FINGER_TIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
    mp_hands.HandLandmark.RING_FINGER_TIP,
    mp_hands.HandLandmark.PINKY_TIP,
]
FINGER_PIPS = [
    mp_hands.HandLandmark.INDEX_FINGER_PIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
    mp_hands.HandLandmark.RING_FINGER_PIP,
    mp_hands.HandLandmark.PINKY_PIP,
]

# ══════════════════════════════════════════════════════════════
# FINGER DETECTION (from reference)
# ══════════════════════════════════════════════════════════════

def count_fingers(hand_landmarks, handedness):
    """
    Returns total number of fingers up (0-5).
    Uses handedness to correctly detect thumb direction.
    handedness: 'Left' or 'Right' (MediaPipe label)
    """
    lm         = hand_landmarks.landmark
    fingers_up = 0

    # Thumb — uses x-axis (horizontal), direction depends on hand
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip  = lm[mp_hands.HandLandmark.THUMB_IP]
    if handedness == "Right":
        if thumb_tip.x < thumb_ip.x:
            fingers_up += 1
    else:  # Left hand
        if thumb_tip.x > thumb_ip.x:
            fingers_up += 1

    # Other 4 fingers — uses y-axis (tip above pip = finger is up)
    for tip_id, pip_id in zip(FINGER_TIPS, FINGER_PIPS):
        if lm[tip_id].y < lm[pip_id].y:
            fingers_up += 1

    return fingers_up


def get_finger_states(hand_landmarks, handedness):
    """
    Returns dict of each finger's up/down state.
    Used for specific gesture matching (e.g. call sign).
    """
    lm = hand_landmarks.landmark

    # Thumb
    thumb_tip = lm[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip  = lm[mp_hands.HandLandmark.THUMB_IP]
    if handedness == "Right":
        thumb_up = thumb_tip.x < thumb_ip.x
    else:
        thumb_up = thumb_tip.x > thumb_ip.x

    # Four fingers
    index_up  = lm[mp_hands.HandLandmark.INDEX_FINGER_TIP].y  < lm[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_up = lm[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < lm[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_up   = lm[mp_hands.HandLandmark.RING_FINGER_TIP].y   < lm[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_up  = lm[mp_hands.HandLandmark.PINKY_TIP].y         < lm[mp_hands.HandLandmark.PINKY_PIP].y

    return {
        "thumb":  thumb_up,
        "index":  index_up,
        "middle": middle_up,
        "ring":   ring_up,
        "pinky":  pinky_up,
    }

# ══════════════════════════════════════════════════════════════
# GESTURE CLASSIFICATION
# ══════════════════════════════════════════════════════════════

def classify_gesture(hand_landmarks, handedness):
    """
    Maps finger states to one of 6 LightControl modes.
    Returns (gesture_name, mode_string) or ("Unknown", None)
    """
    total = count_fingers(hand_landmarks, handedness)
    f     = get_finger_states(hand_landmarks, handedness)

    # Class 0 — Fist: all fingers down
    if total == 0:
        return "Fist", "OFF"

    # Class 1 — Open Hand: all 5 up
    if total == 5:
        return "Open Hand", "WHITE"

    # Class 5 — Call Sign: thumb + pinky only
    # (checked before count-based classes to avoid misclassification)
    if f["thumb"] and f["pinky"] and not f["index"] and not f["middle"] and not f["ring"]:
        return "Call Sign", "RAINBOW"

    # Class 2 — One Finger: index only
    if f["index"] and not f["thumb"] and not f["middle"] and not f["ring"] and not f["pinky"]:
        return "One Finger", "RED"

    # Class 3 — Peace Sign: index + middle
    if f["index"] and f["middle"] and not f["thumb"] and not f["ring"] and not f["pinky"]:
        return "Peace Sign", "GREEN"

    # Class 4 — Three Fingers: index + middle + ring
    if f["index"] and f["middle"] and f["ring"] and not f["thumb"] and not f["pinky"]:
        return "Three Fingers", "BLUE"

    return "Unknown", None

# ══════════════════════════════════════════════════════════════
# SEND COMMAND TO ESP32 CONTROLLER
# ══════════════════════════════════════════════════════════════

def send_mode(mode: str):
    """Sends HTTP GET to ESP32 controller with the new mode."""
    try:
        url  = f"{ESP32_CTRL_IP}/gesture?mode={mode}"
        resp = requests.get(url, timeout=2)
        print(f"  [-> ESP32] mode={mode}  |  response: {resp.text.strip()}")
    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Cannot reach ESP32 at {ESP32_CTRL_IP} — check WiFi/IP")
    except requests.exceptions.Timeout:
        print(f"  [ERROR] ESP32 did not respond in time")

# ══════════════════════════════════════════════════════════════
# HUD COLOR PER MODE
# ══════════════════════════════════════════════════════════════

MODE_COLORS = {
    "OFF":     (80,  80,  80),
    "WHITE":   (220, 220, 220),
    "RED":     (0,   0,   220),
    "GREEN":   (0,   200, 0),
    "BLUE":    (220, 80,  0),
    "RAINBOW": (160, 0,   200),
}

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("  LightControl Gesture Server")
    print("=" * 50)
    print(f"  CAM stream : {ESP32_CAM_URL}")
    print(f"  Controller : {ESP32_CTRL_IP}")
    print(f"  Hold time  : {GESTURE_HOLD_TIME}s")
    print("  Press Q in the window to quit")
    print("=" * 50 + "\n")

    # Open the ESP32-CAM stream
    cap = cv2.VideoCapture(ESP32_CAM_URL)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open stream: {ESP32_CAM_URL}")
        print("  → Check ESP32-CAM is powered and on the same WiFi")
        print("  → Try opening the URL in a browser first")
        return

    print("[OK] Stream opened successfully!\n")

    # Tracking state
    last_sent_mode  = None
    current_gesture = None
    gesture_start   = None

    with mp_hands.Hands(
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Frame read failed — retrying...")
                time.sleep(0.1)
                continue

            # Mirror horizontally (more natural for the user)
            frame  = cv2.flip(frame, 1)
            h, w   = frame.shape[:2]
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            gesture_name = "No Hand"
            mode         = None
            finger_count = 0

            if result.multi_hand_landmarks and result.multi_handedness:
                for hand_lm, hand_info in zip(
                        result.multi_hand_landmarks,
                        result.multi_handedness):

                    # Draw hand skeleton on frame
                    mp_drawing.draw_landmarks(
                        frame, hand_lm, mp_hands.HAND_CONNECTIONS
                    )

                    # Get handedness label and classify
                    label        = hand_info.classification[0].label  # 'Left' or 'Right'
                    finger_count = count_fingers(hand_lm, label)
                    gesture_name, mode = classify_gesture(hand_lm, label)

                    # Gesture hold logic — only send after GESTURE_HOLD_TIME seconds
                    if gesture_name == current_gesture:
                        held = (time.time() - gesture_start) if gesture_start else 0
                        if held >= GESTURE_HOLD_TIME and mode and mode != last_sent_mode:
                            send_mode(mode)
                            last_sent_mode = mode
                    else:
                        # Gesture changed — reset timer
                        current_gesture = gesture_name
                        gesture_start   = time.time()

                    # Finger count label (matching reference style)
                    cv2.putText(
                        frame,
                        f"{label}: {finger_count} fingers",
                        (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.5, (0, 255, 0), 3
                    )

            else:
                # No hand in frame — reset tracking
                current_gesture = None
                gesture_start   = None

            # ── HUD — top bar ──────────────────────────────
            cv2.rectangle(frame, (0, 0), (w, 50), (30, 30, 30), -1)
            cv2.putText(frame, "LightControl",
                        (10, 34), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 255, 255), 2)

            # ── HUD — bottom bar ───────────────────────────
            color = MODE_COLORS.get(last_sent_mode, (180, 180, 180))
            cv2.rectangle(frame, (0, h - 80), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, f"Gesture : {gesture_name}",
                        (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (200, 200, 200), 2)
            cv2.putText(frame, f"Mode    : {last_sent_mode or 'None'}",
                        (10, h - 16), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, color, 2)
            cv2.circle(frame, (w - 30, h - 30), 14, color, -1)

            cv2.imshow("LightControl — Hand Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[INFO] Quit by user.")
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()