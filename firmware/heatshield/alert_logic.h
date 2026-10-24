#ifndef HEATSHIELD_ALERT_LOGIC_H
#define HEATSHIELD_ALERT_LOGIC_H

#include "reading_types.h"
#include <stdbool.h>

/**
 * @file alert_logic.h
 * @brief Autonomous, offline-capable local safety alert evaluation engine.
 *
 * Evaluates environmental telemetry on-device to alert workers immediately,
 * without requiring active Wi-Fi, cellular, or cloud backend connectivity.
 *
 * CRITICAL SAFETY RULES:
 * 1. Missing data or unconfigured sensors MUST evaluate to ALERT_LEVEL_UNKNOWN.
 *    They must NEVER default to ALERT_LEVEL_SAFE or illuminate green indicators.
 * 2. Invalid readings (NaN, infinite, out-of-bounds, bus errors) MUST evaluate to
 *    ALERT_LEVEL_UNKNOWN.
 * 3. Thresholds defined herein are PROVISIONAL ENGINEERING PLACEHOLDERS.
 *    They DO NOT claim clinical diagnosis, heatstroke prediction, or regulatory
 *    occupational safety compliance. Formal risk calculations (e.g. WBGT/Heat Index)
 *    belong to the dedicated Risk Engine module.
 * 4. Actuator hardware (buzzers, LEDs, vibration motors) is isolated behind IAlertOutput.
 *    No unconfirmed GPIO pins are toggled.
 */

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Discrete alert states for local worker warning indicators.
 */
typedef enum {
    ALERT_LEVEL_UNKNOWN = 0, /**< Sensor unconfigured, reading missing/corrupted, or hardware fault */
    ALERT_LEVEL_SAFE    = 1, /**< Reading valid, below provisional caution threshold */
    ALERT_LEVEL_CAUTION = 2, /**< Reading valid, exceeds provisional caution threshold */
    ALERT_LEVEL_DANGER  = 3  /**< Reading valid, exceeds provisional danger threshold */
} AlertLevel;

/**
 * @brief Provisional temperature thresholds for scaffolding alert evaluation.
 *
 * WARNING: These are engineering defaults pending formal occupational risk modeling.
 */
typedef struct {
    float caution_temp_c;   /**< Provisional threshold for CAUTION level (default 35.0 C) */
    float danger_temp_c;    /**< Provisional threshold for DANGER level (default 40.0 C) */
    float hysteresis_c;     /**< Thermal deadband to prevent rapid threshold bouncing (default 0.5 C) */
} AlertThresholds;

/**
 * @brief Default provisional alert thresholds.
 */
static const AlertThresholds DEFAULT_ALERT_THRESHOLDS = {
    35.0f,  /**< caution_temp_c */
    40.0f,  /**< danger_temp_c */
     0.5f   /**< hysteresis_c */
};

/**
 * @brief Helper to convert AlertLevel to a human-readable string.
 */
static inline const char* alert_level_to_string(AlertLevel level) {
    switch (level) {
        case ALERT_LEVEL_UNKNOWN: return "UNKNOWN (Missing/Faulty Data)";
        case ALERT_LEVEL_SAFE:    return "SAFE (Below Threshold)";
        case ALERT_LEVEL_CAUTION: return "CAUTION (Elevated Heat)";
        case ALERT_LEVEL_DANGER:  return "DANGER (High Thermal Stress)";
        default:                  return "INVALID_STATE";
    }
}

#ifdef __cplusplus
}

/**
 * @brief Hardware-independent alert evaluator with stateful hysteresis support.
 */
class AlertEvaluator {
private:
    AlertLevel _current_level;
    AlertThresholds _thresholds;

public:
    AlertEvaluator(const AlertThresholds& thresholds = DEFAULT_ALERT_THRESHOLDS)
        : _current_level(ALERT_LEVEL_UNKNOWN), _thresholds(thresholds) {}

