# HeatShield Bharat — Heat-Risk Calculation Method & Explainability Specification

## Status
- **Method Status:** Accepted (Module 7)
- **Primary Algorithm:** National Weather Service (NWS) Heat Index Equation (Rothfusz 1990 / Steadman 1979)
- **Algorithm Version:** `1.0.0`
- **Method Identifier:** `NWS_ROTHFUSZ_1990`

---

## 1. Executive Summary & Purpose

The **HeatShield Bharat Heat-Risk Calculation Engine** calculates an environmental Heat Index from ambient dry-bulb temperature and relative humidity. Its primary purpose is **environmental screening and educational decision support** for outdoor workers and site supervisors.

### Critical Safety Declarations
1. **Heat Index is NOT Wet Bulb Globe Temperature (WBGT):**
   Temperature and relative humidity alone do not constitute WBGT. WBGT requires measuring natural wet-bulb temperature and black-globe temperature, accounting for direct solar radiant heat load and wind velocity.
2. **No Medical Diagnosis:**
   This system does NOT diagnose heatstroke, predict individual physiological thermal strain, or certify a worksite as legally compliant with occupational safety regulations.
3. **No Unapproved Standards:**
   No official Indian regulatory heat categories (e.g. from NDMA or state heat action plans) have been formally adopted into the software ruleset. Any screening categories provided are strictly provisional NOAA informational reference points.

---

## 2. Authoritative Scientific References

The calculation engine implements the published, peer-reviewed methodology developed by Robert G. Steadman and codified by the National Oceanic and Atmospheric Administration (NOAA) / National Weather Service (NWS):

1. **Steadman, R. G. (1979).** *"The assessment of sultriness. Part I: A temperature-humidity index based on human physiology and clothing science."* Journal of Applied Meteorology, 18(7), 861–873.
2. **Rothfusz, L. P. (1990).** *"The heat index equation (or, more than you ever wanted to know about heat index)."* National Oceanic and Atmospheric Administration, National Weather Service, Office of Meteorology, Technical Attachment, SR/SSD 90-23, Fort Worth, Texas.
3. **Anderson, G. B., Bell, M. L., & Peng, R. D. (2013).** *"Methods to calculate the heat index as an exposure metric in environmental health research."* Environmental Health Perspectives, 121(10), 1111–1119.

---

## 3. Mathematical Formulation

### 3.1 Unit Conversions
The NWS polynomial is calibrated in degrees Fahrenheit ($^\circ\text{F}$) and relative humidity percent ($RH$). Input temperatures in degrees Celsius ($^\circ\text{C}$) are converted internally:

$$T_F = \left(T_C \times \frac{9}{5}\right) + 32$$

$$T_C = (T_F - 32) \times \frac{5}{9}$$

All intermediate operations use double-precision floating-point arithmetic. Rounding occurs only at the final presentation layer (1 decimal place).

---

### 3.2 Step 1: Steadman's Simple Equation
For mild or borderline conditions, the algorithm first computes Steadman's simple formula:

$$HI_{\text{simple}} = 0.5 \times \left(T_F + 61.0 + \left((T_F - 68.0) \times 1.2\right) + (RH \times 0.094)\right)$$

The apparent temperature average is computed:

$$\overline{HI} = \frac{HI_{\text{simple}} + T_F}{2}$$

- **Condition:** If $\overline{HI} < 80.0^\circ\text{F}$ (approx $26.7^\circ\text{C}$):
  $$HI_F = HI_{\text{simple}}$$
  The simple value is retained and evaluation terminates without invoking the full polynomial.

---

### 3.3 Step 2: Full Rothfusz 9-Term Polynomial
If $\overline{HI} \ge 80.0^\circ\text{F}$, the full 9-term polynomial is evaluated:

$$HI_{\text{full}} = c_1 + c_2 T_F + c_3 RH + c_4 T_F RH + c_5 T_F^2 + c_6 RH^2 + c_7 T_F^2 RH + c_8 T_F RH^2 + c_9 T_F^2 RH^2$$

#### Coefficient Table

| Coefficient | Exact Value | Description |
| :--- | :--- | :--- |
| $c_1$ | `-42.379` | Base constant |
| $c_2$ | `2.04901523` | First-order temperature term |
| $c_3$ | `10.14333127` | First-order humidity term |
| $c_4$ | `-0.22475541` | Interaction cross-term ($T_F \times RH$) |
| $c_5$ | `-0.00683783` | Second-order temperature term ($T_F^2$) |
| $c_6$ | `-0.05481717` | Second-order humidity term ($RH^2$) |
| $c_7$ | `0.00122874` | Cross-term ($T_F^2 \times RH$) |
| $c_8$ | `0.00085282` | Cross-term ($T_F \times RH^2$) |
| $c_9$ | `-0.00000199` | Fourth-order cross-term ($T_F^2 \times RH^2$) |

---

### 3.4 Step 3: Low & High Humidity Adjustments

#### Low-Humidity Adjustment
Applied in hot, arid conditions typical of Northern and Western Indian summers:
- **Condition:** $RH < 13\%$ AND $80^\circ\text{F} \le T_F \le 112^\circ\text{F}$

$$\text{Adj}_{\text{low}} = \left(\frac{13 - RH}{4}\right) \times \sqrt{\frac{17 - |T_F - 95.0|}{17}}$$

$$HI_F = HI_{\text{full}} - \text{Adj}_{\text{low}}$$

#### High-Humidity Adjustment
Applied in tropical, warm, sultry conditions (coastal and monsoon regions):
- **Condition:** $RH > 85\%$ AND $80^\circ\text{F} \le T_F \le 87^\circ\text{F}$

