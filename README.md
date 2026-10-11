# Bottle Detector — a Teachable Machine → Arduino pipeline

An end-to-end AI-hardware pipeline. A webcam watches the room, a Google
Teachable Machine image model decides whether it is looking at a bottle, and an
Arduino Mega 2560 reacts in the physical world: a 4-digit 7-segment display
spells out the answer and a piezo buzzer sounds while the bottle is in view.


The link runs both ways. Python sends `on` / `off`; the board answers
`ack on` / `ack off`, which is what makes it possible to tell a dead cable apart
from a model that simply is not confident enough.

## What's in here

| Path | What it is |
|---|---|
| [`GoogleTeachableCode-KerasOpenCV-Serial.py`](GoogleTeachableCode-KerasOpenCV-Serial.py) | **The main pipeline.** Camera → model → serial, with the on-screen overlay. |
| [`GoogleTeachableCode-KerasOpenCV.py`](GoogleTeachableCode-KerasOpenCV.py) | The same classifier with no hardware, for checking the model alone. |
| [`serial_test.py`](serial_test.py) | Hardware checker. Sends `on`/`off` on a timer, skipping the camera and model entirely. |
| [`arduino/BottleDisplay/`](arduino/BottleDisplay/) | **The sketch used in the demo.** Display + buzzer + built-in LED. |
| [`arduino/BottleLight/`](arduino/BottleLight/) | Minimal version: built-in LED only, no wiring needed. Good first milestone. |
| [`arduino/DigitTest/`](arduino/DigitTest/) | Wiring checker for the display. Lights one digit at a time. |
| `keras_model.h5` | The trained model, exported from Teachable Machine (Keras 2 format). |
| [`labels.txt`](labels.txt) | The three class names, in the model's output order. |
| [`TIPS-AND-BOTTLENECKS.md`](TIPS-AND-BOTTLENECKS.md) | What went wrong on the way here, and how each problem was fixed. |

## The model and its data

