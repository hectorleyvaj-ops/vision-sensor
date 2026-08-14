#pragma once

#include <Arduino.h>

namespace WorksurfaceConfig {

// Firmware y transporte.
constexpr char FIRMWARE_VERSION[] = "worksurface-controller-1.0.0";
constexpr char PROTOCOL_VERSION[] = "1";
constexpr uint32_t SERIAL_BAUDRATE = 115200;
constexpr size_t MAX_PAYLOAD_BYTES = 512;

// Entradas y salida conservadas del gabinete Worksurface actual.
constexpr uint8_t PIN_TRIGGER = 5;
constexpr uint8_t PIN_MODEL_BIT_0 = 18;
constexpr uint8_t PIN_MODEL_BIT_1 = 19;
constexpr uint8_t PIN_QUALITY_RELEASE = 4;
constexpr uint8_t PIN_SENSOR_LEFT = 2;
constexpr uint8_t PIN_SENSOR_RIGHT = 15;
constexpr uint8_t PIN_PLC_PASS = 32;

// Polaridades. Deben comprobarse con multimetro antes del corte productivo.
constexpr bool TRIGGER_ACTIVE_HIGH = true;
constexpr bool MODEL_BITS_ACTIVE_HIGH = true;
constexpr bool QUALITY_RELEASE_ACTIVE_HIGH = true;
constexpr bool SENSOR_OK_ACTIVE_HIGH = true;
constexpr bool PLC_PASS_ACTIVE_HIGH = true;

// Mapeo esperado si bit 0 esta cableado a Y0 y bit 1 a Y1.
// Si la medicion fisica demuestra que A/B estan invertidos, intercambiar solo
// MODEL_BITS_10 y MODEL_BITS_01; no cambiar recetas ni el motor Python.
constexpr char MODEL_BITS_10[] = "A";
constexpr char MODEL_BITS_01[] = "B";
constexpr char MODEL_BITS_11[] = "C";
constexpr char DEFAULT_MODEL[] = "A";

struct SensorPattern {
  const char *model;
  bool left_ok;
  bool right_ok;
};

// Patron funcional confirmado para los tres modelos.
constexpr SensorPattern SENSOR_PATTERNS[] = {
    {"A", true, false},
    {"B", false, true},
    {"C", true, true},
};

constexpr uint32_t INPUT_DEBOUNCE_MS = 80;
constexpr uint32_t VISION_TIMEOUT_MS = 30000;
constexpr uint32_t FOCUS_BUSY_TIMEOUT_MS = 90000;
constexpr uint32_t LINK_TIMEOUT_MS = 7000;
constexpr uint32_t RETRY_INTERVAL_MS = 500;
constexpr uint8_t MAX_TRIGGER_RETRIES = 5;
constexpr uint8_t MAX_FINAL_RETRIES = 10;
constexpr uint8_t SENSOR_STABLE_SAMPLES = 5;
constexpr uint32_t SENSOR_SAMPLE_DELAY_US = 500;

// Mantener false en produccion para que solo existan tramas STX/ETX.
constexpr bool DEBUG_SERIAL_LOGS = false;

}  // namespace WorksurfaceConfig
