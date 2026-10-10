# Tips & Bottlenecks

Everything that went wrong between "Teachable Machine says 97% bottle" and "the
buzzer actually sounds". Each entry is a real problem this project hit, written
as symptom → cause → fix, because the symptom is almost never a clue to the
cause in a pipeline like this.

> **TODO — your own notes.** Items marked 🖊️ are places to add your own account:
> how long it took, what you tried first, what you were looking at when it
> clicked. That is the part the write-up is actually graded on. Screenshots of
> the error messages are worth adding wherever you still have them.

---

## Version mismatches

### 1. Keras 3 cannot load a Teachable Machine model at all

**Symptom.** `load_model("keras_model.h5")` failed outright. The error talks
about the HDF5 legacy format being unsupported, not about anything in the file
being wrong.

**Cause.** Teachable Machine exports **Keras 2** `.h5` models. TensorFlow 2.21
ships **Keras 3** as its built-in `tf.keras`, and Keras 3 dropped the ability to
load Keras 2 HDF5 files. So the export is fine and the loader is fine — they are
just two incompatible generations, and nothing in the error message says so.

**Fix.** Install the `tf-keras` compatibility package, set the environment
variable *before* TensorFlow is imported, and import from `tf_keras` instead of
`tensorflow.keras`:

```python
os.environ["TF_USE_LEGACY_KERAS"] = "1"   # must be before any TF import
...
from tf_keras.models import load_model
```

**Tip.** The ordering is the trap. `TF_USE_LEGACY_KERAS` is read once when
TensorFlow initialises, so setting it after an `import tensorflow` anywhere
higher in the file silently does nothing. That is why those two lines sit at the
very top of the script with a comment explaining why they cannot be moved.

🖊️ *Your note: how many different fixes did you try before this one? Did you
try downgrading TensorFlow first?*

### 2. `mutex lock failed: Invalid argument` — a crash from a package we never use

**Symptom.** TensorFlow aborted on import with `mutex lock failed: Invalid
argument`, before a single line of our own code ran. No stack trace pointing
anywhere useful.

**Cause.** `pyarrow`, pulled in indirectly through `pandas`, conflicts with
TensorFlow's threading on macOS. This pipeline never touches pandas or pyarrow —
it was collateral damage from something else in the environment.

**Fix.** Block the import before TensorFlow loads:

```python
sys.modules["pyarrow"] = None
```

**Tip.** This is a blunt instrument and it is deliberate. It works because
nothing here needs pyarrow, so poisoning the module entry is cheaper than
untangling the dependency tree. In a project that *did* use pandas, the real fix
would be matching pyarrow and TensorFlow versions instead.

### 3. Python version

TensorFlow wheels lag behind new Python releases. This was built on **Python
3.12.10**. A newer interpreter means `pip install tensorflow` either fails to
find a wheel or tries to build from source, which is a long detour for nothing.

**Tip.** Pin the interpreter first, then the packages. `requirements.txt` has
the exact versions that work together.

---

## Camera

### 4. The camera "opens" successfully and returns nothing

**Symptom.** `cv2.VideoCapture(0)` succeeded, `camera.isOpened()` returned
`True`, and every `camera.read()` came back empty. It looked exactly like a
broken or in-use webcam.

**Cause.** macOS camera permission. When permission has not been granted, macOS
does not fail the open — it hands over a working capture object that produces
empty frames forever.

**Fix.** System Settings → Privacy & Security → Camera, enable the switch for
the app that launches Python (**Visual Studio Code**, **Terminal**, or **iTerm**
— not "Python"), then **quit that app entirely with Cmd-Q and reopen it**.

**Tip.** The restart is the part everyone skips. macOS only applies a new camera
permission when the app next launches, so toggling the switch while VS Code is
running changes nothing and makes it look like the permission was not the
problem after all.

This cost enough time that the script now prints a 15-line explanation instead
of an exception — see `CAMERA_HELP` in the main script.

🖊️ *Your note: how long were you convinced the webcam itself was broken?*

### 5. The first few frames are empty even on a working camera

**Symptom.** Intermittent. Sometimes the script exited immediately with the
camera error, sometimes it ran perfectly — same hardware, same code.

**Cause.** AVFoundation on macOS needs a moment to spin up the capture session.
`isOpened()` being true does not mean a frame is ready yet.

**Fix.** Retry instead of giving up on the first failure — up to 60 attempts,
50 ms apart, before declaring the camera dead:

```python
for attempt in range(60):
    ret, frame = camera.read()
    if ret:
        break
    time.sleep(0.05)
else:
    sys.exit(CAMERA_HELP)
```

