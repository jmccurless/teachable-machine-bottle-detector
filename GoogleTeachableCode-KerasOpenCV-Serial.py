import os
import sys
import time

# Force TensorFlow to use the legacy Keras 2 engine.
# Teachable Machine exports Keras 2 models, which Keras 3 cannot load.
# This must be set before TensorFlow is imported.
os.environ["TF_USE_LEGACY_KERAS"] = "1"

# On macOS, pyarrow (pulled in through pandas) can crash TensorFlow on import
# with "mutex lock failed: Invalid argument". This code does not need pyarrow,
# so block it before TensorFlow loads.
sys.modules["pyarrow"] = None

import cv2
import numpy as np
import serial
import serial.tools.list_ports
from tf_keras.models import load_model

# Find the model and labels next to this script, whatever folder you run it from
HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------
# Serial settings
# ----------------------------------------------------------------------

# The label number in labels.txt that means "a bottle is in view".
# 0 Background, 1 Bottle, 2 Not bottle -> so Bottle is 1.
BOTTLE_LABEL = 1

# Must match the Serial.begin() number in your Arduino sketch
BAUD_RATE = 9600

# Only act on a prediction the model is fairly sure about, so a blurry frame
# does not flip your device back and forth. Lowered from 0.80, because a
# webcam in ordinary room light often lands in the 60s even on a clear bottle.
CONFIDENCE_THRESHOLD = 0.60

# Which port the board is on. None means "find it automatically", which is the
# right answer almost always - the usbmodem number changes between machines and
# sometimes between plug-ins. Set it to a string like "/dev/cu.usbmodem3101"
# only if auto-detection picks the wrong device.
SERIAL_PORT = None

# Resend the current state this often, even when it has not changed.
# This matters: if the board loses power or gets reset it comes back up showing
# "----" and waiting, and without a resend it would sit there forever while
# this script happily believed it had already said "on".
HEARTBEAT_SECONDS = 2.0


def find_board_port():
    """Pick the most likely Arduino port, or return None if nothing looks right."""
    candidates = []
    for port in serial.tools.list_ports.comports():
        # Skip the two fake ports macOS always lists, which are not boards.
        if "Bluetooth" in port.device or "debug-console" in port.device:
            continue
        # A real Arduino reports vendor id 0x2341. Clones use other chips, so
        # fall back to the usual USB-serial device names too.
        is_arduino_vid = port.vid == 0x2341
        looks_like_usb_serial = any(
            name in port.device
            for name in ("usbmodem", "usbserial", "wchusbserial", "SLAB_USBtoUART")
        )
        if is_arduino_vid or looks_like_usb_serial:
            # Genuine boards sort first, so they win when both are plugged in.
            candidates.append((0 if is_arduino_vid else 1, port.device))

    candidates.sort()
    return candidates[0][1] if candidates else None


# Work out which port to use, then open it.
port_name = SERIAL_PORT or find_board_port()

board = None
if port_name is None:
    print("No Arduino-looking serial port found. Is the board plugged in?")
    print("Ports I can see right now:")
    for port in serial.tools.list_ports.comports():
        print(f"  {port.device}  ({port.description})")
else:
    try:
        board = serial.Serial(port_name, BAUD_RATE, timeout=1)
        # Opening the port resets most Arduino boards. Give it time to restart,
        # otherwise the first messages are sent into the void.
        time.sleep(2.5)
        print(f"Connected to {port_name} at {BAUD_RATE} baud.")
    except serial.SerialException as error:
        print(f"Could not open {port_name}: {error}")
        print("Close the Arduino IDE's Serial Monitor, then run this again.")

# Say so loudly rather than letting it look like a camera problem later.
if board is None:
    print("*** RUNNING WITHOUT THE BOARD. The camera and model still work, ***")
    print("*** but nothing will be sent, so the display stays on '----'.   ***")


def send(message):
    """Send one message to the board, followed by a newline."""
    if board is None:
        return
    try:
        board.write((message + "\n").encode())
        board.flush()
    except serial.SerialException as error:
        print(f"Lost the board: {error}")


# Counts how many replies the board has sent us. Stays at 0 if the board is
# not running the sketch, or if the board -> computer half of the link is dead.
acks_received = 0


def read_replies():
    """Print anything the board has said back. Never blocks for long."""
    global acks_received
    if board is None:
        return
    try:
        while board.in_waiting:
            line = board.readline().decode(errors="replace").strip()
            if line:
                acks_received += 1
                print(f"  board: {line}")
    except serial.SerialException as error:
        print(f"Lost the board: {error}")


# ----------------------------------------------------------------------
# Model, labels, and camera
# ----------------------------------------------------------------------

# Load the model directly using legacy Keras
model = load_model(os.path.join(HERE, "keras_model.h5"), compile=False)

# Load the labels. Each line looks like "0 Background", so keep only the name.
with open(os.path.join(HERE, "labels.txt"), "r") as f:
    class_names = [line.strip().split(" ", 1)[1] for line in f if line.strip()]