Trained in [Google Teachable Machine](https://teachablemachine.withgoogle.com/)
(Image Project → Standard image model) on webcam photos taken in the room where
the demo runs, then exported as **Tensorflow → Keras**.

| Class | Index | What it contains |
|---|---|---|
| Background | 0 | The empty scene — desk, wall, whatever the camera normally sees. |
| Bottle | 1 | A water bottle held at various distances and angles. |
| Not bottle | 2 | Other objects — phone, mug, hand — so the model learns "object, but not *that* object". |

Roughly 2000 images per class.

The three-class split matters. With only Bottle and Background, anything held up
to the camera reads as a bottle, because "something is there" is the easiest
feature to learn. The *Not bottle* class is what forces the model to learn the
bottle itself.

The exported model is committed here (`keras_model.h5`, ~2.4 MB) so the repo
runs without retraining. The raw training photos are not — Teachable Machine
keeps them in the browser session, and they are just webcam shots of a desk.

## Hardware

- Arduino **Mega 2560** + USB-B cable
- 4-digit 7-segment display, **common cathode**
- 7 × 470 Ω resistors
- Passive piezo buzzer
- Breadboard and jumper wires

### Wiring

Segment pins go through **one 470 Ω resistor each**. Digit pins connect
directly, with no resistors.

| Display pin | Arduino pin | Resistor? |
|---|---|---|
| Segment a | 2 | 470 Ω |
| Segment b | 3 | 470 Ω |
| Segment c | 4 | 470 Ω |
| Segment d | 5 | 470 Ω |
| Segment e | 6 | 470 Ω |
| Segment f | 7 | 470 Ω |
| Segment g | 8 | 470 Ω |
| Digit 1 (leftmost) | 9 | no |
| Digit 2 | 10 | no |
| Digit 3 | 11 | no |
| Digit 4 (rightmost) | 12 | no |

| Buzzer leg | Goes to |
|---|---|
| + | A0 |
| − | GND |


## Setup

### 1. Python

Needs Python 3.12.

```bash
git clone https://github.com/jmccurless/teachable-machine-bottle-detector.git
cd teachable-machine-bottle-detector
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Arduino

1. Open the Arduino IDE → **Tools → Manage Libraries**, search **SevSeg**, install it.
2. Open [`arduino/BottleDisplay/BottleDisplay.ino`](arduino/BottleDisplay/BottleDisplay.ino).
3. **Tools → Board → Arduino Mega or Mega 2560**, and pick the right port.
4. Upload, and wait for "Done uploading".
5. The display should show `----`, meaning "powered up, waiting to hear from the computer".

### 3. Run it

**Close the Arduino IDE's Serial Monitor first.** Only one program can hold the
serial port, and the Serial Monitor is the single most common reason this fails.

```bash
python3 GoogleTeachableCode-KerasOpenCV-Serial.py
```

The display should jump from `----` to `OFF` straight away. Hold up a bottle and
it switches to `On` with the buzzer. Click the webcam window and press **Esc** or
**q** to quit.

Terminal output looks like this:

```
Connected to /dev/cu.usbmodem3101 at 9600 baud.
  board: BottleDisplay ready
Camera ready (1280x720).
[off] Background: 94%  Bottle: 3%  Not bottle: 3%
[ON ] Background: 2%   Bottle: 97%  Not bottle: 1%
  board: ack on
```

Every class score is printed, not just the winner, so when the buzzer stays
quiet you can see why — either Bottle is losing to another
class, or it is winning but sitting below the confidence threshold.

## Settings worth knowing

All at the top of
[`GoogleTeachableCode-KerasOpenCV-Serial.py`](GoogleTeachableCode-KerasOpenCV-Serial.py):

| Setting | Default | What it does |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `0.60` | How sure the model must be before the buzzer sounds. Raise it if it triggers on nothing; lower it if a clear bottle is ignored. |
| `SERIAL_PORT` | `None` | `None` means it will auto detect.|
| `BOTTLE_LABEL` | `1` | Which row of `labels.txt` means "bottle". Change this if you retrain with classes in a different order. |
| `HEARTBEAT_SECONDS` | `2.0` | Resends the current state this often even when unchanged, so a board that gets reset mid-run recovers instead of sitting on `----` forever. |
| `BAUD_RATE` | `9600` | Must match `Serial.begin()` in the sketch. |

## When it doesn't work

Work down this list in order — each step rules out one layer of the pipeline.

| Symptom | Cause and fix |
|---|---|
| `Could not open /dev/cu.usbmodem...` | The Arduino IDE's Serial Monitor (or another copy of the script) already has the port. Close it. |
| `No Arduino-looking serial port found` | Board unplugged, or a charge-only USB cable. The script lists every port it *can* see — check the board appears there at all. |
| Display stuck on `----` | Nothing is arriving. Run `python3 serial_test.py`, which skips the camera and model entirely. |
| `*** The board never replied ***` | Port opened but nothing comes back. Unplug the USB cable, wait 5 seconds, plug it back in. |
| Camera window never opens, or frames are empty | macOS camera permission. See below. |
| Right characters, wrong positions | `DIGIT_PINS` order. Upload `arduino/DigitTest` and watch which position lights for each pin. |
| Buzzer silent but display works | You have an *active* buzzer, not a passive one. Active buzzers ignore `tone()`. |

### macOS camera permission

It may say: the camera **opens successfully** even when
permission is refused, and simply hands back empty frames.

1. **System Settings → Privacy & Security → Camera.**
2. Turn on the switch for — *Visual Studio Code*
   if you use its terminal, *Terminal*, or *iTerm*.
3. **Close and reopen the app.** macOS will only apply
   camera permission when the app next starts. This step is not optional.

Also check that nothing else holds the camera. Zoom, Teams, FaceTime, etc
all claim it exclusively.

## Notes on the implementation- From Claude

A few decisions that are not obvious from reading the code:

- **`off` is sent for Background, not nothing.** Sending only on changes sounds
  tidier but leaves the display stuck on `----` until the first bottle appears.
- **Centre-crop before resize.** Teachable Machine center-crops to a square
  during training. Resizing a 16:9 frame straight to 224×224 squashes it, and
  the model then sees something it was never trained on.
- **2.5-second wait after opening the port.** Opening a serial port resets most
  Arduino boards. Messages sent before it finishes rebooting goes nowhere.

## Tested on

| | |
|---|---|
| macOS | Darwin 27.0 (Apple Silicon) |
| Python | 3.12.10 |
| TensorFlow | 2.21.0 (with `tf-keras` 2.21.0) |
| OpenCV | 5.0.0.93 |
| NumPy | 2.5.3 |
| pyserial | 3.5 |
| Board | Arduino Mega 2560 |
| SevSeg | 3.7.0 |