The same reasoning applies inside the main loop, where a counter tolerates up to
30 consecutive dropped frames. One dropped frame is normal and means nothing;
thirty in a row means Zoom took the camera.

**Tip.** Any "works sometimes" bug in a hardware pipeline is a timing bug. Look
for the thing you assumed was instant.

### 6. The image was being squashed, and accuracy quietly suffered

**Symptom.** The model performed noticeably worse against a live webcam than it
did in Teachable Machine's own preview.

**Cause.** The webcam delivers 16:9 (1280×720). Resizing that straight to
224×224 squashes everything horizontally. Teachable Machine **centre-crops to a
square** during training, so the model was being shown a kind of image it had
never seen.

**Fix.** Centre-crop to a square *first*, then resize:

```python
h, w = frame.shape[:2]
size = min(h, w)
top, left = (h - size) // 2, (w - size) // 2
frame = frame[top:top + size, left:left + size]
frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
```

**Tip.** Preprocessing at inference must match preprocessing at training,
exactly. This one is dangerous precisely because nothing errors — you just get a
worse model and no reason why.

---

## Serial and the board

### 7. The port name keeps changing

**Symptom.** A hardcoded `/dev/cu.usbmodem3101` worked, then stopped working
after unplugging and replugging the board.

**Cause.** macOS assigns the `usbmodem` number per port and per enumeration. It
changes between machines, and sometimes between plug-ins on the same machine.

**Fix.** Auto-detect. `find_board_port()` walks every serial port, skips the two
fake ones macOS always lists (`Bluetooth`, `debug-console`), and prefers a
genuine Arduino vendor ID (`0x2341`) while still accepting the usual clone chip
names (`usbserial`, `wchusbserial`, `SLAB_USBtoUART`).

**Tip.** When nothing is found, the script prints every port it *can* see. That
turns "no board found" from a dead end into a diagnosis — if the board is not in
that list, the problem is upstream of any code.

### 8. Opening the port resets the board, and the first messages vanish

**Symptom.** The first `on`/`off` sent after connecting was ignored. Everything
after it worked.

**Cause.** Opening a serial connection toggles DTR, which resets most Arduino
boards. For about two seconds the board is rebooting and not listening.

**Fix.** `time.sleep(2.5)` after opening the port, before sending anything. The
same wait exists in `serial_test.py`.

### 9. "Is the cable dead, or is the model just not confident?"

**Symptom.** Nothing happened, and there was no way to tell whether messages
were not arriving or the model was never crossing the threshold.

**Cause.** The link was write-only. Python talked, and nothing ever talked back.

**Fix.** Make it bidirectional. `BottleDisplay.ino` prints `BottleDisplay ready`
on startup and acknowledges every command with `ack on` / `ack off`. Python
counts those replies, and if none arrive it says so loudly:

```
*** The board never replied. It is powered and the port opened, but ***
*** nothing is coming back. Unplug the USB cable, wait 5 seconds,   ***
```

**Tip.** This was the single highest-value change in the whole project. Almost
every remaining bug became a two-second diagnosis instead of a hunt, because the
board's own voice told you which half of the pipeline was at fault.

### 10. The Serial Monitor steals the port

**Symptom.** `SerialException: could not open port ... Resource busy`.

**Cause.** Only one program can hold a serial port. The Arduino IDE's Serial
Monitor counts, and so does a previous copy of the script still running in
another terminal tab.

**Fix.** Close the Serial Monitor. There is no clever workaround.

**Tip.** This is the most frequent failure of the lot, and it comes back every
time you re-upload the sketch and forget to close the Monitor afterwards. The
error message now suggests it explicitly.

### 11. The display got stuck on `----` forever

**Symptom.** The board powered up showing `----` and stayed there, even though
the terminal was clearly printing `off` predictions.

**Cause.** The first version only sent a message when the answer *changed*. On
startup there was no previous answer and the scene was Background, so there was
nothing to send — and `----` means "I have not heard from the computer yet".

**Fix.** Two changes:
1. Send `off` explicitly for Background rather than sending nothing, and send one
   `off` the instant the script starts.
2. Add a **heartbeat** — resend the current state every 2 seconds even when
   unchanged.

**Tip.** The heartbeat is what makes this survive a board reset mid-demo.
Without it, a board that loses power comes back up on `----` and waits forever,
while Python happily believes it already said `on`. Knocking the display off
`----` in the first half-second is also a free sanity check: if it does not
move, the problem is the board or the wiring, and there is no point staring at
confidence numbers.

---

## Display wiring

### 12. The display lit up and showed a ghostly smear

**Symptom.** Segments from several characters visible at once, nothing legible.

