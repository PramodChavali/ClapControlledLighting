import time
import cv2
import mediapipe as mp
import clapDetector
import lifxlan
from picamera2 import Picamera2
from threading import Thread
from queue import Queue
import collections

print("System starting...")

# ---- LIFX SETUP ----
bulb1 = lifxlan.Light("MAC ADDRESS", "IP")
bulb2 = lifxlan.Light("MAC ADDRESS", "IP")
lights = [bulb1, bulb2]
brightnessMultiplier = 318.45

for light in lights:
    print("Found light:", light.get_label())

# LIFX command queue
lifx_queue = Queue(maxsize=10)

def lifx_worker():
    while True:
        try:
            command = lifx_queue.get()
            if command[0] == "brightness":
                for light in lights:
                    light.set_brightness(command[1])
            elif command[0] == "power":
                _, isOn, fullPower = command
                for light in lights:
                    light.set_power(isOn)
                    if fullPower:
                        light.set_brightness(65535)
            lifx_queue.task_done()
        except Exception as e:
            print("LIFX error:", e)

def ChangeBrightness(heightDiff):
    print(f"ChangeBrightness called with heightDiff: {heightDiff}")
    if heightDiff > 60:
        power = int(heightDiff * brightnessMultiplier)
        power = min(power, 65535)
        print(f"Setting brightness to: {power}")
        lifx_queue.put(("brightness", power))
    else:
        print(f"heightDiff {heightDiff} <= 60, not changing brightness")

def ToggleLights(isOn, fullPower=False):
    lifx_queue.put(("power", isOn, fullPower))

# ---- MEDIAPIPE HAND DETECTION ----
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.6,  # Slightly lower for longer distances
    min_tracking_confidence=0.6,  # Slightly lower for longer distances
    model_complexity=1
)

# ---- CAMERA SETUP ----
picam = Picamera2()
camera_config = picam.create_preview_configuration(
    main={"size": (1920, 1080), "format": "RGB888"}  # higher resolution for better long-distance detection
)
picam.configure(camera_config)
picam.start()
print("Camera started successfully")

frame_queue = Queue(maxsize=1)
latest_frame = None

# smoothing buffers
alpha = 0.3
smoothed_left = None
smoothed_right = None
process_every_n_frames = 2
frame_count = 0

# ---- CAMERA CAPTURE THREAD ----
def camera_capture():
    global latest_frame
    while True:
        frame = picam.capture_array()  # RGB
        latest_frame = frame
        if frame_queue.full():
            frame_queue.get_nowait()
        frame_queue.put(frame)
        time.sleep(0.005)

# ---- HAND DETECTION THREAD ----
def hand_detection():
    global latest_frame, smoothed_left, smoothed_right, frame_count
    while True:
        if frame_queue.empty():
            time.sleep(0.005)
            continue

        frame_count += 1
        frame = frame_queue.get()
        h, w, _ = frame.shape

        # skip frames to reduce CPU
        if frame_count % process_every_n_frames != 0:
            latest_frame = frame
            continue

        # Convert RGB to BGR for Mediapipe (this is what worked before)
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        results = hands_detector.process(bgr_frame)

        print(f"Frame {frame_count}: Hands detected: {len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0}")

        # draw landmarks
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)  # Draw on RGB frame

        # compute hand centers
        hand_centers = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                middle_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                center_x = int((wrist.x + middle_mcp.x)/2 * w)
                center_y = int((wrist.y + middle_mcp.y)/2 * h)
                hand_centers.append((center_x, center_y))

        if len(hand_centers) >= 2:
            leftX, leftY = hand_centers[0]
            rightX, rightY = hand_centers[1]

            print(f"Hand centers: Left({leftX},{leftY}), Right({rightX},{rightY})")

            if smoothed_left is None:
                smoothed_left = (leftX, leftY)
                smoothed_right = (rightX, rightY)
            else:
                smoothed_left = (int(alpha*leftX + (1-alpha)*smoothed_left[0]),
                                 int(alpha*leftY + (1-alpha)*smoothed_left[1]))
                smoothed_right = (int(alpha*rightX + (1-alpha)*smoothed_right[0]),
                                  int(alpha*rightY + (1-alpha)*smoothed_right[1]))

            leftX, leftY = smoothed_left
            rightX, rightY = smoothed_right

            print(f"Smoothed centers: Left({leftX},{leftY}), Right({rightX},{rightY})")

            leeway = 100  # Further increased leeway for longer distance gestures
            if abs(rightX - leftX) < leeway:
                heightDiff = abs(rightY - leftY)
                print(f"Hands close enough, heightDiff: {heightDiff}")
                ChangeBrightness(heightDiff)
            else:
                print(f"Hands too far apart: {abs(rightX - leftX)} > {leeway}")

        latest_frame = frame

# ---- CLAP DETECTION ----
clapDetector.printDeviceInfo()
thresholdBias = 6000
lowcut = 200
highcut = 3200
clapListener = clapDetector.ClapDetector(
    inputDevice=1,
    rate=44100,
    bufferLength=4096,
    logLevel=10
)
clapListener.initAudio()
clap_queue = Queue(maxsize=20)
lightsOn = True if bulb1.get_power() else False

def audio_reader():
    while True:
        audioData = clapListener.getAudio()
        if clap_queue.full():
            clap_queue.get_nowait()
        clap_queue.put(audioData)

def clap_processor():
    global lightsOn
    while True:
        if not clap_queue.empty():
            audioData = clap_queue.get()
            result = clapListener.run(
                thresholdBias=thresholdBias,
                lowcut=lowcut,
                highcut=highcut,
                audioData=audioData
            )
            if len(result) in [2,3]:
                lightsOn = not lightsOn
                ToggleLights(lightsOn, fullPower=(len(result)==3))
                print("Lights toggled via clap:", lightsOn)
        time.sleep(0.01)


# ---- START ALL THREADS ----
if __name__ == "__main__":
    Thread(target=lifx_worker, daemon=True).start()
    Thread(target=camera_capture, daemon=True).start()
    Thread(target=hand_detection, daemon=True).start()
    Thread(target=audio_reader, daemon=True).start()
    Thread(target=clap_processor, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        clapListener.stop()
        hands_detector.close()
        picam.stop()
