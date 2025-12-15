# main.py  -- A-PLUS 完整版
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Models
# -------------------------
class RequestData(BaseModel):
    battery_level: float
    charger_power: float
    target_time: str            # "HH:MM"
    cheap_mode: bool = False
    target_soc: float = 80.0

class TimelinePoint(BaseModel):
    rel_time: str   # "+0.25h"
    abs_time: str   # "HH:MM"
    soc: float

class PredictResponse(BaseModel):
    hours: float
    final_battery: float
    timeline: List[TimelinePoint]
    start_time: str         # "HH:MM" charging start (absolute)
    end_time: str           # "HH:MM" charging end (absolute)
    cost_now: float
    cost_optimized: float
    savings: float
    meets_departure: bool
    night_tariff_applied: bool
    info: Optional[str] = None

# -------------------------
# Constants & config
# -------------------------
LOW_PRICE = 0.20
HIGH_PRICE = 0.40
BATTERY_CAPACITY_KWH = 50.0
SLOT_INTERVAL = 0.25            # hours (15 min) — used to build slots sequence
SIM_SUB_INTERVAL = 5 / 60.0     # hours (5 min) — simulation substep
MAX_SCAN_HOURS = 48.0           # safety cap to avoid infinite loops
MAX_SIM_STEPS = 2000            # safety cap for simulation steps

# -------------------------
# Helpers
# -------------------------
def is_low_price(dt: datetime) -> bool:
    # Low price windows: weekends OR 22:00 - 02:00 (cross-midnight)
    if dt.weekday() >= 5:
        return True
    t = dt.time()
    return (t >= time(22, 0)) or (t < time(2, 0))

def taper_factor(soc: float) -> float:
    # taper model (same for normal and optimized)
    if soc < 80.0:
        return 1.0
    if soc < 90.0:
        return 0.5
    return 0.2

def fmt_hm(dt: datetime) -> str:
    return dt.strftime("%H:%M")

# simulate immediate charging starting at `start_dt` until required_kwh or until we hit end_dt (optional cutoff)
# returns timeline points (rel/abs/soc), total_hours, final_soc, cost, completed_flag
def simulate_from_start(
    current_soc: float,
    charger_kw: float,
    required_kwh: float,
    start_dt: datetime,
    cutoff_dt: Optional[datetime] = None
):
    soc = current_soc
    charged_total = 0.0
    elapsed = 0.0
    cost = 0.0
    timeline: List[Dict[str, Any]] = []

    steps = 0
    while charged_total + 1e-9 < required_kwh and soc < 100.0 and steps < MAX_SIM_STEPS:
        factor = taper_factor(soc)
        can_charge = charger_kw * SIM_SUB_INTERVAL * factor
        charge_now = min(can_charge, required_kwh - charged_total)

        # Determine duration of this sub-interval
        if charger_kw * factor > 0:
            partial_hours = charge_now / (charger_kw * factor)
        else:
            partial_hours = SIM_SUB_INTERVAL

        charged_total += charge_now
        soc += (charge_now / BATTERY_CAPACITY_KWH) * 100.0
        soc = min(100.0, soc)
        elapsed += partial_hours

        point_dt = start_dt + timedelta(hours=elapsed)

        # cutoff rule
        if cutoff_dt is not None and point_dt > cutoff_dt:
            break

        # correct dynamic pricing for normal charging
        if is_low_price(point_dt):
            cost += charge_now * LOW_PRICE
        else:
            cost += charge_now * HIGH_PRICE

        timeline.append({
            "rel_time": f"+{elapsed:.2f}h",
            "abs_time": fmt_hm(point_dt),
            "soc": round(soc, 1)
        })

        steps += 1

    completed = charged_total + 1e-9 >= required_kwh
    return {
        "timeline": timeline,
        "hours": round(elapsed, 2),
        "final_soc": round(soc, 1),
        "cost": round(cost, 2),
        "completed": completed
    }


