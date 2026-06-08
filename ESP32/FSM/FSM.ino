#define STX 0x02
#define ETX 0x03

// INPUTS
const int trigger = 5;
const int bin_0 = 18;
const int bin_1 = 19;
const int quality_key = 4;
const int sensor_L = 2;
const int sensor_R = 15;

// OUPUTS
const int result = 32;

// FSM
enum State {
  IDLE,
  TRIGGERED,
  WAIT_SENSORS,
  EVALUATE,
  RESULT
};

State currentState = IDLE;

// VARIABLES
String currentModel = "A";
String lastModel = "A";

String lastResultMsg = "";

String buffer = "";
bool receiving = false;
bool visionResult = false;
bool visionReceived = false;

bool finalResult = false;

bool lastQualityState = false;
bool lastTriggerState = false;

bool reseted = false;

bool triggerState = false;
bool lastStableState = false;

bool triggerEvent = false;
bool triggerLatched = false;

bool systemSynced = false;
bool handshakeReceived = false;

bool waitingAckResult = false;

unsigned long lastSendTime = 0;
const unsigned long ackTimeout = 500;

unsigned long triggerStartTime = 0;
const unsigned long miniTriggerTime = 100;

unsigned long stateStartTime = 0;
unsigned long timeoutVision = 12000;


// HELPERS
void handleTrigger() {
  bool reading = digitalRead(trigger);

  // CONTEO
  if (reading == HIGH && triggerStartTime == 0) {
    triggerStartTime = millis();
  }

  if (reading == HIGH && triggerStartTime > 0) {
    if (millis() - triggerStartTime > miniTriggerTime) {
      triggerState = true;
    }
  }

  // RESET SI CAE A LOW
  if (reading == LOW) {
    triggerStartTime = 0;
    triggerState = false;
    triggerLatched = false;
  }

  if (triggerState && !triggerLatched) {
    triggerLatched = true;

    Serial.println("[ESP] Trigger valido");
    sendSerial("TRIGGER");
    triggerEvent = true;
  }
}

String getModel() {
  int b0 = digitalRead(bin_0);
  int b1 = digitalRead(bin_1);

  if (b0 == HIGH && b1 == LOW) return "B";
  if (b0 == LOW && b1 == HIGH) return "A";
  if (b0 == HIGH && b1 == HIGH) return "C";

  return currentModel;
}

void sendSerial(String msg) {
  Serial.write(STX);
  Serial.print(msg);
  Serial.write(ETX);
  Serial.println("");
}

void processSerial() {
  while (Serial.available()) {
    byte b = Serial.read();

    if (b == STX){
      buffer = "";
      receiving = true;
    }

    else if (b == ETX && receiving == true){
      receiving = false;
      procesar(buffer);   // FUNCION PARA OBTENER EL RESULTADO DE VISION
    }

    else if (receiving){
      buffer += (char)b;
    }
  }
}

void procesar(String message){
  if (message == "OK"){
    visionResult = true;
    visionReceived = true;
    sendSerial("ACK");
  }
  else if (message == "NG"){
    visionResult = false;
    visionReceived = true;
    sendSerial("ACK");
  }
  else if (message == "SYNC"){
    handshakeReceived = true;
    sendSerial("ACK");
  }
  else if (message == "ACK"){
    if (waitingAckResult){
      waitingAckResult = false;
      Serial.println("[ESP] ACK de RESULT recibido");
    }
  }
}

void sendResultWithAck(String msg) {
  sendSerial(msg);
  lastResultMsg = msg;
  waitingAckResult = true;
  lastSendTime = millis();

  Serial.print("[ESP] Enviado: ");
  Serial.println(msg);
}

void sendHandshake() {
  currentModel = getModel();
  lastModel = currentModel;

  sendSerial("SYNC_OK|MODEL: " + currentModel);
  systemSynced = true;

  Serial.println("[ESP] Handshake completado");
}

bool readStable(int pin) {
  bool a = digitalRead(pin);
  delayMicroseconds(200);
  bool b = digitalRead(pin);
  return (a && b);
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  pinMode(trigger, INPUT_PULLDOWN);
  pinMode(bin_0, INPUT);
  pinMode(bin_1, INPUT);
  pinMode(quality_key, INPUT);
  pinMode(sensor_L, INPUT);
  pinMode(sensor_R, INPUT);
  pinMode(result, OUTPUT);

  digitalWrite(result, LOW);
}

void loop() {
  // put your main code here, to run repeatedly:
  processSerial();

  if (waitingAckResult) {
    if (millis() - lastSendTime > ackTimeout){
      Serial.println("[ESP] Reenviando RESULT...");
      sendSerial(lastResultMsg);
      lastSendTime = millis();
    }
  }

  if (!systemSynced && handshakeReceived) {
    delay(200);
    sendHandshake();
    handshakeReceived = false;
  }

  bool currentQuality = digitalRead(quality_key);

  if (currentQuality && !lastQualityState) {
    Serial.println("[FSM] Reset de calidad");

    buffer = "";
    receiving = false;
    visionReceived = false;
    visionResult = false;
    reseted = true;
    currentState = IDLE;

    sendSerial("RESET");
  }

  lastQualityState = currentQuality;

  if (reseted && digitalRead(trigger) == LOW) {
      digitalWrite(result, LOW);
      reseted = false;
    }

  if (!systemSynced){
      // BLOQUEAR FSM HASTA HANDSHAKE
    }
  else {
  // FSM
    switch (currentState) {
      case IDLE:
        handleTrigger();

        if (triggerEvent) {
          triggerEvent = false;
          receiving = false;
          visionResult = false;
          visionReceived = false;
          waitingAckResult = false;
          lastResultMsg = "";
          buffer = "";
          stateStartTime = millis();
          currentState = WAIT_SENSORS;
        }
        currentModel = getModel();

        if (currentModel != lastModel) {
          sendSerial("MODEL: " + currentModel);
          lastModel = currentModel;
        }
        break;

      case WAIT_SENSORS:
        if (currentState != WAIT_SENSORS) break;

        if (visionReceived) {
          currentState = EVALUATE;
        }
        else if (millis() - stateStartTime > timeoutVision) {
          visionResult = false;
          currentState = EVALUATE;
          Serial.print(millis());
          Serial.println("[FSM]Timeout Vision\n");
        }
        break;

      case EVALUATE: {
        bool sensorL = readStable(sensor_L);
        bool sensorR = readStable(sensor_R);

        if (currentModel == "A") {
          finalResult = (!sensorL && !sensorR && visionResult);
        }
        else if (currentModel == "B") {
          finalResult = (!sensorL && sensorR && visionResult);
        }
        else if (currentModel == "C") {
          finalResult = (sensorL && sensorR && visionResult);
        }

        digitalWrite(result, finalResult ? HIGH: LOW);

        String resultMsg = finalResult ? "OK": "NG";

        Serial.print("[RESULT] ");
        Serial.println(resultMsg);

        sendResultWithAck(resultMsg);

        currentState = RESULT;
        break;
      }

      case RESULT:
        if (finalResult){
          Serial.println("[FSM] Fin de ciclo exitoso");
          if (digitalRead(trigger) == LOW) {
            digitalWrite(result, LOW);
            currentState = IDLE;
          }
        }
    }
  }
  delay(50);
}
