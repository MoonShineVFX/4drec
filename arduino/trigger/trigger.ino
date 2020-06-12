int currentState = HIGH;
int lastState = HIGH;
unsigned long lastTriggerTime = -1;

void setup() {
  Serial.begin(9600);
  pinMode(A1, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);
  pinMode(10, INPUT);
  digitalWrite(10, HIGH);
  Serial.println("ready!");

  //digitalWrite(A1, HIGH);
}

void loop() {
  if (Serial.available() > 0) {
    while (Serial.read() > -1);
    trigger(true);
  }
  
  currentState = digitalRead(10);
  if (currentState != lastState) {
    lastState = currentState;
    Serial.print("State change to: ");
    Serial.println(currentState);
    digitalWrite(LED_BUILTIN, currentState);
  }

  if (lastTriggerTime != -1) {
    if (millis() - lastTriggerTime > 1000) {
      trigger(false);
    }
  }
}

void trigger(bool toggle) {
  if (toggle) {
    Serial.println("trigger on!");
    digitalWrite(A1, HIGH);
    lastTriggerTime = millis();
  }else{
    Serial.println("trigger off!");
    digitalWrite(A1, LOW);
    lastTriggerTime = -1;
  }
}
