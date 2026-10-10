# Media — shot list

The assignment wants pictures or video showing the pipeline working, and they
have to be taken by you. The main `README.md` already links to the filenames
below, so if you save them with these exact names the images appear in the repo
automatically with no further editing.

Delete this file once the media is in, or leave it — either is fine.

## Required

| Filename | What to capture | Why it matters |
|---|---|---|
| `on-bottle.jpg` | Bottle held in front of the webcam, with the **display reading `On`** and the laptop screen visible in the same frame. | This is the money shot. One photo proving camera → model → hardware all the way through. |
| `off-background.jpg` | Same framing, bottle removed, **display reading `OFF`**. | Proves it switches back. A single `On` photo could be a coincidence or a hardcoded value. |
| `wiring.jpg` | Top-down shot of the breadboard, close enough to follow individual wires. | Worth more than the wiring table in the README, and shows the build is physically yours. |
| `demo.mp4` | 30–60 second run-through. See the script below. | The strongest evidence of the whole pipeline, and the thing a grader can check fastest. |

## Strongly recommended

| Filename | What to capture |
|---|---|
| `terminal-output.png` | Screenshot of the terminal mid-run, showing `board: ack on` and a line of class scores. Proves the two-way serial link. |
| `teachable-machine-training.png` | Screenshot of your Teachable Machine project with all three classes and their image counts. This is your "data" evidence for requirement 2. |

## Video script (30–60 seconds)

Frame the shot so the **display and the laptop screen are both visible** the
whole time. Record with your phone propped up, not handheld.

1. **Start before you run anything.** Show the display sitting on `----`. Say
   out loud that `----` means "waiting to hear from the computer" — it proves
   the board starts in a known state and is not just pre-set.
2. **Run the script.** `python3 GoogleTeachableCode-KerasOpenCV-Serial.py`
3. **Pause on the switch to `OFF`.** This happens within a second of startup and
   is the first proof the serial link works.
4. **Bring the bottle in slowly.** Let the confidence numbers climb on screen
   before it flips. The display goes to `On` and the buzzer sounds — make sure
   your phone picks up the sound.
5. **Take the bottle away.** Back to `OFF`, buzzer stops.
6. **Do it once more, faster.** Shows it is repeatable and not a one-off.
7. **Optional and worth it:** hold up a phone or a mug. It stays on `OFF`. That
   demonstrates the *Not bottle* class is doing real work, which is the most
   interesting design decision in the project.
8. **Press `q` to quit.** Buzzer goes silent, display settles — a clean shutdown.

## Practical notes

- **Keep files small.** GitHub rejects anything over 100 MB and warns above 50 MB.
  A 60-second phone video can easily exceed that. If `demo.mp4` is large:
  ```bash
  # Check the size first
  ls -lh media/demo.mp4

  # Shrink it (ffmpeg, or just use iMovie / QuickTime "Export 720p")
  ffmpeg -i demo-original.mp4 -vf scale=1280:-2 -b:v 2M -b:a 128k demo.mp4
  ```
  Under ~20 MB is comfortable.
- **Film in good light.** Not only for the video — the model's confidence is
  genuinely higher in bright light, so the demo itself works better.
- **Say the numbers out loud** if you narrate. "Bottle, 94 percent" alongside a
  visible display and an audible buzzer leaves nothing to interpret.
- **Keep one failure clip** if you have it. A short before/after — the display
  stuck on `----`, then working — pairs well with `TIPS-AND-BOTTLENECKS.md`
  and shows the debugging was real.
