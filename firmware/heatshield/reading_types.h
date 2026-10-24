#ifndef HEATSHIELD_READING_TYPES_H
#define HEATSHIELD_READING_TYPES_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Source mode distinguishing physical hardware measurements from test fixtures.
 * Mirrors the 'source_mode' column in the backend database and API contracts.
 */
typedef enum {
    SOURCE_MODE_HARDWARE = 0,   /**< Real physical sensor measurement (hardware unconfirmed) */
    SOURCE_MODE_SIMULATED = 1   /**< Explicitly labeled test/diagnostic fixture measurement */
} ReadingSourceMode;

/**
 * @brief Hardware operational status reported by the sensor driver abstraction.
 */
typedef enum {
    SENSOR_STATUS_UNCONFIGURED = 0, /**< No physical hardware or driver configured (scaffolding stage) */
    SENSOR_STATUS_INITIALIZING = 1, /**< Hardware initializing or warming up */
    SENSOR_STATUS_OK = 2,           /**< Sensor hardware reporting operational state */
    SENSOR_STATUS_ERROR = 3,        /**< Bus read failure, checksum mismatch, or electrical fault */
    SENSOR_STATUS_DISCONNECTED = 4  /**< Sensor module absent or communication timeout */
} SensorStatus;

/**
 * @brief Quality assessment of the reading.
 * Mirrors the 'quality_status' contract in Module 2 and database schema.
 */
typedef enum {
    QUALITY_VALID = 0,   /**< Structurally sound, within plausibility bounds */
    QUALITY_SUSPECT = 1, /**< Values present but near extreme environmental extremes */
    QUALITY_INVALID = 2, /**< Sensor error, NaN, infinite, or physically implausible */
    QUALITY_MISSING = 3  /**< Measurement fields absent or sensor unconfigured */
} ReadingQuality;

/**
 * @brief Strongly typed environmental measurement record.
 * Conforms to Module 2 sensor-reading.schema.json data contract.
 *
 * NOTE: Never substitute 0.0 for missing measurements. The flags 'has_temperature'
 * and 'has_humidity' indicate presence, and 'quality' records validity.
 */
typedef struct {
    char device_code[64];           /**< Non-secret stable device identifier (e.g. HS-WS01-D001) */
    char event_id[32];              /**< Monotonically increasing per-device event ID (e.g. evt-00042) */
    uint32_t event_counter;         /**< Raw numeric event sequence counter */
    
    bool has_temperature;           /**< True if temperature measurement is present and not null */
    float temperature_c;            /**< Ambient temperature in degrees Celsius */

    bool has_humidity;              /**< True if humidity measurement is present and not null */
    float relative_humidity_pct;    /**< Relative humidity percentage (0.0 to 100.0) */

    SensorStatus sensor_status;     /**< Hardware communication status */
    ReadingQuality quality;         /**< Evaluated data quality */
    ReadingSourceMode source_mode;  /**< Hardware vs simulated test fixture */

    uint32_t uptime_ms;             /**< Local system uptime at measurement time in milliseconds */
    bool has_utc_clock;             /**< True if real-time UTC clock is synchronized (NTP/RTC) */
    char measured_at_iso8601[32];   /**< ISO 8601 UTC timestamp string (empty if unclocked) */
    char firmware_version[16];      /**< Semantic firmware version string (e.g. 0.1.0) */
} EnvironmentalReading;

/**
 * @brief Helper to initialize a reading to an explicit, safe empty/unconfigured state.
 */
static inline void init_reading_unconfigured(EnvironmentalReading* reading, const char* device_code, uint32_t counter) {
    if (!reading) return;
    
    reading->device_code[0] = '\0';
    if (device_code) {
        int i = 0;
        while (device_code[i] != '\0' && i < 63) {
            reading->device_code[i] = device_code[i];
            i++;
        }
        reading->device_code[i] = '\0';
    }

    reading->event_counter = counter;
    reading->event_id[0] = '\0';
    reading->has_temperature = false;
    reading->temperature_c = 0.0f;
    reading->has_humidity = false;
    reading->relative_humidity_pct = 0.0f;
    reading->sensor_status = SENSOR_STATUS_UNCONFIGURED;
    reading->quality = QUALITY_MISSING;
    reading->source_mode = SOURCE_MODE_HARDWARE;
    reading->uptime_ms = 0;
    reading->has_utc_clock = false;
    reading->measured_at_iso8601[0] = '\0';
    reading->firmware_version[0] = '0';
    reading->firmware_version[1] = '.';
    reading->firmware_version[2] = '1';
    reading->firmware_version[3] = '.';
    reading->firmware_version[4] = '0';
    reading->firmware_version[5] = '\0';
}

#ifdef __cplusplus
}
#endif

#endif /* HEATSHIELD_READING_TYPES_H */
