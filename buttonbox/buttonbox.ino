#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

#define SCREEN_WIDTH 128 // ADJUST set correct width for your OLED
#define SCREEN_HEIGHT 64 // ADJUST set correct height for your OLED

Adafruit_SSD1306 oled(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(115200);
  Serial.println("BUTTONBOX - SETUP");

  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Failed to start SSD1306 OLED"));
    while (1);
  }

  delay(2000);
}

void loop() {
  oled.clearDisplay();
  oled.drawTriangle(30, 50, 98, 50, 64, 10, WHITE);
  oled.display();
}
