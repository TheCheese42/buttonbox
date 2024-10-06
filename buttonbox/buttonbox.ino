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

// From top to bottom as the buttons are places, NOT as the pins are placed
const int BUTTON_MATRIX_PINS[] = {26, 25, 33, 32, 35, 34};  // Eventually ADAPT

const int BUTTON_SINGLE_PIN = 17;  // Eventually ADAPT

const int ROTARY_ENCODER_CLK = 14;  // Eventually ADAPT
const int ROTARY_ENCODER_DT = 27;  // Eventually ADAPT

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
    display.println(text);
  } else if (task.startsWith("display profile")) {
    String num = task.substring(16, 18);
    String profile = task.substring(19);
    resetDisplay();
    display.setTextSize(2);
    display.println("Profile: " + num);
    display.println();
    display.setTextSize(2);
    display.println(profile);
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