# Knock the board off "----" straight away. If the display does not change the
# moment this script starts, the problem is the board or the wiring, not the
# model - which saves staring at confidence numbers for no reason.
send("off")
time.sleep(0.3)
read_replies()
if board is not None and acks_received == 0:
    print("*** The board never replied. It is powered and the port opened, but ***")
    print("*** nothing is coming back. Unplug the USB cable, wait 5 seconds,   ***")
    print("*** plug it back in, and run this again.                            ***")

CAMERA_HELP = """
Could not get pictures from the camera.

On macOS the camera almost always "opens" even when permission is refused - it
just hands back empty frames, which looks exactly like a broken camera.

Fix it like this:
  1. System Settings > Privacy & Security > Camera.
  2. Turn ON the switch for whichever app you are running this from:
     "Visual Studio Code" if you use its terminal or Run button,
     "Terminal" if you use the Terminal app, "iTerm" for iTerm.
  3. QUIT THAT APP COMPLETELY (Cmd-Q) and reopen it. macOS only applies a new
     camera permission when the app next starts, so this step is not optional.

Also check that nothing else is using the camera - Zoom, Teams, FaceTime and
Photo Booth all hold it exclusively, and Zoom keeps it even when minimised.
"""

# CAMERA can be 0 or 1 based on default camera of your computer
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    sys.exit(CAMERA_HELP)

# Opening the camera is not the same as it being ready. AVFoundation on macOS
# needs a moment to start the capture session, so the first few reads can come
# back empty on a perfectly good camera. Give it a few seconds before giving up.
print("Waiting for the camera...")
for attempt in range(60):
    ret, frame = camera.read()
    if ret:
        print(f"Camera ready ({frame.shape[1]}x{frame.shape[0]}).")
        break
    time.sleep(0.05)
else:
    camera.release()
    sys.exit(CAMERA_HELP)

print("Click the webcam window, then press Esc or q to quit (or Ctrl+C in the terminal).")

# What we last told the board, and when we last told it.
last_message = None
last_send_time = 0.0

# A single dropped frame is normal and means nothing. Only give up if they keep
# failing, which is what a camera being unplugged or stolen by Zoom looks like.
dropped_frames = 0

while True:
    # Grab the webcamera's image.
    ret, frame = camera.read()
    if not ret:
        dropped_frames += 1
        if dropped_frames >= 30:
            print("Lost the camera - 30 empty frames in a row.")
            print(CAMERA_HELP)
            break
        time.sleep(0.05)
        continue
    dropped_frames = 0

    # Crop the center square, like Teachable Machine does, so the image is not squashed
    h, w = frame.shape[:2]
    size = min(h, w)
    top, left = (h - size) // 2, (w - size) // 2
    frame = frame[top:top + size, left:left + size]

    # Resize the square image to (224-height,224-width) pixels
    frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)

    # OpenCV uses BGR color order, but the model was trained on RGB images
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Make the image a numpy array and reshape it to the model's input shape.
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)

    # Normalize the image array to the range -1 to 1
    image = (image / 127.5) - 1

    # Predict. verbose=0 stops Keras from printing a progress bar every frame.
    prediction = model.predict(image, verbose=0)
    index = int(np.argmax(prediction[0]))
    class_name = class_names[index]
    confidence_score = prediction[0][index]

    # A bottle, and we are sure enough about it, means buzz. Everything else -
    # including Background - means quiet. Sending "off" for Background rather
    # than sending nothing is what stops the display getting stuck on "----".
    is_bottle = index == BOTTLE_LABEL and confidence_score >= CONFIDENCE_THRESHOLD
    message = "on" if is_bottle else "off"

    now = time.time()
    changed = message != last_message
    due = now - last_send_time >= HEARTBEAT_SECONDS

    if changed or due:
        send(message)
        last_message = message
        last_send_time = now

    read_replies()

    # Show every class score, not just the winner. When the board is not
    # buzzing this line tells you why in one glance - either Bottle is losing
    # to another class, or it is winning but below CONFIDENCE_THRESHOLD.
    scores = "  ".join(
        f"{name}: {prediction[0][i] * 100:.0f}%" for i, name in enumerate(class_names)
    )
    arrow = "ON " if is_bottle else "off"
    print(f"[{arrow}] {scores}")

    # Put the same information on the video window, so you can watch the bottle
    # and the numbers at once instead of looking down at the terminal.
    display_frame = cv2.resize(frame, (448, 448), interpolation=cv2.INTER_NEAREST)
    color = (0, 255, 0) if is_bottle else (0, 0, 255)
    cv2.putText(display_frame, f"{class_name} {confidence_score * 100:.0f}%",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(display_frame, f"sending: {last_message}",
                (10, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imshow("Webcam Image", display_frame)

    # Listen to the keyboard for presses. Esc key (27) or q to exit.
    # The webcam window must be selected (clicked) to receive key presses.
    # "& 0xFF" keeps only the key code, since macOS can add extra bits.
    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord("q"):
        break

# Leave the board quiet rather than stuck buzzing after the script ends.
send("off")
time.sleep(0.2)

camera.release()
cv2.destroyAllWindows()
if board is not None:
    board.close()