# Evaluate charging plan that starts at a given slot index: greedily fill each slot (using sub-intervals),
# respecting taper and slot time length, stopping once required_kwh satisfied or departure reached.
def evaluate_start_index(
    current_soc: float,
    charger_kw: float,
    required_kwh: float,
    slots: List[Dict[str, Any]],
    start_idx: int,
    slot_interval_hours: float,
    sim_sub_interval: float,
    departure_dt: datetime
) -> Dict[str, Any]:
    soc = current_soc
    required_remaining = required_kwh
    timeline: List[Dict[str, Any]] = []
    elapsed_from_start = 0.0
    cost = 0.0
    steps = 0

    charging_start_dt = slots[start_idx]["time"]

    n = len(slots)
    for i in range(start_idx, n):
        slot = slots[i]
        slot_dt = slot["time"]
        slot_price = slot["price"]

        # simulate within this slot using sim_sub_interval slices
        slot_time_consumed = 0.0
        max_substeps = int(slot_interval_hours / sim_sub_interval) + 2
        sub = 0
        while required_remaining > 1e-9 and sub < max_substeps and steps < MAX_SIM_STEPS:
            # compute taper
            factor = taper_factor(soc)
            can_sub = charger_kw * sim_sub_interval * factor
            charge_now = min(can_sub, required_remaining)
            if charger_kw * factor > 0:
                dh = charge_now / (charger_kw * factor)
            else:
                dh = sim_sub_interval

            # if charging over this substep would pass departure cutoff -> stop and return incomplete
            point_abs_time = charging_start_dt + timedelta(hours=elapsed_from_start + dh)
            if point_abs_time > departure_dt:
                # cannot finish in this slot before departure; stop here and return incomplete plan
                return {
                    "timeline": timeline,
                    "hours": round(elapsed_from_start, 2),
                    "final_soc": round(soc, 1),
                    "cost": round(cost, 2),
                    "completed": False,
                    "start_dt": charging_start_dt
                }

            # apply
            required_remaining -= charge_now
            elapsed_from_start += dh
            soc += (charge_now / BATTERY_CAPACITY_KWH) * 100.0
            soc = min(100.0, soc)
            cost += charge_now * slot_price

            abs_time = charging_start_dt + timedelta(hours=elapsed_from_start)
            timeline.append({
                "rel_time": f"+{elapsed_from_start:.2f}h",
                "abs_time": fmt_hm(abs_time),
                "soc": round(soc, 1)
            })

            sub += 1
            steps += 1

            # if we've satisfied required -> break
            if required_remaining <= 1e-9:
                break

    # after iterating scheduled slots, if required_remaining still > 0 => did not complete before departure
    completed = required_remaining <= 1e-9
    return {
        "timeline": timeline,
        "hours": round(elapsed_from_start, 2),
        "final_soc": round(soc, 1),
        "cost": round(cost, 2),
        "completed": completed,
        "start_dt": charging_start_dt
    }