$$\text{Adj}_{\text{high}} = \left(\frac{RH - 85}{10}\right) \times \left(\frac{87 - T_F}{5}\right)$$

$$HI_F = HI_{\text{full}} + \text{Adj}_{\text{high}}$$

#### Standard Case
If neither condition is met:

$$HI_F = HI_{\text{full}}$$

---

## 4. Operating Domain & Safety Exclusions

| Input Condition | Engine Status | Output Value | Safety Rationale |
| :--- | :--- | :--- | :--- |
| **$T_C < -50.0^\circ\text{C}$ or $T_C > 100.0^\circ\text{C}$** | `invalid_input` | `None` | Exceeds physically plausible terrestrial atmospheric range. |
| **$T_C < 20.0^\circ\text{C}$** ($< 68^\circ\text{F}$) | `out_of_domain` | `None` | Below heat-stress threshold. Heat Index cannot evaluate cold environments or windchill. |
| **$T_C > 55.0^\circ\text{C}$** ($> 131^\circ\text{F}$) | `out_of_domain` | `None` | Exceeds empirical boundary of the Rothfusz regression. Polynomial extrapolation produces mathematical artifacts. |
| **$RH < 0\%$ or $RH > 100\%$** | `invalid_input` | `None` | Physically impossible atmospheric relative humidity. |
| **$T_C$ or $RH$ is `None`** | `missing_data` | `None` | Calculation cannot occur. Never substitute zero or default values. |
| **$T_C$ or $RH$ is NaN / Inf** | `invalid_input` | `None` | Numerical corruption detected. |
| **Reading is stale (`is_stale=True` / `stale`)** | `stale` | `None` | Reading timestamp exceeds maximum freshness window; cannot evaluate real-time conditions. |
| **Reading quality is `invalid`** | `invalid_quality` | `None` | Upstream sensor communication or CRC failure. |
| **Reading quality is `suspect`** | `suspect_quality` | Evaluated | Result is returned with a mandatory audit warning note. |

---

## 5. Why Heat Index != WBGT

Occupational heat stress standards (e.g. ISO 7243, ACGIH TLVs, OSHA guidance, and National Disaster Management Authority advisories) distinguish between **Heat Index** and **Wet Bulb Globe Temperature (WBGT)**:

1. **Radiant Heat Exposure:**
   - Heat Index assumes the worker is in the **shade**.
   - Working under direct, unshaded sunlight can add **up to 8°C (15°F)** to apparent heat stress.
   - WBGT incorporates black globe temperature ($T_g$), which directly measures solar radiant heat.
2. **Air Velocity & Evaporative Cooling:**
   - Heat Index assumes a fixed light breeze of approx. **5 knots (2.5 m/s)**.
   - High humidity combined with stagnant air significantly reduces sweat evaporation; conversely, forced ventilation increases cooling. WBGT natural wet-bulb temperature ($T_{nw}$) measures actual evaporative cooling potential.
3. **Personal & Physiological Factors:**
   - Neither Heat Index nor WBGT accounts for metabolic workload (heavy lifting vs sedentary monitoring), PPE encapsulation (e.g. non-permeable coveralls), worker hydration, or individual acclimatization.

---

## 6. Provisional Informational Screening Categories & Policy Extension Point

### 6.1 Provisional NOAA Screening Categories
The project provides an optional `informational_screening_level` mapping based on NOAA public safety advisories for informational decision-support only:

| Heat Index ($^\circ\text{C}$) | Heat Index ($^\circ\text{F}$) | Screening Level | NOAA Warning Descriptor |
| :--- | :--- | :--- | :--- |
| **$< 27.0^\circ\text{C}$** | $< 80^\circ\text{F}$ | `NORMAL` | Normal conditions |
| **$27.0^\circ\text{C} - 32.2^\circ\text{C}$** | $80^\circ\text{F} - 90^\circ\text{F}$ | `CAUTION` | Fatigue possible with prolonged exposure |
| **$32.2^\circ\text{C} - 39.4^\circ\text{C}$** | $90^\circ\text{F} - 103^\circ\text{F}$ | `EXTREME_CAUTION` | Heat cramps and heat exhaustion possible |
| **$39.4^\circ\text{C} - 51.7^\circ\text{C}$** | $103^\circ\text{F} - 125^\circ\text{F}$ | `DANGER` | Heat cramps and heat exhaustion likely; heatstroke possible |
| **$\ge 51.7^\circ\text{C}$** | $\ge 125^\circ\text{F}$ | `EXTREME_DANGER` | Heatstroke highly likely |
| **Missing / Out-of-Domain / Stale** | — | `UNAVAILABLE` | Calculation cannot evaluate; never defaults to normal |

> [!WARNING]
> **UNAPPROVED STATUS:** The categories above are NOAA educational screening descriptors. They are **NOT** an officially approved occupational standard for Indian worksites. Regulatory worksite thresholds must be configured explicitly in Module 8 alert rules based on certified regional guidance.

### 6.2 Policy Extension Point
To support unapproved, emerging, or site-specific classification models without hardcoding them into the core engine, `calculate_heat_index` provides a `custom_classifier` parameter:
```python
def my_classifier(heat_index_c: float) -> str:
    if heat_index_c >= 42.0:
        return "RED_WORK_HALT"
    return "YELLOW_ADVISORY"

result = calculate_heat_index(38.0, 75.0, custom_classifier=my_classifier)
```
If the reading is invalid, missing, or stale, `custom_classification` is guaranteed to be `None`, preventing any false low-risk categorization.

---

## 7. How to Test the Calculation Service

The service contains standalone unit tests covering authoritative NOAA lookups, conversion accuracy, boundary limits, and edge cases:

```bash
# Run heat index unit and API tests:
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_heat_index.py -v
```
