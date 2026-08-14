#include <Arduino.h>
#include <esp_system.h>

#include "worksurface_config.h"

using namespace WorksurfaceConfig;

constexpr uint8_t STX = 0x02;
constexpr uint8_t ETX = 0x03;

enum class CycleState {
  IDLE,
  WAIT_VISION,
  WAIT_FINAL_ACK,
  HOLD_RESULT,
};

CycleState cycleState = CycleState::IDLE;

String rxPayload;
bool receivingFrame = false;
bool discardFrame = false;

bool linkSynced = false;
bool visionReady = false;
bool focusBusy = false;
unsigned long lastEngineContactMs = 0;

String bootToken;
uint32_t cycleCounter = 0;
String activeCycle;
String activeModel = DEFAULT_MODEL;
String lastPublishedModel = DEFAULT_MODEL;
String acceptedVisionResult;
String finalResult;

bool triggerAcked = false;
uint8_t triggerRetries = 0;
unsigned long lastTriggerSendMs = 0;
unsigned long visionDeadlineMs = 0;

bool finalAcked = false;
uint8_t finalRetries = 0;
unsigned long lastFinalSendMs = 0;

bool rawTrigger = false;
bool stableTrigger = false;
bool triggerLatched = false;
unsigned long triggerChangedMs = 0;
bool lastQualityRelease = false;

void debugLog(const String &message) {
  if (DEBUG_SERIAL_LOGS) Serial.println(message);
}

bool isActiveLevel(uint8_t pin, bool activeHigh) {
  return digitalRead(pin) == (activeHigh ? HIGH : LOW);
}

void setPassOutput(bool pass) {
  const bool levelHigh = pass == PLC_PASS_ACTIVE_HIGH;
  digitalWrite(PIN_PLC_PASS, levelHigh ? HIGH : LOW);
}

bool isUnreserved(uint8_t value) {
  return (value >= 'A' && value <= 'Z') ||
         (value >= 'a' && value <= 'z') ||
         (value >= '0' && value <= '9') || value == '-' || value == '_' ||
         value == '.' || value == ':';
}

char hexDigit(uint8_t value) {
  return value < 10 ? static_cast<char>('0' + value)
                    : static_cast<char>('A' + value - 10);
}

int hexValue(char value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'A' && value <= 'F') return value - 'A' + 10;
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}

String percentEncode(const String &value) {
  String encoded;
  encoded.reserve(value.length() + 16);
  for (size_t index = 0; index < value.length(); ++index) {
    const uint8_t current = static_cast<uint8_t>(value[index]);
    if (isUnreserved(current)) {
      encoded += static_cast<char>(current);
    } else {
      encoded += '%';
      encoded += hexDigit((current >> 4) & 0x0F);
      encoded += hexDigit(current & 0x0F);
    }
  }
  return encoded;
}

String percentDecode(const String &value) {
  String decoded;
  decoded.reserve(value.length());
  for (size_t index = 0; index < value.length(); ++index) {
    if (value[index] == '%' && index + 2 < value.length()) {
      const int high = hexValue(value[index + 1]);
      const int low = hexValue(value[index + 2]);
      if (high >= 0 && low >= 0) {
        decoded += static_cast<char>((high << 4) | low);
        index += 2;
        continue;
      }
    }
    decoded += value[index];
  }
  return decoded;
}

String messageKind(const String &payload) {
  const int separator = payload.indexOf('|');
  String kind = separator < 0 ? payload : payload.substring(0, separator);
  kind.trim();
  kind.toUpperCase();
  return kind;
}

String fieldValue(const String &payload, const String &requestedKey) {
  String key = requestedKey;
  key.toUpperCase();
  int start = payload.indexOf('|');
  while (start >= 0 && start + 1 < static_cast<int>(payload.length())) {
    const int end = payload.indexOf('|', start + 1);
    const String item = end < 0 ? payload.substring(start + 1)
                                : payload.substring(start + 1, end);
    const int equals = item.indexOf('=');
    if (equals > 0) {
      String candidate = item.substring(0, equals);
      candidate.trim();
      candidate.toUpperCase();
      if (candidate == key) {
        return percentDecode(item.substring(equals + 1));
      }
    }
    start = end;
  }
  return "";
}

void sendPayload(const String &payload) {
  Serial.write(STX);
  Serial.print(payload);
  Serial.write(ETX);
  Serial.flush();
}