# -------------------------
# Endpoint
# -------------------------
@app.post("/predict", response_model=PredictResponse)
def predict(data: RequestData):
    now = datetime.now()

    # parse departure
    try:
        dep_h, dep_m = map(int, data.target_time.split(":"))
    except Exception:
        raise ValueError("target_time must be 'HH:MM'")

    departure_dt = datetime.combine(now.date(), time(dep_h, dep_m))
    if departure_dt <= now:
        departure_dt += timedelta(days=1)

    current_soc = max(0.0, min(100.0, data.battery_level))
    target_soc = max(current_soc, min(100.0, data.target_soc))
    required_kwh = (target_soc - current_soc) / 100.0 * BATTERY_CAPACITY_KWH

    # Already at/above target
    if required_kwh <= 0:
        return PredictResponse(
            hours=0.0,
            final_battery=current_soc,
            timeline=[TimelinePoint(rel_time="+0.00h", abs_time=fmt_hm(now), soc=round(current_soc,1))],
            start_time=fmt_hm(now),
            end_time=fmt_hm(departure_dt),
            cost_now=0.0,
            cost_optimized=0.0,
            savings=0.0,
            meets_departure=True,
            night_tariff_applied=is_low_price(now),
            info="Already at or above target SOC"
        )

    # build slots between now and departure at SLOT_INTERVAL granularity
    slots: List[Dict[str, Any]] = []
    t = now
    max_steps = int(MAX_SCAN_HOURS / SLOT_INTERVAL)
    steps = 0
    while t < departure_dt and steps < max_steps:
        slots.append({"time": t, "price": LOW_PRICE if is_low_price(t) else HIGH_PRICE})
        t += timedelta(hours=SLOT_INTERVAL)
        steps += 1

    # If no slots (very short window), fallback to immediate simulation but cut at departure
    if len(slots) == 0:
        sim = simulate_from_start(current_soc, data.charger_power, required_kwh, now, cutoff_dt=departure_dt)
        meets = (now + timedelta(hours=sim["hours"])) <= departure_dt
        return PredictResponse(
            hours=sim["hours"],
            final_battery=sim["final_soc"],
            timeline=[TimelinePoint(rel_time=p["rel_time"], abs_time=p["abs_time"], soc=p["soc"]) for p in sim["timeline"]],
            start_time=fmt_hm(now),
            end_time=fmt_hm(now + timedelta(hours=sim["hours"])),
            cost_now=sim["cost"],
            cost_optimized=sim["cost"],
            savings=0.0,
            meets_departure=meets,
            night_tariff_applied=any(is_low_price(sl["time"]) for sl in slots),
            info="Very short window; simulated immediate charging with cutoff"
        )

    # ------------------ NORMAL (no optimization) ------------------
    if not data.cheap_mode:
        sim = simulate_from_start(current_soc, data.charger_power, required_kwh, now, cutoff_dt=departure_dt)
        meets = (now + timedelta(hours=sim["hours"])) <= departure_dt
        # cost_now baseline: simulate immediate without cutoff for accurate baseline (but here we used cutoff)
        cost_now = sim["cost"]
        return PredictResponse(
            hours=sim["hours"],
            final_battery=sim["final_soc"],
            timeline=[TimelinePoint(rel_time=p["rel_time"], abs_time=p["abs_time"], soc=p["soc"]) for p in sim["timeline"]],
            start_time=fmt_hm(now),
            end_time=fmt_hm(now + timedelta(hours=sim["hours"])),
            cost_now=round(cost_now, 2),
            cost_optimized=round(cost_now, 2),
            savings=0.0,
            meets_departure=meets,
            night_tariff_applied=any(is_low_price(sl["time"]) for sl in slots),
            info="Normal immediate charging (no cost optimization)"
        )

    # ------------------ CHEAP MODE: enumerate start indices and pick best feasible plan ------------------
    best_plan: Optional[Dict[str, Any]] = None
    n = len(slots)
    for start_idx in range(n):
        # Candidate must start at or after now (slots built from now) so that's fine
        plan = evaluate_start_index(
            current_soc=current_soc,
            charger_kw=data.charger_power,
            required_kwh=required_kwh,
            slots=slots,
            start_idx=start_idx,
            slot_interval_hours=SLOT_INTERVAL,
            sim_sub_interval=SIM_SUB_INTERVAL,
            departure_dt=departure_dt
        )
        # Only accept plans that are completed before departure
        if plan["completed"]:
            # cost baseline for plan comparison is plan["cost"]
            if best_plan is None or plan["cost"] < best_plan["cost"]:
                best_plan = plan

    # If no feasible plan completes before departure, allow plans that maximize fill before departure:
    if best_plan is None:
        # Evaluate all starts but pick the one that reaches the highest final SOC (tie-breaker: lower cost)
        candidate_plans = []
        for start_idx in range(n):
            plan = evaluate_start_index(
                current_soc=current_soc,
                charger_kw=data.charger_power,
                required_kwh=required_kwh,
                slots=slots,
                start_idx=start_idx,
                slot_interval_hours=SLOT_INTERVAL,
                sim_sub_interval=SIM_SUB_INTERVAL,
                departure_dt=departure_dt
            )
            candidate_plans.append(plan)
        # choose plan with largest final_soc; tie-breaker: lower cost; tie-breaker: earliest start
        candidate_plans_sorted = sorted(candidate_plans, key=lambda p: (-p["final_soc"], p["cost"], p.get("start_dt", now)))
        best_plan = candidate_plans_sorted[0]

    # build final response fields from best_plan
    timeline = best_plan["timeline"]
    hours = best_plan["hours"]
    final_soc = best_plan["final_soc"]
    cost_opt = best_plan["cost"]
    start_dt = best_plan["start_dt"]
    cost_now = simulate_from_start(current_soc, data.charger_power, required_kwh, now)["cost"]

    # Fix: compute end_dt from timeline last abs_time with day rollover
    if len(timeline) > 0:
        last_abs = timeline[-1]["abs_time"]  # "HH:MM"
        hh, mm = map(int, last_abs.split(":"))
        end_dt = start_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
    else:
        end_dt = start_dt

    # night tariff applied check — whether any timeline point falls into low-price period
    night_flag = False
    for p in timeline:
        hh, mm = map(int, p["abs_time"].split(":"))
        cand = start_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        # if cand < start_dt assume next day if necessary
        if cand < start_dt:
            cand += timedelta(days=1)
        if is_low_price(cand):
            night_flag = True
            break

    meets_departure = best_plan["completed"]

    info = None
    if not best_plan.get("completed", False):
        info = "Cannot reach target SOC before departure; returning maximal fill plan before departure."

    return PredictResponse(
        hours=round(hours, 2),
        final_battery=round(final_soc, 1),
        timeline=[TimelinePoint(rel_time=p["rel_time"], abs_time=p["abs_time"], soc=p["soc"]) for p in timeline],
        start_time=fmt_hm(start_dt),
        end_time=fmt_hm(end_dt),
        cost_now=round(cost_now, 2),
        cost_optimized=round(cost_opt, 2),
        savings=round(max(cost_now - cost_opt, 0.0), 2),
        meets_departure=meets_departure,
        night_tariff_applied=night_flag,
        info=info
    )
