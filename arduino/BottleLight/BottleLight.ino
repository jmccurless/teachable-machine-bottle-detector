/*
  BottleLight

  Listens for messages from the Teachable Machine Python script and switches
  the board's built-in LED to match.

    "on"   ->  LED on   (the camera sees a Bottle)
    "off"  ->  LED off  (the camera sees something else)

  The Python script sends each message followed by a newline, and only sends
  when the answer changes, so this sketch just waits for a full line to arrive.
*/

// The LED built into the board. On the Mega 2560 this is the one marked "L",
// next to pin 13. LED_BUILTIN is the right pin number for whichever board you use.
const int LED_PIN = LED_BUILTIN;

// Must match the BAUD_RATE number in the Python script.
const long BAUD_RATE = 9600;

// Where we collect the characters of the message as they arrive one at a time.
String message = "";

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Start with the light off

  Serial.begin(BAUD_RATE);

  // Give the String room to grow without reallocating as characters arrive.
  message.reserve(16);
}

void loop() {
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
    digitalWrite(LED_PIN, HIGH);
  } else if (text == "off") {
    digitalWrite(LED_PIN, LOW);
  }
  // Anything else is ignored, so a garbled message leaves the light alone.
}
