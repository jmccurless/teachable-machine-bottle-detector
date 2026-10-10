/*
  DigitTest

  A wiring checker, not a real program. Run this when the display shows the
  right characters in the wrong places, or when a digit is stuck lit.

  It deliberately does NOT use the SevSeg library. It drives the pins directly,
  one digit at a time, so there is nothing clever in the way of what you see.

  WHAT IT DOES
  Every 2 seconds it lights up ALL segments of exactly ONE digit, and prints
  which pin it is using to the Serial Monitor. Open the Serial Monitor at 9600
  and watch the display and the text side by side.

  WHAT YOU SHOULD SEE
  A single bright 8 marching from the far LEFT to the far RIGHT, one step at a
  time, while the Monitor counts 1, 2, 3, 4. Nothing else should be lit.

  WHAT IT MEANS IF YOU DO NOT
  - The 8 jumps around out of order  -> write down the real order. The number
    the Monitor prints, paired with the position you actually saw, tells you how
    to reorder DIGIT_PINS in BottleDisplay.
  - A second digit stays lit the whole time, through all four steps -> that
    digit's common pin is permanently connected to GND. It is a wiring fault,
    not a code problem. Follow that wire; it is in the wrong hole.
  - No digit lights at all -> change IS_COMMON_CATHODE to false below.
*/

// Must match BottleDisplay. Segments a, b, c, d, e, f, g. No decimal point.
byte SEGMENT_PINS[] = {2, 3, 4, 5, 6, 7, 8};

// Must match BottleDisplay. These are the pins we are testing the order of.
byte DIGIT_PINS[] = {9, 10, 11, 12};

// Set to false if your display turned out to be common anode.
const bool IS_COMMON_CATHODE = true;

const int NUM_DIGITS = 4;
const int NUM_SEGMENTS = 7;

// Which digit we are lighting right now.
int current = 0;


void setup() {
  Serial.begin(9600);

  for (int i = 0; i < NUM_SEGMENTS; i++) {
    pinMode(SEGMENT_PINS[i], OUTPUT);
  }
  for (int i = 0; i < NUM_DIGITS; i++) {
    pinMode(DIGIT_PINS[i], OUTPUT);
  }

  Serial.println();
  Serial.println("DigitTest running.");
  Serial.println("Watch for ONE bright 8 moving left to right.");
  Serial.println();
}


void loop() {
  // Turn every segment on. For common cathode the segment side is the positive
  // side, so HIGH lights it. For common anode it is the other way round.
  for (int i = 0; i < NUM_SEGMENTS; i++) {
    digitalWrite(SEGMENT_PINS[i], IS_COMMON_CATHODE ? HIGH : LOW);
  }

  // Enable only the digit we are testing, and firmly disable the other three.
  // A common cathode digit turns on when its common is pulled LOW.
  for (int i = 0; i < NUM_DIGITS; i++) {
    bool enabled = (i == current);
    if (IS_COMMON_CATHODE) {
      digitalWrite(DIGIT_PINS[i], enabled ? LOW : HIGH);
    } else {
      digitalWrite(DIGIT_PINS[i], enabled ? HIGH : LOW);
    }
  }

  Serial.print("Lighting digit ");
  Serial.print(current + 1);
  Serial.print(" of 4  (Arduino pin ");
  Serial.print(DIGIT_PINS[current]);
  Serial.println(")  <- which position is lit on the display?");

  // A plain delay is fine here. This sketch is not multiplexing, so there is
  // no flicker to worry about - we want each digit held still long enough
  // to look at it properly.
  delay(2000);

  current++;
  if (current >= NUM_DIGITS) {
    current = 0;
    Serial.println("--- starting over ---");
  }
}
