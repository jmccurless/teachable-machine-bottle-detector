/*
  BottleDisplay

  Listens for messages from the Teachable Machine Python script and shows the
  answer on a 4-digit 7-segment display.

    "on"   ->  display shows " On",  buzzer sounds   (camera sees a Bottle)
    "off"  ->  display shows "OFF",  buzzer silent   (camera sees something else)

  The buzzer sounds for as long as the bottle stays in view, and stops the
  moment it leaves.

  Before the first message arrives the display shows "----", so you can tell
  the difference between "waiting to hear from the computer" and "heard OFF".

  A 7-segment digit cannot form a real capital N, so the N is drawn as a
  lowercase n. This is the normal way these displays spell "On".

  Needs the SevSeg library:  Tools > Manage Libraries, search SevSeg, Install.

  WIRING - see the notes under SEGMENT_PINS and DIGIT_PINS below.
*/

#include "SevSeg.h"

SevSeg display;

// ----------------------------------------------------------------------
// Wiring
// ----------------------------------------------------------------------

// The 7 segment pins, in this exact order: a, b, c, d, e, f, g.
// Each one goes through its own 470 ohm resistor on the way to the display.
// The order matters - the library assumes a through g.
// The decimal point is NOT wired up, which is why there are 7 here and not 8.
byte SEGMENT_PINS[] = {2, 3, 4, 5, 6, 7, 8};

// The 4 digit pins, ordered LEFT to RIGHT as you look at the display.
// These connect straight to the display, with no resistors.
byte DIGIT_PINS[] = {9, 10, 11, 12};

// Is your display common cathode or common anode? If the display lights up but
// shows the wrong thing - segments from several characters at once, or a sort of
// ghostly smear - this is almost certainly the setting to change.
// Try COMMON_ANODE instead.
byte HARDWARE_CONFIG = COMMON_CATHODE;

// true because the resistors are on the segment wires, not the digit wires.
bool RESISTORS_ON_SEGMENTS = true;

// Must match the BAUD_RATE number in the Python script.
const long BAUD_RATE = 9600;

// The built-in LED still mirrors the display, as a second thing to look at.
const int LED_PIN = LED_BUILTIN;

// Passive buzzer. The + leg goes here, the - leg goes to GND.
// A0 is used because pins 2 to 12 are taken by the display and 13 has the LED.
const int BUZZER_PIN = A0;

// The pitch of the buzz, in hertz. Piezo buzzers are loudest somewhere around
// 2000 to 4000. Lower this for a softer, less piercing note.
const int BUZZER_FREQ = 2000;

// What to actually show. Four characters, because there are four digits.
// Spaces leave a digit dark. Change these if you want it sitting elsewhere.
const char TEXT_ON[]      = " On ";
const char TEXT_OFF[]     = "OFF ";
const char TEXT_WAITING[] = "----";

// Where we collect the characters of the message as they arrive one at a time.
String message = "";


void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Start silent, so the buzzer does not sound while we wait for a message.
  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  Serial.begin(BAUD_RATE);
  message.reserve(16);

  // Announce ourselves. This is the only way to prove the board -> computer
  // direction of the cable actually works. Without it a board can look dead
  // when the real problem is that nothing is listening.
  Serial.println("BottleDisplay ready");

  display.begin(HARDWARE_CONFIG,
                4,                      // number of digits
                DIGIT_PINS,
                SEGMENT_PINS,
                RESISTORS_ON_SEGMENTS,
                false,                  // updateWithDelays - leave false
                false,                  // leadingZeros - not showing numbers
                true);                  // disableDecPoint - the dot is not wired

  // 0 to 100. Turn it down if the display is uncomfortably bright.
  display.setBrightness(90);

  display.setChars(TEXT_WAITING);
}


void loop() {
  // This has to run over and over, as fast as possible. The display only ever
  // lights ONE digit at a time and switches between them faster than the eye
  // can follow, which is what makes all four look lit at once. Anything that
  // stalls this loop - a delay(), a slow calculation - shows up as flicker.
  // That is why there is no delay() anywhere in this sketch.
  display.refreshDisplay();

  // Read whatever has arrived, one character at a time.
  while (Serial.available() > 0) {
    char incoming = Serial.read();

    if (incoming == '\n') {
      // A newline means the message is finished, so act on it.
      handleMessage(message);
      message = "";  // Clear it, ready for the next one
    } else if (incoming != '\r') {
      // Collect this character. '\r' is skipped because some programs send
      // "\r\n" instead of just "\n", and we do not want it in the message.
      message += incoming;
    }
  }
}


void handleMessage(String text) {
  // Remove any stray spaces, so " on" and "on " both still work.
  text.trim();

  if (text == "on") {
    display.setChars(TEXT_ON);
    digitalWrite(LED_PIN, HIGH);
    // tone() with no duration keeps sounding until noTone() is called. It runs
    // on a hardware timer, so this line returns straight away and the display
    // keeps refreshing. Do NOT add a delay() here - it would freeze the digits.
    tone(BUZZER_PIN, BUZZER_FREQ);
    Serial.println("ack on");
  } else if (text == "off") {
    display.setChars(TEXT_OFF);
    digitalWrite(LED_PIN, LOW);
    noTone(BUZZER_PIN);
    Serial.println("ack off");
  } else {
    // Anything else leaves the display alone, but say what arrived. If this
    // prints gibberish, the two baud rates do not match.
    Serial.print("ignored: ");
    Serial.println(text);
  }
}
