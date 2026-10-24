/**
 * @file test_firmware.cpp
 * @brief Host-runnable C++ unit tests for HeatShield Bharat firmware scaffolding.
 *
 * Verifies sensor abstraction, reading validation, and fail-safe local alert logic
 * on a standard host computer without physical hardware or Arduino dependencies.
 */

#include <iostream>
#include <iomanip>
#include <cmath>
#include <cassert>
#include <string>
#include <vector>

// Include firmware components under test
#include "../heatshield/reading_types.h"
#include "../heatshield/sensor_interface.h"
#include "../heatshield/validation.h"
#include "../heatshield/alert_logic.h"
#include "../heatshield/telemetry_boundary.h"

// Test framework macros
static int g_tests_run = 0;
static int g_tests_passed = 0;
static int g_tests_failed = 0;

#define RUN_TEST(fn) do { \
    g_tests_run++; \
    std::cout << "[ RUN      ] " << #fn << "..." << std::flush; \
    try { \
        fn(); \
        g_tests_passed++; \
        std::cout << " [PASS]" << std::endl; \
    } catch (const std::exception& e) { \
        g_tests_failed++; \
        std::cout << " [FAIL] Exception: " << e.what() << std::endl; \
    } catch (...) { \
        g_tests_failed++; \
        std::cout << " [FAIL] Unknown exception" << std::endl; \
    } \
} while(0)

#define ASSERT_TRUE(condition) do { \
    if (!(condition)) { \
        throw std::runtime_error("Assertion failed: " #condition " at line " + std::to_string(__LINE__)); \
    } \
} while(0)

#define ASSERT_FALSE(condition) do { \
    if (condition) { \
        throw std::runtime_error("Assertion failed: NOT " #condition " at line " + std::to_string(__LINE__)); \
    } \
} while(0)

#define ASSERT_EQ(actual, expected) do { \
    if ((actual) != (expected)) { \
        throw std::runtime_error("Assertion failed: " #actual " (" + std::to_string(actual) + ") != " #expected " (" + std::to_string(expected) + ") at line " + std::to_string(__LINE__)); \
    } \
} while(0)

// ============================================================================
// Test Group 1: Sensor Abstraction & Unconfigured Adapter
// ============================================================================

void test_unconfigured_sensor_fails_safe() {
    UnconfiguredSensor sensor;
    ASSERT_EQ(sensor.get_status(), SENSOR_STATUS_UNCONFIGURED);

    // Initialization MUST return false
    bool begin_result = sensor.begin();
    ASSERT_FALSE(begin_result);
    ASSERT_EQ(sensor.get_status(), SENSOR_STATUS_UNCONFIGURED);

    // Read MUST return false and report missing data
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    bool read_result = sensor.read(reading);

    ASSERT_FALSE(read_result);
    ASSERT_FALSE(reading.has_temperature);
    ASSERT_FALSE(reading.has_humidity);
    ASSERT_EQ(reading.sensor_status, SENSOR_STATUS_UNCONFIGURED);
    ASSERT_EQ(reading.quality, QUALITY_MISSING);
    ASSERT_EQ(reading.source_mode, SOURCE_MODE_HARDWARE);
}

void test_diagnostic_simulated_sensor_flags_source_mode() {
    DiagnosticSimulatedSensor sim_sensor(true, 32.5f, true, 65.0f, SENSOR_STATUS_OK);
    ASSERT_TRUE(sim_sensor.begin());
    ASSERT_EQ(sim_sensor.get_status(), SENSOR_STATUS_OK);

    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-SIM-001", 1);
    bool read_result = sim_sensor.read(reading);

    ASSERT_TRUE(read_result);
    ASSERT_TRUE(reading.has_temperature);
    ASSERT_EQ(reading.temperature_c, 32.5f);
    ASSERT_TRUE(reading.has_humidity);
    ASSERT_EQ(reading.relative_humidity_pct, 65.0f);
    // CRITICAL: Simulated readings MUST be explicitly marked SOURCE_MODE_SIMULATED
    ASSERT_EQ(reading.source_mode, SOURCE_MODE_SIMULATED);
}

