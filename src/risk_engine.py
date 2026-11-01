import math

def calculate_hourly_hazards(
    hourly_data: dict, 
    hour_idx: int = 0, 
    ppe_type: str = "HighVis_Vest",
    is_acclimatized: bool = True
) -> dict:
    """
    Processes raw weather metrics into physiological and structural hazard indicators.
    """
    # Extract weather metrics for the specified hour
    temp = hourly_data["temperature_2m"][hour_idx]
    rh = hourly_data["relative_humidity_2m"][hour_idx]
    rain = hourly_data["precipitation"][hour_idx]
    gusts = hourly_data["wind_gusts_10m"][hour_idx]
    uv = hourly_data["uv_index"][hour_idx]

    # ISO 9920 Clothing/PPE Penalty Matrix (°C adjustment)
    ppe_penalties = {
        "Standard": 0.0,
        "HighVis_Vest": 2.0,
        "Tyvek_Suit": 11.0
    }
    ppe_penalty = ppe_penalties.get(ppe_type, 0.0)

    # Outdoor WBGT Approximation: 0.567*T + 0.393*e + 3.94
    # e = vapor pressure calculated from Relative Humidity and Air Temp
    e = (rh / 100) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
    base_wbgt = (0.567 * temp) + (0.393 * e) + 3.94
    effective_wbgt = base_wbgt + ppe_penalty

    # Estimated Hourly Fluid Loss Rate (Liters/Hour)
    sweat_rate_lph = round(0.4 + (effective_wbgt / 100) + (uv / 50), 2)

    # Safe Exposure Limit before Sunburn (Minutes)
    safe_sun_minutes = math.inf if uv <= 0 else round(200 / uv)

    # Evaluate Threshold Hazard Flags
    hazard_flags = []
    if effective_wbgt > 32.0:
        hazard_flags.append("CRITICAL_HEAT_STROKE_RISK")
    elif effective_wbgt > 28.0:
        hazard_flags.append("MODERATE_HEAT_STRAIN")

    if gusts > 35.0:
        hazard_flags.append("CRANE_SCAFFOLDING_SHUTDOWN")

    if rain > 4.0:
        hazard_flags.append("HEAVY_RAIN_SLIP_HAZARD")
    elif rain > 1.0:
        hazard_flags.append("LIGHT_RAIN_CAUTION")

    if uv > 8.0:
        hazard_flags.append("EXTREME_UV_BURN_RISK")

    if not is_acclimatized:
        hazard_flags.append("UNACCLIMATIZED_WORKER_CAP_20_PCT")

    return {
        "effective_wbgt_c": round(effective_wbgt, 1),
        "est_sweat_loss_lph": sweat_rate_lph,
        "safe_sun_minutes": safe_sun_minutes,
        "rain_mm": rain,
        "wind_gusts_kmh": gusts,
        "uv_index": uv,
        "hazard_flags": hazard_flags
    }