**Cause.** Common cathode vs common anode. The two are wired in opposite
polarity, and the part number is rarely printed on the display.

**Fix.** Change `HARDWARE_CONFIG` in `BottleDisplay.ino` from `COMMON_CATHODE`
to `COMMON_ANODE` (or back). It is a one-word change — just try both.

### 13. Right characters, wrong positions

**Symptom.** The display spelled `nO  ` instead of ` On `.

**Cause.** `DIGIT_PINS` must be listed left-to-right as you look at the display.
Pins 9–12 on the breadboard were not in that physical order.

**Fix.** The `DigitTest` sketch, which exists only for this. It drives the pins
directly — no SevSeg library in the way — and lights **all segments of exactly
one digit** every 2 seconds while printing which pin it is using. Watch the
display and the Serial Monitor side by side, write down the real order, and
reorder `DIGIT_PINS` to match.

**Tip.** Writing a throwaway diagnostic sketch felt like a detour and was the
fastest path through this. Guessing at permutations of four pins is 24
upload-and-squint cycles; `DigitTest` answers it in one.

🖊️ *Your note: which order did yours turn out to be?*

### 14. Flicker whenever the buzzer sounded

**Symptom.** The digits visibly flickered or dimmed while the buzzer was on.

**Cause.** A 4-digit display is **multiplexed** — only one digit is physically
lit at any instant, cycled faster than the eye can follow. `refreshDisplay()`
has to run constantly. Anything that blocks the loop, including a `delay()` to
time a beep, stops the cycling and shows up as flicker.

**Fix.** Use `tone(BUZZER_PIN, BUZZER_FREQ)` with **no duration argument**. It
runs on a hardware timer, returns immediately, and keeps sounding until
`noTone()` is called. There is no `delay()` anywhere in `BottleDisplay.ino`, and
that is load-bearing.

**Tip.** If you add anything to that loop later and the digits start flickering,
whatever you just added is blocking.

---

## The model itself

### 15. Two classes were not enough

**Symptom.** With just *Bottle* and *Background*, holding up **anything** — a
phone, a hand — triggered the buzzer.

**Cause.** With only those two options, the easiest feature that separates them
is "is there an object in frame at all", not "is it a bottle". The model learned
the easy thing, which is what models do.

**Fix.** A third class, **Not bottle**, trained on other handheld objects. That
gives the model a reason to learn the bottle's actual shape, because "object
present" no longer predicts the answer.

**Tip.** This is the most transferable lesson in the project. A hard negative
class is worth more than more photos of the positive one.

🖊️ *Your note: what did you put in Not bottle, and did anything still fool it?*

### 16. 80% confidence was too strict for real room light

**Symptom.** A clearly visible bottle, obviously winning the prediction, and no
buzzer.

**Cause.** `CONFIDENCE_THRESHOLD` started at `0.80`. Under ordinary indoor
lighting a true positive often lands in the 60s — good enough to be the clear
winner, not good enough to clear the bar.

**Fix.** Lowered to `0.60`.

**Tip.** This was only diagnosable because the terminal prints **every** class
score, not just the winner:

```
[off] Background: 22%  Bottle: 68%  Not bottle: 10%
```

One glance separates "Bottle is losing" from "Bottle is winning but below the
threshold" — two different problems with two different fixes. Printing only the
argmax hides that distinction completely.

### 17. Keras printed a progress bar for every single frame

**Symptom.** The terminal was unreadable, scrolling progress bars at ~30 fps.

**Fix.** `model.predict(image, verbose=0)`.

---

## General lessons

1. **Make the hardware talk back.** The `ack` messages (#9) converted most of
   this list from guesswork into reading. Build the return channel before you
   need it.
2. **Isolate one layer at a time.** `serial_test.py` tests the board with no
   camera or model; `DigitTest` tests the wiring with no library; the non-serial
   script tests the model with no hardware. When something breaks, the question
   is always "which layer", and each of those answers it in under a minute.
3. **Errors are not clues.** Camera permission reported as empty frames (#4),
   version mismatch reported as a mutex failure (#2), wrong preprocessing
   reported as nothing at all (#6). In a pipeline, suspect the layer, not the
   message.
4. **"Works sometimes" means timing.** Both #5 and #8 were races against
   hardware startup, and both looked like random flakiness.
5. **Write the error message you wish you had seen.** The long `CAMERA_HELP`
   text and the "board never replied" warning were written immediately after
   losing time to those exact problems. They cost five minutes each and saved
   that many times over.

🖊️ *Your note: anything that bit you that is not on this list? Add it — the
ones you hit yourself are the ones worth writing up.*
