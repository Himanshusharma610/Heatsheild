#ifndef HEATSHIELD_TELEMETRY_BOUNDARY_H
#define HEATSHIELD_TELEMETRY_BOUNDARY_H

#include "reading_types.h"
#include <stdbool.h>

/**
 * @file telemetry_boundary.h
 * @brief Telemetry publication boundary abstraction.
 *
 * Provides a clean interface boundary for future network telemetry transmission
 * (e.g. Wi-Fi HTTP POST, MQTT, BLE, or LoRaWAN) without binding the firmware
 * to unconfirmed radio hardware, unconfigured access points, or credentials.
 *
 * CRITICAL SECURITY & DESIGN CONSTRAINTS:
 * 1. Zero embedded credentials: No Wi-Fi SSIDs, WPA2 passkeys, or API secrets.
 * 2. Unconfigured default: Safely reports disconnected and drops outbound packets
 *    without crashing or blocking local safety evaluation.
 * 3. Does not claim offline queueing, delivery guarantees, or cloud synchronization
 *    until fully implemented and tested.
 */

#ifdef __cplusplus

/**
 * @brief Abstract interface for publishing environmental readings to an ingestion receiver.
 */
class ITelemetryPublisher {
public:
    virtual ~ITelemetryPublisher() {}

    /**
     * @brief Attempt to transmit an environmental reading to the telemetry ingest service.
     * @param reading The reading to transmit.
     * @return true if transmitted or queued, false if disconnected or failed.
     */
    virtual bool publish(const EnvironmentalReading& reading) = 0;

    /**
     * @brief Query network link / backend reachability status.
     * @return true if connected to transport network, false otherwise.
     */
    virtual bool is_connected() const = 0;

    /**
     * @brief Return human-readable publisher name.
     */
    virtual const char* get_publisher_name() const = 0;
};

/**
 * @brief Safe unconfigured telemetry publisher.
 *
 * Used while network connectivity hardware, Wi-Fi parameters, and backend URLs
 * are unconfirmed.
 */
class UnconfiguredTelemetryPublisher : public ITelemetryPublisher {
public:
    UnconfiguredTelemetryPublisher() {}

    bool publish(const EnvironmentalReading& reading) override {
        (void)reading;
        // No radio configured; telemetry safely dropped without blocking local alerts.
        return false;
    }

    bool is_connected() const override {
        return false;
    }

    const char* get_publisher_name() const override {
        return "UnconfiguredTelemetryPublisher (Network Pending Selection)";
    }
};

#endif /* __cplusplus */

#endif /* HEATSHIELD_TELEMETRY_BOUNDARY_H */
