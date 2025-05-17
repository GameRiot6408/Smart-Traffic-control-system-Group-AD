#include <FastLED.h>

// ====== Configuration ======
#define NUM_LEDS   4
#define DATA_PIN   5      // match your wiring
#define BAUD_RATE  115200

CRGB leds[NUM_LEDS];

// play a 3-step sequence on one LED, then leave it at the final color
void runSequence(int idx, const CRGB seq[3]) {
  for (int i = 0; i < 3; ++i) {
    leds[idx] = seq[i];       
    FastLED.show();
    delay(1500);
  }
  // stays at seq[2]
}

void setup() {
  Serial.begin(BAUD_RATE);
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  FastLED.clear(); FastLED.show();
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  int sep = line.indexOf(':');
  if (sep < 0) return;

  int ledNum = line.substring(0, sep).toInt() - 1;
  String state = line.substring(sep + 1);

  if (ledNum < 0 || ledNum >= NUM_LEDS) return;

  // Define “ON” / “OFF” sequences
  static const CRGB onSeq[3]  = { CRGB::Red,    CRGB::Yellow, CRGB::Green  };
  static const CRGB offSeq[3] = { CRGB::Green,  CRGB::Yellow, CRGB::Red    };

  if (state == "ON") {
    runSequence(ledNum, onSeq);
  } else if (state == "OFF") {
    runSequence(ledNum, offSeq);
  }
}
