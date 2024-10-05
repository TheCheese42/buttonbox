#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

using namespace std;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);


vector<String> tasks = {};
vector<int> taskTimestamps = {};


void resetDisplay() {
  display.clearDisplay();
  display.display();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
}


void execTask(String task);


void setup() {
  Serial.begin(115200);
  Serial.println("BUTTONBOX - SETUP");

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Failed to start SSD1306 OLED Display"));
    while (1);
  }

  delay(20);

  resetDisplay();
  display.println("Starting BUTTONBOX...");
  display.display();
  delay(200);
  display.println("Establishing connection with Computer...");
  display.println("Waiting for HANDSHAKE byte...");
  display.display();
  while (true) {
    Serial.write("HANDSHAKE");
    if (Serial.available() > 0) {
      String receivedData = Serial.readStringUntil('\n');
      if (receivedData == "HANDSHAKE") {
        break;
      }
    }
    delay(10);
  }
  display.println("HANDSHAKE received.");
  display.display();
}


void loop() {
  while (true) {
    if (Serial.available() > 0) {
      String receivedData = Serial.readStringUntil('\n');
      execTask(receivedData);
    }
  }
}


void execDisplayTask(String task) {
  if (task.startsWith("display reset")) {
    resetDisplay();
  } else if (task.startsWith("display display")) {
    display.display();
  } else if (task.startsWith("display print")) {
    String text = task.substring(14);
    display.print(text);
  } else if (task.startsWith("display println")) {
    String text = task.substring(16);
    display.print(text);
  } else {
    Serial.println("ERROR Invalid display task '" + task + "'");
  }
}


void execTask(String task) {
  if (task.startsWith("digital HIGH")) {
    int num = task.substring(13).toInt();
    digitalWrite(num, HIGH);
  } else if (task.startsWith("digital LOW")) {
    int num = task.substring(12).toInt();
    digitalWrite(num, LOW);
  } else if (task.startsWith("display")) {
    execDisplayTask(task);
  } else {
    Serial.println("ERROR Invalid task '" + task + "'");
  }
}