// ============================================================================
// Test Group 2: Environmental Reading Validation
// ============================================================================

void test_validation_valid_reading() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = 28.5f;
    reading.has_humidity = true;
    reading.relative_humidity_pct = 55.0f;
    reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_TRUE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_VALID);
    ASSERT_EQ(res.error_flags, VAL_ERR_NONE);
    ASSERT_EQ(reading.quality, QUALITY_VALID);
}

void test_validation_missing_temperature() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = false;
    reading.temperature_c = 0.0f; // Note: 0.0 must not be treated as valid
    reading.has_humidity = true;
    reading.relative_humidity_pct = 50.0f;
    reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_MISSING);
    ASSERT_TRUE((res.error_flags & VAL_ERR_MISSING_TEMP) != 0);
}

void test_validation_missing_humidity() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = 30.0f;
    reading.has_humidity = false;
    reading.relative_humidity_pct = 0.0f;
    reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_MISSING);
    ASSERT_TRUE((res.error_flags & VAL_ERR_MISSING_HUM) != 0);
}

void test_validation_non_finite_nan() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = std::numeric_limits<float>::quiet_NaN();
    reading.has_humidity = true;
    reading.relative_humidity_pct = 50.0f;
    reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_INVALID);
    ASSERT_TRUE((res.error_flags & VAL_ERR_NON_FINITE_TEMP) != 0);
}

void test_validation_non_finite_infinity() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = 25.0f;
    reading.has_humidity = true;
    reading.relative_humidity_pct = std::numeric_limits<float>::infinity();
    reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_INVALID);
    ASSERT_TRUE((res.error_flags & VAL_ERR_NON_FINITE_HUM) != 0);
}

void test_validation_out_of_bounds_temperature() {
    // Extreme subzero below plausibility bound (-20.0 C)
    EnvironmentalReading cold_reading;
    init_reading_unconfigured(&cold_reading, "HS-TEST-001", 1);
    cold_reading.has_temperature = true;
    cold_reading.temperature_c = -40.0f;
    cold_reading.has_humidity = true;
    cold_reading.relative_humidity_pct = 40.0f;
    cold_reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res1 = validate_reading(&cold_reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res1.is_valid);
    ASSERT_EQ(res1.quality, QUALITY_INVALID);
    ASSERT_TRUE((res1.error_flags & VAL_ERR_TEMP_OUT_OF_BOUNDS) != 0);

    // Extreme heat above plausibility bound (70.0 C)
    EnvironmentalReading hot_reading;
    init_reading_unconfigured(&hot_reading, "HS-TEST-001", 2);
    hot_reading.has_temperature = true;
    hot_reading.temperature_c = 85.0f;
    hot_reading.has_humidity = true;
    hot_reading.relative_humidity_pct = 40.0f;
    hot_reading.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res2 = validate_reading(&hot_reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res2.is_valid);
    ASSERT_EQ(res2.quality, QUALITY_INVALID);
    ASSERT_TRUE((res2.error_flags & VAL_ERR_TEMP_OUT_OF_BOUNDS) != 0);
}

void test_validation_out_of_bounds_humidity() {
    // Negative humidity (< 0.0%)
    EnvironmentalReading neg_hum;
    init_reading_unconfigured(&neg_hum, "HS-TEST-001", 1);
    neg_hum.has_temperature = true;
    neg_hum.temperature_c = 25.0f;
    neg_hum.has_humidity = true;
    neg_hum.relative_humidity_pct = -5.0f;
    neg_hum.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res1 = validate_reading(&neg_hum, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res1.is_valid);
    ASSERT_EQ(res1.quality, QUALITY_INVALID);
    ASSERT_TRUE((res1.error_flags & VAL_ERR_HUM_OUT_OF_BOUNDS) != 0);

    // Humidity exceeding 100%
    EnvironmentalReading over_hum;
    init_reading_unconfigured(&over_hum, "HS-TEST-001", 2);
    over_hum.has_temperature = true;
    over_hum.temperature_c = 25.0f;
    over_hum.has_humidity = true;
    over_hum.relative_humidity_pct = 105.0f;
    over_hum.sensor_status = SENSOR_STATUS_OK;

    ValidationResult res2 = validate_reading(&over_hum, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res2.is_valid);
    ASSERT_EQ(res2.quality, QUALITY_INVALID);
    ASSERT_TRUE((res2.error_flags & VAL_ERR_HUM_OUT_OF_BOUNDS) != 0);
}

