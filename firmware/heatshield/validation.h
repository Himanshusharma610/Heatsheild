#ifndef HEATSHIELD_VALIDATION_H
#define HEATSHIELD_VALIDATION_H

#include "reading_types.h"
#include <math.h>
#include <stdbool.h>
#include <stdint.h>

/**
 * @file validation.h
 * @brief Hardware-independent environmental reading validation engine.
 *
 * Checks physical plausibility, numerical sanity (NaN/Inf), presence of required
 * measurements, and sensor communication status.
 *
 * IMPORTANT SAFETY PRINCIPLES:
 * 1. Physical plausibility != calibration accuracy. Passing this validation confirms
 *    that data is structurally reasonable and not corrupted bus noise, but does not
 *    guarantee instrument accuracy.
 * 2. Invalid or missing readings MUST NEVER be silently clamped or substituted with 0.0.
 *    Original invalid values are preserved for auditing, and quality is marked INVALID or MISSING.
 * 3. Final plausibility bounds and sampling behavior must be reviewed against official
 *    sensor datasheets once physical hardware is procured.
 */

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Configurable bounds for physical atmospheric plausibility.
 *
 * Default bounds reflect realistic outdoor and industrial microclimates in India:
 * - Temperature: -20.0 deg C to +70.0 deg C (surfaces/ambient in extreme summer).
 * - Relative humidity: 0.0% to 100.0%.
 */
typedef struct {
    float min_temperature_c;
    float max_temperature_c;
    float min_humidity_pct;
    float max_humidity_pct;
    uint32_t max_acceptable_age_ms; /**< Max allowable reading age in milliseconds (0 = disabled) */
} PlausibilityBounds;

/**
 * @brief Default plausibility bounds for standard atmospheric monitoring.
 */
static const PlausibilityBounds DEFAULT_PLAUSIBILITY_BOUNDS = {
    -20.0f,  /**< min_temperature_c */
     70.0f,  /**< max_temperature_c */
      0.0f,  /**< min_humidity_pct */
    100.0f,  /**< max_humidity_pct */
    60000    /**< max_acceptable_age_ms: 60 seconds */
};

/**
 * @brief Bitmask error flags identifying specific validation failures.
 */
typedef enum {
    VAL_ERR_NONE                = 0,
    VAL_ERR_SENSOR_FAILED       = 1 << 0, /**< Sensor driver reported error, disconnected, or unconfigured */
    VAL_ERR_MISSING_TEMP        = 1 << 1, /**< Temperature field absent */
    VAL_ERR_MISSING_HUM         = 1 << 2, /**< Humidity field absent */
    VAL_ERR_NON_FINITE_TEMP     = 1 << 3, /**< Temperature is NaN or Infinite */
    VAL_ERR_NON_FINITE_HUM      = 1 << 4, /**< Humidity is NaN or Infinite */
    VAL_ERR_TEMP_OUT_OF_BOUNDS  = 1 << 5, /**< Temperature exceeds min/max plausibility */
    VAL_ERR_HUM_OUT_OF_BOUNDS   = 1 << 6, /**< Relative humidity outside 0-100% plausibility */
    VAL_ERR_STALE_READING       = 1 << 7  /**< Reading timestamp or age exceeds acceptable window */
} ValidationErrorFlags;

/**
 * @brief Comprehensive validation outcome report.
 */
typedef struct {
    bool is_valid;              /**< True if completely valid and within bounds */
    ReadingQuality quality;     /**< Evaluated quality classification */
    uint32_t error_flags;       /**< Bitmask of ValidationErrorFlags */
} ValidationResult;

/**
 * @brief Validates an environmental reading against plausibility bounds.
 *
 * Updates the reading's internal `quality` field to reflect the outcome.
 * Raw values are NEVER modified or clamped.
 *
 * @param reading Pointer to the reading struct to validate.
 * @param bounds Pointer to plausibility criteria (or NULL for default).
 * @return ValidationResult containing status and detailed failure flags.
 */
static inline ValidationResult validate_reading(EnvironmentalReading* reading, const PlausibilityBounds* bounds) {
    ValidationResult result;
    result.is_valid = true;
    result.error_flags = VAL_ERR_NONE;
    result.quality = QUALITY_VALID;

    if (!reading) {
        result.is_valid = false;
        result.error_flags = VAL_ERR_SENSOR_FAILED;
        result.quality = QUALITY_INVALID;
        return result;
    }

    const PlausibilityBounds* b = bounds ? bounds : &DEFAULT_PLAUSIBILITY_BOUNDS;

    // 1. Sensor hardware communication status
    if (reading->sensor_status != SENSOR_STATUS_OK) {
        result.is_valid = false;
        result.error_flags |= VAL_ERR_SENSOR_FAILED;
        if (reading->sensor_status == SENSOR_STATUS_UNCONFIGURED) {
            result.quality = QUALITY_MISSING;
        } else {
            result.quality = QUALITY_INVALID;
        }
    }

    // 2. Temperature presence check
    if (!reading->has_temperature) {
        result.is_valid = false;
        result.error_flags |= VAL_ERR_MISSING_TEMP;
        if (result.quality != QUALITY_INVALID) {
            result.quality = QUALITY_MISSING;
        }
    } else {
        // Numerical sanity: NaN / Infinity
        if (isnan(reading->temperature_c) || isinf(reading->temperature_c)) {
            result.is_valid = false;
            result.error_flags |= VAL_ERR_NON_FINITE_TEMP;
            result.quality = QUALITY_INVALID;
        } else {
            // Physical plausibility bounds
            if (reading->temperature_c < b->min_temperature_c || reading->temperature_c > b->max_temperature_c) {
                result.is_valid = false;
                result.error_flags |= VAL_ERR_TEMP_OUT_OF_BOUNDS;
                result.quality = QUALITY_INVALID;
            }
        }
    }

    // 3. Humidity presence check
    if (!reading->has_humidity) {
        result.is_valid = false;
        result.error_flags |= VAL_ERR_MISSING_HUM;
        if (result.quality != QUALITY_INVALID) {
            result.quality = QUALITY_MISSING;
        }
    } else {
        // Numerical sanity: NaN / Infinity
        if (isnan(reading->relative_humidity_pct) || isinf(reading->relative_humidity_pct)) {
            result.is_valid = false;
            result.error_flags |= VAL_ERR_NON_FINITE_HUM;
            result.quality = QUALITY_INVALID;
        } else {
            // Physical plausibility bounds
            if (reading->relative_humidity_pct < b->min_humidity_pct || reading->relative_humidity_pct > b->max_humidity_pct) {
                result.is_valid = false;
                result.error_flags |= VAL_ERR_HUM_OUT_OF_BOUNDS;
                result.quality = QUALITY_INVALID;
            }
        }
    }

    // Synchronize the reading's internal quality tag with the evaluation
    reading->quality = result.quality;

    return result;
}

#ifdef __cplusplus
}
#endif

#endif /* HEATSHIELD_VALIDATION_H */