void sendAck(const String &type, const String &cycle = "",
             const String &status = "OK", const String &error = "") {
  String payload = "ACK|TYPE=" + percentEncode(type);
  if (cycle.length() > 0) payload += "|CYCLE=" + percentEncode(cycle);
  payload += "|STATUS=" + percentEncode(status);
  if (error.length() > 0) payload += "|ERROR=" + percentEncode(error);
  sendPayload(payload);
}

void sendError(const String &code, const String &detail = "") {
  String payload = "ERROR|CODE=" + percentEncode(code);
  if (detail.length() > 0) payload += "|DETAIL=" + percentEncode(detail);
  sendPayload(payload);
}

String readModel() {
  const bool bit0 = isActiveLevel(PIN_MODEL_BIT_0, MODEL_BITS_ACTIVE_HIGH);
  const bool bit1 = isActiveLevel(PIN_MODEL_BIT_1, MODEL_BITS_ACTIVE_HIGH);
  if (bit0 && !bit1) return MODEL_BITS_10;
  if (!bit0 && bit1) return MODEL_BITS_01;
  if (bit0 && bit1) return MODEL_BITS_11;
  return "";
}

bool stableSensorIsOk(uint8_t pin) {
  uint8_t activeSamples = 0;
  for (uint8_t index = 0; index < SENSOR_STABLE_SAMPLES; ++index) {
    if (isActiveLevel(pin, SENSOR_OK_ACTIVE_HIGH)) ++activeSamples;
    delayMicroseconds(SENSOR_SAMPLE_DELAY_US);
  }
  return activeSamples == SENSOR_STABLE_SAMPLES;
}

bool physicalPatternPasses(const String &model) {
  const bool leftOk = stableSensorIsOk(PIN_SENSOR_LEFT);
  const bool rightOk = stableSensorIsOk(PIN_SENSOR_RIGHT);
  for (const SensorPattern &pattern : SENSOR_PATTERNS) {
    if (model == pattern.model) {
      return leftOk == pattern.left_ok && rightOk == pattern.right_ok;
    }
  }
  return false;
}

void resetCycleState() {
  setPassOutput(false);
  cycleState = CycleState::IDLE;
  activeCycle = "";
  acceptedVisionResult = "";
  finalResult = "";
  triggerAcked = false;
  triggerRetries = 0;
  finalAcked = false;
  finalRetries = 0;
  focusBusy = false;
  visionDeadlineMs = 0;
}

void loseLink(const String &reason) {
  debugLog("[LINK] " + reason);
  setPassOutput(false);
  linkSynced = false;
  visionReady = false;
  resetCycleState();
}

void sendHelloAck() {
  const String detectedModel = readModel();
  if (detectedModel.length() > 0) {
    activeModel = detectedModel;
    lastPublishedModel = detectedModel;
  }
  String payload = "HELLO_ACK|PROTO=" + String(PROTOCOL_VERSION) +
                   "|FW=" + percentEncode(FIRMWARE_VERSION) + "|READY=1";
  if (detectedModel.length() > 0) {
    payload += "|MODEL=" + percentEncode(detectedModel);
  }
  sendPayload(payload);
}

void sendTrigger() {
  sendPayload("TRIGGER|CYCLE=" + percentEncode(activeCycle) +
              "|MODEL=" + percentEncode(activeModel));
  lastTriggerSendMs = millis();
  ++triggerRetries;
}

void sendFinalResult() {
  sendPayload("FINAL_RESULT|CYCLE=" + percentEncode(activeCycle) +
              "|RESULT=" + percentEncode(finalResult));
  lastFinalSendMs = millis();
  ++finalRetries;
}

void finishVisionDecision(const String &visionResult) {
  if (visionResult == "ERROR") {
    finalResult = "ERROR";
  } else if (visionResult == "NG") {
    finalResult = "NG";
  } else if (visionResult == "OK") {
    finalResult = physicalPatternPasses(activeModel) ? "OK" : "NG";
  } else {
    finalResult = "ERROR";
  }

  setPassOutput(finalResult == "OK");
  cycleState = CycleState::WAIT_FINAL_ACK;
  finalAcked = false;
  finalRetries = 0;
  sendFinalResult();
}