void test_validation_failed_sensor_status() {
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = 25.0f;
    reading.has_humidity = true;
    reading.relative_humidity_pct = 50.0f;
    reading.sensor_status = SENSOR_STATUS_ERROR; // Bus error / parity fault

    ValidationResult res = validate_reading(&reading, &DEFAULT_PLAUSIBILITY_BOUNDS);
    ASSERT_FALSE(res.is_valid);
    ASSERT_EQ(res.quality, QUALITY_INVALID);
    ASSERT_TRUE((res.error_flags & VAL_ERR_SENSOR_FAILED) != 0);
}

// ============================================================================
// Test Group 3: Local Alert Logic & Fail-Safe Unknown State
// ============================================================================

void test_alert_missing_data_evaluates_unknown() {
    AlertEvaluator evaluator;
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = false;
    reading.quality = QUALITY_MISSING;
    reading.sensor_status = SENSOR_STATUS_UNCONFIGURED;

    AlertLevel level = evaluator.evaluate(reading);
    // CRITICAL REQUIREMENT: Missing data must NOT evaluate to SAFE (green)!
    ASSERT_EQ(level, ALERT_LEVEL_UNKNOWN);
    ASSERT_EQ(evaluator.get_current_level(), ALERT_LEVEL_UNKNOWN);
}

void test_alert_invalid_reading_evaluates_unknown() {
    AlertEvaluator evaluator;
    EnvironmentalReading reading;
    init_reading_unconfigured(&reading, "HS-TEST-001", 1);
    reading.has_temperature = true;
    reading.temperature_c = 45.0f;
    reading.has_humidity = true;
    reading.relative_humidity_pct = 60.0f;
    reading.quality = QUALITY_INVALID; // Quality marked invalid (e.g. NaN or bus failure)
    reading.sensor_status = SENSOR_STATUS_ERROR;

    AlertLevel level = evaluator.evaluate(reading);
    // CRITICAL: Invalid reading must never trigger SAFE!
    ASSERT_EQ(level, ALERT_LEVEL_UNKNOWN);
}

void test_alert_threshold_levels() {
    AlertThresholds thresholds = { 35.0f, 40.0f, 0.5f };
    AlertEvaluator evaluator(thresholds);

    // 1. Below caution -> SAFE
    EnvironmentalReading safe_reading;
    init_reading_unconfigured(&safe_reading, "HS-TEST-001", 1);
    safe_reading.has_temperature = true;
    safe_reading.temperature_c = 30.0f;
    safe_reading.has_humidity = true;
    safe_reading.relative_humidity_pct = 50.0f;
    safe_reading.quality = QUALITY_VALID;
    safe_reading.sensor_status = SENSOR_STATUS_OK;

    ASSERT_EQ(evaluator.evaluate(safe_reading), ALERT_LEVEL_SAFE);

    // 2. Crossing caution -> CAUTION
    EnvironmentalReading caution_reading = safe_reading;
    caution_reading.temperature_c = 36.0f;
    ASSERT_EQ(evaluator.evaluate(caution_reading), ALERT_LEVEL_CAUTION);

    // 3. Crossing danger -> DANGER
    EnvironmentalReading danger_reading = safe_reading;
    danger_reading.temperature_c = 41.5f;
    ASSERT_EQ(evaluator.evaluate(danger_reading), ALERT_LEVEL_DANGER);
}

