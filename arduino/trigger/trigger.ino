int currentState = HIGH;
int lastState = HIGH;
unsigned long lastTriggerTime = -1;

void setup() {
  Serial.begin(9600);
  pinMode(19, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("ready!");
}

void loop() {
  if (Serial.available() > 0) {
    while (Serial.read() > -1);
    trigger(true);
  }
  
  if (lastTriggerTime != -1) {
    if (millis() - lastTriggerTime > 5000) {
      trigger(false);
    }
  }
}

void trigger(bool toggle) {
  if (toggle) {
    Serial.println("trigger on!");
    digitalWrite(19, HIGH);
    digitalWrite(LED_BUILTIN, HIGH);
    lastTriggerTime = millis();
  }else{
    Serial.println("trigger off!");
    digitalWrite(19, LOW);
    digitalWrite(LED_BUILTIN, LOW);
    lastTriggerTime = -1;
  }
}