    /**
     * @brief Reset the evaluator state to ALERT_LEVEL_UNKNOWN.
     */
    void reset() {
        _current_level = ALERT_LEVEL_UNKNOWN;
    }

    /**
     * @brief Get current latched alert level.
     */
    AlertLevel get_current_level() const {
        return _current_level;
    }

    /**
     * @brief Configure alert thresholds.
     */
    void set_thresholds(const AlertThresholds& thresholds) {
        _thresholds = thresholds;
    }

    const AlertThresholds& get_thresholds() const {
        return _thresholds;
    }

    /**
     * @brief Evaluate an environmental reading and update the alert state.
     *
     * FAIL-SAFE BEHAVIOR:
     * - Any non-VALID quality or non-OK sensor status immediately sets ALERT_LEVEL_UNKNOWN.
     * - Missing temperature data immediately sets ALERT_LEVEL_UNKNOWN.
     *
     * @param reading The environmental reading to evaluate.
     * @return Resulting AlertLevel.
     */
    AlertLevel evaluate(const EnvironmentalReading& reading) {
        // Fail-safe check: invalid, corrupted, or missing data MUST NOT be treated as safe!
        if (reading.quality != QUALITY_VALID ||
            reading.sensor_status != SENSOR_STATUS_OK ||
            !reading.has_temperature) {
            _current_level = ALERT_LEVEL_UNKNOWN;
            return _current_level;
        }

        float temp = reading.temperature_c;

        switch (_current_level) {
            case ALERT_LEVEL_DANGER:
                // Falling out of DANGER requires dropping below (danger_temp - hysteresis)
                if (temp < (_thresholds.danger_temp_c - _thresholds.hysteresis_c)) {
                    if (temp >= _thresholds.caution_temp_c) {
                        _current_level = ALERT_LEVEL_CAUTION;
                    } else {
                        _current_level = ALERT_LEVEL_SAFE;
                    }
                }
                break;

            case ALERT_LEVEL_CAUTION:
                if (temp >= _thresholds.danger_temp_c) {
                    _current_level = ALERT_LEVEL_DANGER;
                } else if (temp < (_thresholds.caution_temp_c - _thresholds.hysteresis_c)) {
                    _current_level = ALERT_LEVEL_SAFE;
                }
                break;

            case ALERT_LEVEL_SAFE:
            case ALERT_LEVEL_UNKNOWN:
            default:
                if (temp >= _thresholds.danger_temp_c) {
                    _current_level = ALERT_LEVEL_DANGER;
                } else if (temp >= _thresholds.caution_temp_c) {
                    _current_level = ALERT_LEVEL_CAUTION;
                } else {
                    _current_level = ALERT_LEVEL_SAFE;
                }
                break;
        }

        return _current_level;
    }
};

/**
 * @brief Abstract actuator interface for physical alert outputs (LEDs, buzzers, vibration).
 */
class IAlertOutput {
public:
    virtual ~IAlertOutput() {}
    virtual void update(AlertLevel level) = 0;
    virtual const char* get_name() const = 0;
};

/**
 * @brief Safe no-op output implementation used while physical actuator pins are UNCONFIRMED.
 *
 * Prevents dangerous blind writes to GPIO pins before electrical schematics are reviewed.
 */
class NullAlertOutput : public IAlertOutput {
private:
    AlertLevel _last_level;

public:
    NullAlertOutput() : _last_level(ALERT_LEVEL_UNKNOWN) {}

    void update(AlertLevel level) override {
        _last_level = level;
        // No GPIO toggling until physical pins and driver circuits are confirmed.
    }

    AlertLevel get_last_level() const {
        return _last_level;
    }

    const char* get_name() const override {
        return "NullAlertOutput (Hardware Pending Selection)";
    }
};

#endif /* __cplusplus */

#endif /* HEATSHIELD_ALERT_LOGIC_H */
