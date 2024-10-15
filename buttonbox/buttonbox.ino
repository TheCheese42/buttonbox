#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

using namespace std;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// What voltages are the pins under when the buttons are pressed
// From left to right
const int BUTTON_MATRIX_VOLTAGES[] = {4095, 2000, 1000};  // ADAPT

// ± Range of voltages
const int BUTTON_VOLTAGE_RANGE = 50;

// From top to bottom as the buttons are placed, *not* as the pins are placed
const int BUTTON_MATRIX_PINS[] = {26, 25, 33, 32, 35, 34};  // ADAPT

const int BUTTON_SINGLE_PIN = 17;  // ADAPT

const int ROTARY_ENCODER_CLK = 14;  // ADAPT
const int ROTARY_ENCODER_DT = 27;  // ADAPT

const int LED_LEFT_PIN = 4;  // ADAPT
const int LED_MIDDLE_PIN = 0;  // ADAPT
const int LED_RIGHT_PIN = 2;  // ADAPT
const int LED_EXTRA_PIN = 16;  // ADAPT

int ROTARY_ENCODER_STATE = HIGH;

// Use for things like LEDs
int OUTPUT_PINS[] = {4, 0, 2, 16};


void resetDisplay() {
  display.clearDisplay();
  display.display();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
}


void execTask(String task);


void pollButtonMatrix();


void pollButtonSingle();


void pollRotaryEncoder();


void setup() {
  for (int pin : BUTTON_MATRIX_PINS) {
    pinMode(pin, INPUT_PULLUP);
  }
  pinMode(BUTTON_SINGLE_PIN, INPUT);
  pinMode(ROTARY_ENCODER_CLK, INPUT);
  pinMode(ROTARY_ENCODER_DT, INPUT);
  for (int pin : OUTPUT_PINS) {
    pinMode(pin, OUTPUT);
  }


  Serial.begin(115200);
  Serial.println("DEBUG BUTTONBOX - SETUP");

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("DEBUG Failed to start SSD1306 OLED Display"));
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
    if (Serial.available() > 0) {
      String receivedData = Serial.readStringUntil('\n');
      if (receivedData == "HANDSHAKE") {
        Serial.println("HANDSHAKE");
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
    pollButtonMatrix();
    pollButtonSingle();
    pollRotaryEncoder();
  }
}


void pollRotaryEncoder() {
  int newState = digitalRead(ROTARY_ENCODER_CLK);
  if (newState != ROTARY_ENCODER_STATE) {
    ROTARY_ENCODER_STATE = newState;
    int dtValue = digitalRead(ROTARY_ENCODER_DT);
    if (newState == LOW && dtValue == HIGH) {
      Serial.println("EVENT ROTARYENCODER CLOCKWISE");
    } else if (newState == LOW && dtValue == LOW) {
      Serial.println("EVENT ROTARYENCODER COUNTERCLOCKWISE");
    }
  }
}


void pollButtonMatrix() {
  int rows = sizeof(BUTTON_MATRIX_PINS) / sizeof(BUTTON_MATRIX_PINS[0]);
  int cols = sizeof(BUTTON_MATRIX_VOLTAGES) / sizeof(BUTTON_MATRIX_VOLTAGES[0]);

  Serial.print("STATUS BUTTON MATRIX ");
  for (int i = 0; i < rows; i++) {
    for (int j = 0; j < cols; j++) {
      int val = analogRead(BUTTON_MATRIX_PINS[i]);
      if (val >= BUTTON_MATRIX_VOLTAGES[j] - BUTTON_VOLTAGE_RANGE && val <= BUTTON_MATRIX_VOLTAGES[j] + BUTTON_VOLTAGE_RANGE) {
        // Button active
        Serial.print("1");
      } else {
        // Button inactive
        Serial.print("0");
      }
      if (j != cols - 1) {
        Serial.print(":");
      }
    }
    Serial.print(";");
  }
  Serial.println();
}


void pollButtonSingle() {
  int state = digitalRead(BUTTON_SINGLE_PIN);
  Serial.print("STATUS BUTTON SINGLE ");
  if (state == HIGH) {
    Serial.println("1");
  } else {
    Serial.println("0");
  }
}


int parseLedPin(String str) {
  int pin;
  if (str.startsWith("LEFT")) {
    pin = LED_LEFT_PIN;
  } else if (str.startsWith("MIDDLE")) {
    pin = LED_MIDDLE_PIN;
  } else if (str.startsWith("RIGHT")) {
    pin = LED_RIGHT_PIN;
  } else if (str.startsWith("EXTRA")) {
    pin = LED_EXTRA_PIN;
  } else {
    pin = LED_EXTRA_PIN;
    Serial.println("ERROR Invalid LED specifier '" + str + "' (fallback to EXTRA)");
  }
  return pin;
}


void execDisplayTask(String task) {
  if (task.startsWith("DISPLAY RESET")) {
    resetDisplay();
  } else if (task.startsWith("DISPLAY DISPLAY")) {
    display.display();
  } else if (task.startsWith("DISPLAY PRINT")) {
    String text = task.substring(14);
    display.print(text);
  } else if (task.startsWith("DISPLAY PRINTLN")) {
    String text = task.substring(16);
    display.println(text);
  } else if (task.startsWith("DISPLAY PROFILE")) {
    String num = task.substring(16, 18);
    String profile = task.substring(19);
    resetDisplay();
    display.setTextSize(1);
    display.println("Profile: " + num);
    display.println();
    display.setTextSize(2);
    display.println(profile);
  } else {
    Serial.println("ERROR Invalid DISPLAY task '" + task + "'");
  }
}


void execLedTask(String task) {
  if (task.startsWith("LED HIGH")) {
    int pin = parseLedPin(task.substring(9, 15));
    digitalWrite(pin, HIGH);
  } else if (task.startsWith("LED LOW")) {
    int pin = parseLedPin(task.substring(8, 14));
    digitalWrite(pin, LOW);
  } else {
    Serial.println("ERROR Invalid LED task '" + task + "'");
  }
}


void execTask(String task) {
  if (task.startsWith("HANDSHAKE")) {
    Serial.println("HANDSHAKE");
  } else if (task.startsWith("DIGITAL HIGH")) {
    int num = task.substring(13).toInt();
    digitalWrite(num, HIGH);
  } else if (task.startsWith("DIGITAL LOW")) {
    int num = task.substring(12).toInt();
    digitalWrite(num, LOW);
  } else if (task.startsWith("DISPLAY")) {
    execDisplayTask(task);
  } else if (task.startsWith("LED")) {
    execLedTask(task);
  } else {
    Serial.println("ERROR Invalid task '" + task + "'");
  }
}
