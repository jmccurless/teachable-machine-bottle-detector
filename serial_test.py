"""
serial_test.py

A hardware checker, not a real program. Run this when the Arduino does nothing
while the Teachable Machine script is running.

It skips the camera and the model entirely and just sends "on" and "off" to the
board, over and over, so you can watch the board and see whether it reacts.

WHAT IT DOES
Sends "on", waits 3 seconds, sends "off", waits 3 seconds. Four times.

WHAT YOU SHOULD SEE (with BottleDisplay uploaded)
  "on"   ->  display " On",  the little "L" LED on the board lights,  buzzer sounds
  "off"  ->  display "OFF",  the "L" LED goes dark,                  buzzer silent

WHAT IT MEANS IF YOU DO NOT

- "Could not open the port" below
    Something else is already holding the port. Close the Arduino IDE's
    Serial Monitor (and any other copy of the Python script) and run this again.
    This is the most common cause by far.

- The port opens, but the board does nothing at all - not even the "L" LED
    The "L" LED needs no wiring, so this is not a wiring problem. BottleDisplay
    is probably not actually on the board. Re-upload it in the Arduino IDE and
    watch for "Done uploading", then run this again.

- The "L" LED follows on/off correctly, but the display or buzzer does not
    Serial is working fine and the sketch is running. The problem is the display
    wiring or the COMMON_CATHODE / COMMON_ANODE setting in BottleDisplay.
    Run the DigitTest sketch next.

- Everything here works, but it still does nothing during the real script
    The board and the link are fine. The model is simply never reporting Bottle
    above CONFIDENCE_THRESHOLD, so "on" is never sent. Lower that threshold in
    the main script, or retrain with more varied photos.
"""

import sys
import time

import serial
import serial.tools.list_ports

# None means "find the board automatically", which is the right answer almost
# always - the usbmodem number changes between machines and sometimes between
# plug-ins. Set a string like "/dev/cu.usbmodem3101" only to override.
SERIAL_PORT = None

# Must match the main script.
BAUD_RATE = 9600

# How many times to go round, and how long to hold each state so you have
# time to look up at the board.
ROUNDS = 4
HOLD_SECONDS = 3

def find_board_port():
    """Pick the most likely Arduino port, or return None if nothing looks right.

    Same logic as the main script, kept as its own copy so this checker stays
    standalone - it has to keep working even when the main script does not.
    """
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


port_name = SERIAL_PORT or find_board_port()

if port_name is None:
    # Listing what we CAN see turns "no board found" into a diagnosis. If the
    # board is not in this list, the problem is upstream of any code here.
    print("No Arduino-looking serial port found. Is the board plugged in?")
    print("Ports I can see right now:")
    for port in serial.tools.list_ports.comports():
        print(f"  {port.device}  ({port.description})")
    sys.exit(1)

try:
    board = serial.Serial(port_name, BAUD_RATE, timeout=1)
except serial.SerialException as error:
    # Unlike the main script, this one stops here. A test that cannot reach the
    # board has nothing useful left to do.
    sys.exit(f"Could not open the port {port_name}: {error}\n"
             "Close the Arduino IDE's Serial Monitor and try again.")

print(f"Opened {port_name} at {BAUD_RATE} baud.")

# Opening the port resets most Arduino boards. Give it time to restart,
# otherwise the first messages are sent into the void.
print("Waiting 2 seconds for the board to restart...")
time.sleep(2)

print("\nWatch the board now.\n")

for round_number in range(1, ROUNDS + 1):
    for message in ("on", "off"):
        board.write((message + "\n").encode())
        expected = 'display " On",  L LED lit,   buzzer sounding' if message == "on" \
            else 'display "OFF",  L LED dark,  buzzer silent'
        print(f"[{round_number} of {ROUNDS}] Sent {message!r:6} -> expect {expected}")
        time.sleep(HOLD_SECONDS)

# Leave the board quiet rather than stuck buzzing.
board.write(b"off\n")
board.close()

print("\nDone. The board was left in the off state.")
print("Compare what you saw with the notes at the top of this file.")
