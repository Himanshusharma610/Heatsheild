#ifndef HEATSHIELD_SENSOR_INTERFACE_H
#define HEATSHIELD_SENSOR_INTERFACE_H

#include "reading_types.h"

/**
 * @file sensor_interface.h
 * @brief Hardware Abstraction Layer (HAL) for environmental temperature & humidity sensors.
 *
 * This abstraction decouples hardware-dependent communications (I2C registers, OneWire timing,
 * pin assignments, sensor-specific libraries) from data validation, alert evaluation, and telemetry.
 *
 * All hardware parameters (GPIOs, I2C addresses, bus speeds) remain UNCONFIRMED until physical
 * devices are selected.
 */

#ifdef __cplusplus

/**
 * @brief Abstract sensor interface.
 *
 * Implementations of this interface will wrap concrete physical sensor libraries
 * (e.g. SHT31, BME280, DHT22) once hardware is procured.
 */
class ISensor {
public:
    virtual ~ISensor() {}

    /**
     * @brief Initialize communication bus and physical sensor registers.
     * @return true if hardware handshake succeeds, false on bus error or missing hardware.
     */
    virtual bool begin() = 0;

    /**
     * @brief Poll physical sensor for latest temperature and humidity values.
     * @param reading Reference to EnvironmentalReading struct to populate.
     * @return true if communication succeeded and values were populated, false on bus/checksum error.
     */
    virtual bool read(EnvironmentalReading& reading) = 0;

    /**
     * @brief Retrieve operational status of the sensor.
     * @return Current SensorStatus enum value.
     */
    virtual SensorStatus get_status() const = 0;

    /**
     * @brief Return driver name and hardware status.
     * @return Constant string descriptor.
     */
    virtual const char* get_driver_name() const = 0;
};

/**
 * @brief Default safe adapter used when no physical sensor hardware is confirmed or connected.
 *
 * CRITICAL SAFETY BEHAVIOR:
 * - Does NOT claim hardware initialization succeeded.
 * - Does NOT fabricate simulated readings as physical measurements.
 * - Explicitly populates readings with QUALITY_MISSING and SENSOR_STATUS_UNCONFIGURED.
 * - Prevents the local alert engine from assuming conditions are safe when sensors are absent.
 */
class UnconfiguredSensor : public ISensor {
private:
    SensorStatus _status;

public:
    UnconfiguredSensor() : _status(SENSOR_STATUS_UNCONFIGURED) {}

    bool begin() override {
        // Physical hardware is unselected. Initialization fails safely by design.
        _status = SENSOR_STATUS_UNCONFIGURED;
        return false;
    }

    bool read(EnvironmentalReading& reading) override {
        reading.has_temperature = false;
        reading.temperature_c = 0.0f;
        reading.has_humidity = false;
        reading.relative_humidity_pct = 0.0f;
        reading.sensor_status = SENSOR_STATUS_UNCONFIGURED;
        reading.quality = QUALITY_MISSING;
        reading.source_mode = SOURCE_MODE_HARDWARE;
        _status = SENSOR_STATUS_UNCONFIGURED;
        return false;
    }

    SensorStatus get_status() const override {
        return _status;
    }

    const char* get_driver_name() const override {
        return "UnconfiguredSensor (Hardware Pending Selection)";
    }
};

/**
 * @brief Diagnostic test fixture sensor for host unit testing and pipeline verification.
 *
 * CRITICAL SAFETY BEHAVIOR:
 * - Explicitly tags all readings with SOURCE_MODE_SIMULATED.
 * - Under no circumstances can simulated readings masquerade as SOURCE_MODE_HARDWARE.
 */
class DiagnosticSimulatedSensor : public ISensor {
private:
    SensorStatus _status;
    bool _has_temp;
    float _temp_c;
    bool _has_hum;
    float _hum_pct;

public:
    DiagnosticSimulatedSensor(bool has_temp = true, float temp_c = 25.0f,
                              bool has_hum = true, float hum_pct = 50.0f,
                              SensorStatus status = SENSOR_STATUS_OK)
        : _status(status), _has_temp(has_temp), _temp_c(temp_c),
          _has_hum(has_hum), _hum_pct(hum_pct) {}

    void set_values(bool has_temp, float temp_c, bool has_hum, float hum_pct, SensorStatus status = SENSOR_STATUS_OK) {
        _has_temp = has_temp;
        _temp_c = temp_c;
        _has_hum = has_hum;
        _hum_pct = hum_pct;
        _status = status;
    }

    bool begin() override {
        return (_status == SENSOR_STATUS_OK);
    }

    bool read(EnvironmentalReading& reading) override {
        reading.has_temperature = _has_temp;
        reading.temperature_c = _temp_c;
        reading.has_humidity = _has_hum;
        reading.relative_humidity_pct = _hum_pct;
        reading.sensor_status = _status;
        reading.source_mode = SOURCE_MODE_SIMULATED; // Explicitly simulated!
        return (_status == SENSOR_STATUS_OK);
    }

    SensorStatus get_status() const override {
        return _status;
    }

    const char* get_driver_name() const override {
        return "DiagnosticSimulatedSensor (Host Testing / Simulation Only)";
    }
};

#endif /* __cplusplus */

#endif /* HEATSHIELD_SENSOR_INTERFACE_H */
