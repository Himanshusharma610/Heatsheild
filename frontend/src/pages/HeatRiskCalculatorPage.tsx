import React, { useState } from 'react';
import { heatRiskService } from '../services/heatRiskService';
import type { HeatIndexResult, QualityStatus } from '../features/readings/types';
import { StatusBadge } from '../components/feedback/StatusBadge';
import { LoadingState } from '../components/feedback/LoadingState';
import { ErrorState } from '../components/feedback/ErrorState';

export const HeatRiskCalculatorPage: React.FC = () => {
  const [temperature, setTemperature] = useState<string>('38.5');
  const [humidity, setHumidity] = useState<string>('65.0');
  const [quality, setQuality] = useState<QualityStatus>('valid');
  const [result, setResult] = useState<HeatIndexResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    const tempNum = parseFloat(temperature);
    const humNum = parseFloat(humidity);

    if (isNaN(tempNum) || isNaN(humNum)) {
      setError('Please provide valid numerical values for temperature and relative humidity.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await heatRiskService.calculateHeatIndex({
        temperature_c: tempNum,
        relative_humidity_pct: humNum,
        quality_status: quality,
      });
      setResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Heat index calculation failed';
      setError(message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <section style={{ marginBottom: 'var(--space-2xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--space-xs)' }}>
          <StatusBadge status="valid" label="Module 7: Explainable Engine" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>NWS Rothfusz (1990) & Steadman (1979)</span>
        </div>
        <h1>Heat-Risk Calculation Testbench</h1>
        <p style={{ fontSize: '1.05rem', maxWidth: '850px' }}>
          Interactive verification testbench connecting directly to the backend Heat-Risk Calculation API (<code style={{ color: 'var(--accent-cyan)' }}>POST /api/v1/readings/calculate-heat-index</code>).
        </p>
      </section>

      <div className="grid-2">
        {/* Input Parameters Form */}
        <section className="card">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>Environmental Inputs</h3>
          <form onSubmit={handleCalculate}>
            <div className="form-group">
              <label htmlFor="temp-input" className="form-label">
                Dry-Bulb Ambient Temperature (°C)
              </label>
              <input
                id="temp-input"
                type="number"
                step="0.1"
                min="-50"
                max="100"
                className="form-input"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                required
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Valid polynomial domain: 20.0°C to 55.0°C
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="humidity-input" className="form-label">
                Relative Humidity (% RH)
              </label>
              <input
                id="humidity-input"
                type="number"
                step="0.1"
                min="0"
                max="100"
                className="form-input"
                value={humidity}
                onChange={(e) => setHumidity(e.target.value)}
                required
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Valid bounds: 0.0% to 100.0%
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="quality-select" className="form-label">
                Upstream Quality Status Classification
              </label>
              <select
                id="quality-select"
                className="form-select"
                value={quality}
                onChange={(e) => setQuality(e.target.value as QualityStatus)}
              >
                <option value="valid">valid (Normal plausible sensor measurement)</option>
                <option value="suspect">suspect (Borderline extreme or slight clock drift)</option>
                <option value="invalid">invalid (Impossible value or hardware fault)</option>
                <option value="missing">missing (Sensor packet absent)</option>
              </select>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: 'var(--space-sm)' }} disabled={loading}>
              {loading ? 'Evaluating Model...' : 'Calculate Heat Index'}
            </button>
          </form>
        </section>

        {/* Calculation Result Panel */}
        <section className="card">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>Engine Output & Explainability</h3>

          {loading ? (
            <LoadingState message="Submitting to backend calculation engine..." />
          ) : error ? (
            <ErrorState title="Calculation Rejected" message={error} />
          ) : result ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-subtle)' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Screening Tier</span>
                  <div style={{ marginTop: '0.25rem' }}>
                    <StatusBadge status={result.informational_screening_level} />
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Apparent Heat Index</span>
                  <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--accent-amber)' }}>
                    {result.value_c !== null ? `${result.value_c} °C` : 'N/A'}
                    {result.value_f !== null && (
                      <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 500, marginLeft: '0.5rem' }}>
                        ({result.value_f} °F)
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.88rem', marginBottom: 'var(--space-md)' }}>
                <div><strong>Evaluation Status:</strong> <StatusBadge status={result.status} /></div>
                <div><strong>Method Identifier:</strong> <code>{result.method}</code> (v{result.method_version})</div>
                <div><strong>Equation Applied:</strong> <code>{result.equation_applied}</code></div>
                <div><strong>Algorithm Notes:</strong> <span style={{ color: 'var(--text-secondary)' }}>{result.notes}</span></div>
              </div>

              <div>
                <strong style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Scientific Limitations:</strong>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  {result.limitations.map((limit, idx) => (
                    <li key={idx} style={{ marginBottom: '0.25rem' }}>{limit}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 'var(--space-xl) 0', color: 'var(--text-muted)' }}>
              <p>Configure temperature and humidity parameters on the left and click <strong>Calculate Heat Index</strong> to evaluate the model.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