void test_alert_hysteresis() {
    AlertThresholds thresholds = { 35.0f, 40.0f, 1.0f }; // 1.0 C hysteresis deadband
    AlertEvaluator evaluator(thresholds);

    EnvironmentalReading r;
    init_reading_unconfigured(&r, "HS-TEST-001", 1);
    r.has_temperature = true;
    r.has_humidity = true;
    r.relative_humidity_pct = 50.0f;
    r.quality = QUALITY_VALID;
    r.sensor_status = SENSOR_STATUS_OK;

    // Push into DANGER (>= 40.0 C)
    r.temperature_c = 40.5f;
    ASSERT_EQ(evaluator.evaluate(r), ALERT_LEVEL_DANGER);

    // Drop to 39.5 C: With 1.0 C hysteresis, danger boundary is 40.0 - 1.0 = 39.0 C.
    // 39.5 C is >= 39.0 C, so it MUST stay in DANGER!
    r.temperature_c = 39.5f;
    ASSERT_EQ(evaluator.evaluate(r), ALERT_LEVEL_DANGER);

    // Drop to 38.5 C: < 39.0 C, so drops to CAUTION (>= 35.0 C)
    r.temperature_c = 38.5f;
    ASSERT_EQ(evaluator.evaluate(r), ALERT_LEVEL_CAUTION);

    // Drop to 34.5 C: With 1.0 C hysteresis, caution boundary is 35.0 - 1.0 = 34.0 C.
    // 34.5 C is >= 34.0 C, so it MUST stay in CAUTION!
    r.temperature_c = 34.5f;
    ASSERT_EQ(evaluator.evaluate(r), ALERT_LEVEL_CAUTION);

    // Drop to 33.5 C: < 34.0 C, so drops to SAFE
    r.temperature_c = 33.5f;
    ASSERT_EQ(evaluator.evaluate(r), ALERT_LEVEL_SAFE);
}

// ============================================================================
// Test Group 4: Actuator and Telemetry Decoupling
// ============================================================================

void test_actuator_null_output() {
    NullAlertOutput output;
    ASSERT_EQ(output.get_last_level(), ALERT_LEVEL_UNKNOWN);
    output.update(ALERT_LEVEL_DANGER);
    ASSERT_EQ(output.get_last_level(), ALERT_LEVEL_DANGER);
}

void test_telemetry_unconfigured_publisher() {
    UnconfiguredTelemetryPublisher pub;
    ASSERT_FALSE(pub.is_connected());

    EnvironmentalReading r;
    init_reading_unconfigured(&r, "HS-TEST-001", 1);
    ASSERT_FALSE(pub.publish(r)); // Fails safely without errors
}

// ============================================================================
// Main Test Runner
// ============================================================================

int main() {
    std::cout << "================================================================" << std::endl;
    std::cout << " HeatShield Bharat — Module 5 Firmware Scaffolding Test Suite" << std::endl;
    std::cout << " Host C++ Unit Tests (Hardware-Independent Verification)" << std::endl;
    std::cout << "================================================================" << std::endl;

    RUN_TEST(test_unconfigured_sensor_fails_safe);
    RUN_TEST(test_diagnostic_simulated_sensor_flags_source_mode);
    RUN_TEST(test_validation_valid_reading);
    RUN_TEST(test_validation_missing_temperature);
    RUN_TEST(test_validation_missing_humidity);
    RUN_TEST(test_validation_non_finite_nan);
    RUN_TEST(test_validation_non_finite_infinity);
    RUN_TEST(test_validation_out_of_bounds_temperature);
    RUN_TEST(test_validation_out_of_bounds_humidity);
    RUN_TEST(test_validation_failed_sensor_status);
    RUN_TEST(test_alert_missing_data_evaluates_unknown);
    RUN_TEST(test_alert_invalid_reading_evaluates_unknown);
    RUN_TEST(test_alert_threshold_levels);
    RUN_TEST(test_alert_hysteresis);
    RUN_TEST(test_actuator_null_output);
    RUN_TEST(test_telemetry_unconfigured_publisher);

    std::cout << "----------------------------------------------------------------" << std::endl;
    std::cout << "Test Summary: " << g_tests_passed << "/" << g_tests_run << " passed ("
              << g_tests_failed << " failed)" << std::endl;
    std::cout << "================================================================" << std::endl;

    return (g_tests_failed == 0) ? 0 : 1;
}