void beginPhysicalCycle() {
  if (!linkSynced || !visionReady || focusBusy ||
      cycleState != CycleState::IDLE) {
    return;
  }

  const String detectedModel = readModel();
  if (detectedModel.length() == 0) {
    sendError("INVALID_MODEL_BITS", "Y0=0 Y1=0 durante trigger");
    return;
  }
  activeModel = detectedModel;
  ++cycleCounter;
  activeCycle = bootToken + "-" + String(cycleCounter);
  acceptedVisionResult = "";
  triggerAcked = false;
  triggerRetries = 0;
  visionDeadlineMs = millis() + VISION_TIMEOUT_MS;
  cycleState = CycleState::WAIT_VISION;
  sendTrigger();
}

void cancelFromQualityRelease() {
  setPassOutput(false);
  if (linkSynced && activeCycle.length() > 0) {
    sendPayload("CANCEL|CYCLE=" + percentEncode(activeCycle) +
                "|REASON=QUALITY_RELEASE");
  } else if (linkSynced) {
    sendPayload("RESET|SCOPE=CYCLE|REASON=QUALITY_RELEASE");
  }
  resetCycleState();
}

void handleProtocolMessage(const String &payload) {
  const String kind = messageKind(payload);
  if (kind.length() == 0) return;
  lastEngineContactMs = millis();

  if (kind == "HELLO") {
    const String protocol = fieldValue(payload, "PROTO");
    if (protocol != PROTOCOL_VERSION) {
      loseLink("Version de protocolo incompatible");
      sendError("INCOMPATIBLE_PROTOCOL", "ESP=1 RPI=" + protocol);
      return;
    }
    resetCycleState();
    linkSynced = true;
    visionReady = false;
    sendHelloAck();
    return;
  }

  if (!linkSynced) {
    sendError("HANDSHAKE_REQUIRED");
    return;
  }

  if (kind == "PING") {
    const String sequence = fieldValue(payload, "SEQ");
    sendPayload("PONG|SEQ=" + percentEncode(sequence));
    return;
  }

  if (kind == "READY") {
    const String state = fieldValue(payload, "STATE");
    if (state != "0" && state != "1") {
      sendAck("READY", "", "REJECTED", "INVALID_STATE");
      return;
    }
    visionReady = state == "1";
    sendAck("READY");
    return;
  }

  if (kind == "FOCUS") {
    const String state = fieldValue(payload, "STATE");
    focusBusy = state == "BUSY";
    if (focusBusy && activeCycle.length() > 0) {
      visionDeadlineMs = millis() + FOCUS_BUSY_TIMEOUT_MS;
    }
    sendAck("FOCUS", activeCycle);
    return;
  }

  if (kind == "VISION_RESULT") {
    const String cycle = fieldValue(payload, "CYCLE");
    String result = fieldValue(payload, "RESULT");
    result.toUpperCase();

    if (cycle != activeCycle || activeCycle.length() == 0) {
      sendAck("VISION_RESULT", cycle, "REJECTED", "STALE_CYCLE");
      return;
    }
    if (result != "OK" && result != "NG" && result != "ERROR") {
      sendAck("VISION_RESULT", cycle, "REJECTED", "INVALID_RESULT");
      return;
    }
    if (acceptedVisionResult.length() > 0) {
      if (acceptedVisionResult == result) {
        sendAck("VISION_RESULT", cycle);
      } else {
        sendAck("VISION_RESULT", cycle, "REJECTED", "CONFLICTING_RESULT");
      }
      return;
    }

    acceptedVisionResult = result;
    sendAck("VISION_RESULT", cycle);
    finishVisionDecision(result);
    return;
  }

  if (kind == "ACK") {
    const String type = fieldValue(payload, "TYPE");
    const String cycle = fieldValue(payload, "CYCLE");
    const String status = fieldValue(payload, "STATUS");
    if (cycle != activeCycle || status != "OK") return;
    if (type == "TRIGGER") {
      triggerAcked = true;
    } else if (type == "FINAL_RESULT") {
      finalAcked = true;
      cycleState = CycleState::HOLD_RESULT;
      if (!stableTrigger) resetCycleState();
    }
    return;
  }

  if (kind == "RESET") {
    const String cycle = activeCycle;
    resetCycleState();
    sendAck("RESET", cycle);
    return;
  }

  if (kind == "RESTART") {
    sendAck("RESTART", activeCycle);
    setPassOutput(false);
    delay(100);
    ESP.restart();
    return;
  }

  sendError("UNKNOWN_MESSAGE", kind);
}

