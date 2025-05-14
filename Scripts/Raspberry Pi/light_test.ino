#include <FastLED.h>

#define NUM_LEDS 4
#define DATA_PIN 5

CRGB leds[NUM_LEDS];

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
  Serial.println("Enter 1–4:");
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  // Ignore newlines
  if (c == '\n' || c == '\r') return;

  int idx = c - '1';         // Maps '1'→0, '2'→1, etc.
  if (idx < 0 || idx >= NUM_LEDS) {
    Serial.println("Invalid input. Enter 1–4.");
    return;
  }

  // Cycle through Red, Yellow, Green, then Off
  CRGB sequence[] = { CRGB::Red, CRGB::Orange, CRGB::Green, CRGB::Red };
  for (int step = 0; step < 4; ++step) {
    // Turn all LEDs off except the one we're animating
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    leds[idx] = sequence[step];
    FastLED.show();
    Serial.print("LED "); Serial.print(idx + 1);
    Serial.print(": ");
    switch (step) {
      case 0: Serial.println("Red");    break;
      case 1: Serial.println("Yellow"); break;
      case 2: Serial.println("Green");  break;
      case 3: Serial.println("Off");    break;
    }
    delay(500);  // 500 ms per color
  }
}
