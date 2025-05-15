#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <FastLED.h>

// ====== Configuration ======
#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "abcdef01-1234-5678-1234-56789abcdef0"

#define NUM_LEDS        4
#define DATA_PIN        5
#define STATUS_LED_PIN  8   // onboard status indicator

CRGB leds[NUM_LEDS];

// play a 3-step sequence on one LED, then leave it at the final color
void runSequence(int idx, CRGB seq[]) {
  for (int i = 0; i < 3; ++i) {
    leds[idx] = seq[i];       // only change this LED
    FastLED.show();
    delay(1500);
  }
  // now it stays at seq[2]; other LEDs untouched
}

// BLE server callbacks to drive STATUS_LED_PIN on connect/disconnect
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    digitalWrite(STATUS_LED_PIN, LOW);
  }
  void onDisconnect(BLEServer* pServer) override {
    digitalWrite(STATUS_LED_PIN, HIGH);
    pServer->startAdvertising();
  }
};

// BLE write callback for LED commands
class LEDCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pChar) override {
    String val = pChar->getValue();       // Arduino String
    int sep = val.indexOf(':');           // find “:”
    if (sep < 0) return;

    int ledNum = val.substring(0, sep).toInt() - 1;
    String state = val.substring(sep + 1);

    if (ledNum < 0 || ledNum >= NUM_LEDS) return;

    // Define “on” / “off” sequences
    CRGB onSeq[3]  = { CRGB::Red,    CRGB::Yellow, CRGB::Green  };
    CRGB offSeq[3] = { CRGB::Green,  CRGB::Yellow, CRGB::Red    };

    if (state.equalsIgnoreCase("ON")) {
      runSequence(ledNum, onSeq);
    } else if (state.equalsIgnoreCase("OFF")) {
      runSequence(ledNum, offSeq);
    }
  }
};

void setup() {
  Serial.begin(115200);

  // Status LED pin
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, HIGH);

  // FastLED init
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  FastLED.clear();
  FastLED.show();

  // Boot animation: G→Y→R on all LEDs, hold red
  CRGB bootSeq[3] = { CRGB::Green, CRGB::Yellow, CRGB::Red };
  for (int i = 0; i < 3; ++i) {
    fill_solid(leds, NUM_LEDS, bootSeq[i]);
    FastLED.show();
    delay(1500);
  }

  // BLE setup
  BLEDevice::init("ESP32_LED_Server");
  BLEServer* pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService* pService = pServer->createService(SERVICE_UUID);
  BLECharacteristic* pChar = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    BLECharacteristic::PROPERTY_WRITE
  );
  pChar->addDescriptor(new BLE2902());
  pChar->setCallbacks(new LEDCallbacks());

  pService->start();
  pServer->getAdvertising()->start();
  Serial.println("BLE LED server running...");
}

void loop() {
  // all work happens in callbacks
}
