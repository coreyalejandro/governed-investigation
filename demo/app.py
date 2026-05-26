"""
TLC Demo Server — Governed Investigation
FastAPI app exposing the Contract Window FSM and Bicameral Review
via a browser UI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid

from tlc_kernel.engine import ContractWindow, InvariantStatus, ContractWindowState, EpistemicTag, ClaimEntry
from tlc_kernel.review import BicameralReview
from tlc_kernel.exceptions import HaltAuthorityException

app = FastAPI(title="TLC Runtime Governance Demo")

# In-memory session store
sessions: Dict[str, Dict] = {}


# ---------- Pydantic models ----------

class NewSessionRequest(BaseModel):
    task_state: str = "Auditing retail consumer behavior signals"

class TelemetryRequest(BaseModel):
    session_id: str
    telemetry: Dict[str, Any]
    proposed_output: Optional[str] = "Consumer behavior interpretation output."

class ClaimRequest(BaseModel):
    session_id: str
    claim_text: str
    tag: str  # VERIFIED | CONSTRUCTED | PENDING

class RepairRequest(BaseModel):
    session_id: str


# ---------- Preset telemetry scenarios ----------

SCENARIOS = {
    "nominal": {
        "label": "Nominal — Governed Pass",
        "description": "High narrative coherence, strong brand loyalty, no betrayal signals. All invariants should resolve SATISFIED.",
        "telemetry": {
            "narrative_coherence": 0.85,
            "memory_persistence": 0.75,
            "repeat_rate": 0.82,
            "brand_known_ratio": 0.78,
            "private_label_shift": 0.04,
            "community_vocabulary_match": 0.71,
            "dilution_flag": False,
            "cultural_misappropriation_score": 0.10,
            "event_spike_amplitude": 2.5,
            "visible_category_ratio": 0.55,
            "silhouette_score": 0.62,
            "occasion_match": 0.80,
            "discount_elasticity": -0.45,
            "repeat_purchase_rate": 0.88,
            "switching_on_discount": 0.08,
            "return_rate": 0.03,
            "real_use_positive_sentiment": 0.81,
            "bulk_purchase_scale": 0.55,
            "event_success_rate": 0.82,
            "session_turn_count": 5,
        }
    },
    "betrayal": {
        "label": "Betrayal Event — HALT",
        "description": "Brand reformulation detected without notice + high switching on betrayal. Enacted Fidelity violated.",
        "telemetry": {
            "narrative_coherence": 0.85,
            "memory_persistence": 0.75,
            "repeat_rate": 0.92,
            "reformulation_without_notice": True,
            "betrayal_signal_detected": True,
            "switching_on_betrayal": 0.72,
            "session_turn_count": 8,
        }
    },
    "euphemism": {
        "label": "Semantic Drift — Euphemism Injection",
        "description": "Corporate sanitized language masking store closure. Bicameral Review catches the drift.",
        "telemetry": {
            "narrative_coherence": 0.80,
            "memory_persistence": 0.70,
            "discount_elasticity": -0.4,
            "repeat_purchase_rate": 0.90,
            "switching_on_discount": 0.05,
            "session_turn_count": 3,
        },
        "proposed_output": (
            "The node has successfully executed a geographic footprint optimization strategy, "
            "reallocating fixed assets away from low-index urban sectors to maximize fiscal synergy."
        )
    },
    "memory_bloat": {
        "label": "Memory Bloat — Context Horizon",
        "description": "Session turn count exceeds 40 without reanchoring. Narrative degrades to AMBIGUOUS.",
        "telemetry": {
            "narrative_coherence": 0.82,
            "memory_persistence": 0.71,
            "session_turn_count": 45,
            "state_reanchored_flag": False,
        }
    },
    "frontin": {
        "label": "Frontin' Scenario — Retail Surveillance",
        "description": "Black shopper deploying presentation management in a surveilled big-box environment. Governed system should produce NOMINAL.",
        "telemetry": {
            "narrative_coherence": 0.88,
            "memory_persistence": 0.76,
            "repeat_rate": 0.84,
            "brand_known_ratio": 0.79,
            "private_label_shift": 0.03,
            "community_vocabulary_match": 0.73,
            "dilution_flag": False,
            "cultural_misappropriation_score": 0.08,
            "silhouette_score": 0.67,
            "occasion_match": 0.85,
            "discount_elasticity": -0.50,
            "repeat_purchase_rate": 0.91,
            "switching_on_discount": 0.06,
            "return_rate": 0.02,
            "real_use_positive_sentiment": 0.84,
            "session_turn_count": 2,
        }
    }
}


# ---------- Helper ----------

def session_snapshot(session_id: str) -> Dict:
    s = sessions[session_id]
    cw: ContractWindow = s["contract"]
    return {
        "session_id": session_id,
        "task_state": cw.task_state,
        "fsm_state": cw.fsm_state.value,
        "halt_authority_active": cw.halt_authority_active,
        "turn_count": cw.turn_history_count,
        "invariant_registry": {k: v.value for k, v in cw.invariant_registry.items()},
        "repair_queue": cw.repair_queue,
        "truth_ledger": [c.to_ledger_format() for c in cw.truth_ledger],
        "event_log": s["event_log"],
    }


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
def root():
    with open(os.path.join(os.path.dirname(__file__), "index.html")) as f:
        return f.read()

@app.get("/scenarios")
def list_scenarios():
    return {k: {"label": v["label"], "description": v["description"]} for k, v in SCENARIOS.items()}

@app.post("/session/new")
def new_session(req: NewSessionRequest):
    sid = str(uuid.uuid4())[:8]
    cw = ContractWindow(task_state=req.task_state)
    sessions[sid] = {
        "contract": cw,
        "bicameral": BicameralReview(cw),
        "event_log": [f"Session created. Task: {req.task_state}"],
    }
    return session_snapshot(sid)

@app.post("/session/evaluate")
def evaluate(req: TelemetryRequest):
    if req.session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    s = sessions[req.session_id]
    cw: ContractWindow = s["contract"]
    bicameral: BicameralReview = s["bicameral"]

    # Reset halt for fresh eval
    cw.halt_authority_active = False
    cw.repair_queue = []

    try:
        proposed = req.proposed_output or "Consumer behavior interpretation output."
        cleared = bicameral.execute_dual_pipeline(proposed, req.telemetry)
        if cleared:
            s["event_log"].append(f"TURN {cw.turn_history_count} | CLEARED | Output emitted.")
        else:
            s["event_log"].append(f"TURN {cw.turn_history_count} | BLOCKED | Bicameral review failed.")
    except HaltAuthorityException as e:
        s["event_log"].append(f"TURN {cw.turn_history_count} | HALT | {e.missing_context_gap[:120]}")

    snap = session_snapshot(req.session_id)
    snap["cleared"] = cleared
    return snap

@app.post("/session/run_scenario")
def run_scenario(body: dict):
    sid = body.get("session_id")
    scenario_key = body.get("scenario")
    if sid not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    if scenario_key not in SCENARIOS:
        return JSONResponse(status_code=400, content={"error": f"Unknown scenario: {scenario_key}"})

    scen = SCENARIOS[scenario_key]
    telemetry = scen["telemetry"]
    proposed = scen.get("proposed_output", "Nominal consumer behavior interpretation.")

    s = sessions[sid]
    cw: ContractWindow = s["contract"]
    bicameral: BicameralReview = s["bicameral"]
    cw.halt_authority_active = False
    cw.repair_queue = []

    cleared = False
    try:
        cleared = bicameral.execute_dual_pipeline(proposed, telemetry)
        if cleared:
            s["event_log"].append(f"SCENARIO [{scen['label']}] | CLEARED")
        else:
            s["event_log"].append(f"SCENARIO [{scen['label']}] | BLOCKED")
    except HaltAuthorityException as e:
        s["event_log"].append(f"SCENARIO [{scen['label']}] | HALT | {e.missing_context_gap[:120]}")

    snap = session_snapshot(sid)
    snap["cleared"] = cleared
    snap["scenario_run"] = scenario_key
    return snap

@app.post("/session/add_claim")
def add_claim(req: ClaimRequest):
    if req.session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    cw: ContractWindow = sessions[req.session_id]["contract"]
    try:
        tag = EpistemicTag[req.tag.upper()]
    except KeyError:
        return JSONResponse(status_code=400, content={"error": f"Invalid tag: {req.tag}. Use VERIFIED, CONSTRUCTED, or PENDING."})
    cw.truth_ledger.append(ClaimEntry(req.claim_text, tag))
    sessions[req.session_id]["event_log"].append(f"CLAIM [{tag.value}] added: {req.claim_text[:60]}")
    return session_snapshot(req.session_id)

@app.post("/session/repair")
def repair(req: RepairRequest):
    if req.session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    cw: ContractWindow = sessions[req.session_id]["contract"]
    cw.halt_authority_active = False
    cw.repair_queue = []
    # Reset all VIOLATED and AMBIGUOUS back to AMBIGUOUS (human repair gesture)
    for k in cw.invariant_registry:
        if cw.invariant_registry[k] == InvariantStatus.VIOLATED:
            cw.invariant_registry[k] = InvariantStatus.AMBIGUOUS
    cw.fsm_state = ContractWindowState.REPAIR
    sessions[req.session_id]["event_log"].append("REPAIR action submitted by human investigator.")
    return session_snapshot(req.session_id)

@app.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    return session_snapshot(session_id)

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    sessions.pop(session_id, None)
    return {"status": "terminated"}