void processSerialFrames() {
  while (Serial.available() > 0) {
    const uint8_t value = static_cast<uint8_t>(Serial.read());
    if (value == STX) {
      rxPayload = "";
      receivingFrame = true;
      discardFrame = false;
      continue;
    }
    if (value == ETX && receivingFrame) {
      receivingFrame = false;
      if (!discardFrame) handleProtocolMessage(rxPayload);
      rxPayload = "";
      discardFrame = false;
      continue;
    }
    if (!receivingFrame || discardFrame) continue;
    if (rxPayload.length() >= MAX_PAYLOAD_BYTES) {
      discardFrame = true;
      continue;
    }
    rxPayload += static_cast<char>(value);
  }
}

void updateTriggerInput() {
  const bool current = isActiveLevel(PIN_TRIGGER, TRIGGER_ACTIVE_HIGH);
  if (current != rawTrigger) {
    rawTrigger = current;
    triggerChangedMs = millis();
  }
  if (millis() - triggerChangedMs < INPUT_DEBOUNCE_MS) return;
  if (stableTrigger == rawTrigger) return;

  stableTrigger = rawTrigger;
  if (stableTrigger && !triggerLatched) {
    triggerLatched = true;
    beginPhysicalCycle();
  } else if (!stableTrigger) {
    triggerLatched = false;
    if (cycleState == CycleState::HOLD_RESULT && finalAcked) {
      resetCycleState();
    }
  }
}

void updateQualityRelease() {
  const bool current =
      isActiveLevel(PIN_QUALITY_RELEASE, QUALITY_RELEASE_ACTIVE_HIGH);
  if (current && !lastQualityRelease) cancelFromQualityRelease();
  lastQualityRelease = current;
}

void updateModelPublication() {
  if (!linkSynced || cycleState != CycleState::IDLE) return;
  const String current = readModel();
  if (current.length() == 0) return;
  activeModel = current;
  if (current != lastPublishedModel) {
    lastPublishedModel = current;
    sendPayload("MODEL|CODE=" + percentEncode(current));
  }
}

void updateCycleTimeoutsAndRetries() {
  const unsigned long now = millis();

  if (cycleState == CycleState::WAIT_VISION) {
    if (!triggerAcked && triggerRetries < MAX_TRIGGER_RETRIES &&
        now - lastTriggerSendMs >= RETRY_INTERVAL_MS) {
      sendTrigger();
    }
    if (static_cast<long>(now - visionDeadlineMs) >= 0) {
      acceptedVisionResult = "ERROR";
      finishVisionDecision("ERROR");
    }
  }

  if (cycleState == CycleState::WAIT_FINAL_ACK &&
      now - lastFinalSendMs >= RETRY_INTERVAL_MS) {
    if (finalRetries < MAX_FINAL_RETRIES) {
      sendFinalResult();
    } else {
      const String cancelledCycle = activeCycle;
      setPassOutput(false);
      sendPayload("CANCEL|CYCLE=" + percentEncode(cancelledCycle) +
                  "|REASON=FINAL_ACK_TIMEOUT");
      resetCycleState();
    }
  }
}

void setup() {
  Serial.begin(SERIAL_BAUDRATE);
  pinMode(PIN_TRIGGER, INPUT_PULLDOWN);
  pinMode(PIN_MODEL_BIT_0, INPUT);
  pinMode(PIN_MODEL_BIT_1, INPUT);
  pinMode(PIN_QUALITY_RELEASE, INPUT);
  pinMode(PIN_SENSOR_LEFT, INPUT);
  pinMode(PIN_SENSOR_RIGHT, INPUT);
  pinMode(PIN_PLC_PASS, OUTPUT);
  setPassOutput(false);

  bootToken = "WS-" + String(static_cast<uint32_t>(esp_random()), HEX);
  bootToken.toUpperCase();
  const String startupModel = readModel();
  if (startupModel.length() > 0) activeModel = startupModel;
  lastPublishedModel = startupModel;
  rawTrigger = isActiveLevel(PIN_TRIGGER, TRIGGER_ACTIVE_HIGH);
  stableTrigger = rawTrigger;
  triggerLatched = stableTrigger;
  triggerChangedMs = millis();
  lastQualityRelease =
      isActiveLevel(PIN_QUALITY_RELEASE, QUALITY_RELEASE_ACTIVE_HIGH);
}

void loop() {
  processSerialFrames();
  updateQualityRelease();
  updateTriggerInput();

  if (linkSynced && millis() - lastEngineContactMs > LINK_TIMEOUT_MS) {
    loseLink("Timeout de enlace con Raspberry");
  }

  updateModelPublication();
  updateCycleTimeoutsAndRetries();
  delay(2);
}
