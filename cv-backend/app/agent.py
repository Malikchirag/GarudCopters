"""
================================================================================
Garud Copters CV — Incident Reporting Agent (LangGraph)
================================================================================

Turns raw YOLOv8 detections (from POST /detect/image or /detect/video) into a
structured incident report: what was found, how severe it is, a plain-
language summary, and a recommended next action.

Architecture (mirrors the pattern used by Aegis AI's threat-analysis agent,
v2/api/app/context/agent.py — same repo, same author, reused deliberately so
the two "detect -> assess severity -> LLM narrative -> rule-based action"
agents in this codebase read the same way):

    analyze_detections -> assess_severity -> [conditional: any objects?]
        -> generate_report -> recommend_action -> END   (objects found)
        -> recommend_action -> END                       (zero objects: skip the LLM call entirely)

As in Aegis AI, SEVERITY and the RECOMMENDED ACTION are rule-based and
deterministic, not LLM-decided — auditable, and it means a missing/invalid
ANTHROPIC_API_KEY degrades the plain-language summary, never the actual
severity call a responder would act on. The LLM's only job is prose.

Author: Prerak Nain
================================================================================
"""
import os
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph


# ==============================================================================
# AGENT STATE
# ==============================================================================

class AgentState(TypedDict):
    # --- INPUT (the raw /detect/* response) ---
    raw_detections: dict  # ImageDetectionResponse or VideoDetectionResponse, as a dict

    # --- INTERMEDIATE (populated by analyze_detections) ---
    total_objects: int
    count_by_class: dict[str, int]
    avg_confidence_by_class: dict[str, float]
    min_confidence_by_class: dict[str, float]

    # --- SEVERITY (rule-based) ---
    severity: str  # "NONE" / "LOW" / "MEDIUM" / "HIGH"
    severity_reasons: list[str]

    # --- OUTPUT ---
    summary: str          # plain-language incident summary (LLM, or a rule-based fallback)
    recommendation: dict  # rule-based next action
    final_report: dict


# ==============================================================================
# RULES — deterministic, mirrors Aegis AI's ACTION_RULES table
# ==============================================================================

# Confidence below this is "the model itself is unsure" -- relevant because a
# HIGH person-count reading we're NOT confident in is arguably more urgent to
# have a human verify than a low-confidence reading of an empty scene: the
# cost of missing real survivors is much higher than a false alarm.
LOW_CONFIDENCE_THRESHOLD = 0.5

ACTION_RULES = {
    "HIGH": {
        "action": "Dispatch rescue team to this location immediately",
        "urgency": "immediate",
    },
    "MEDIUM": {
        "action": "Flag for priority human review; prep a team to dispatch pending confirmation",
        "urgency": "within the hour",
    },
    "LOW": {
        "action": "Log and continue monitoring — no dispatch warranted yet",
        "urgency": "routine",
    },
    "NONE": {
        "action": "No action needed — continue sweep",
        "urgency": "none",
    },
}


# ==============================================================================
# NODE 1: ANALYZE DETECTIONS
# ==============================================================================

def analyze_detections(state: AgentState) -> AgentState:
    """Summarize what was detected: counts, classes, confidence levels."""
    raw = state["raw_detections"]

    # Accept either a /detect/image response (per-object `detections`) or a
    # /detect/video response (pre-aggregated `count_by_class`, no per-object list).
    if "detections" in raw:
        detections = raw["detections"]
        count_by_class: dict[str, int] = {}
        conf_sums: dict[str, float] = {}
        conf_mins: dict[str, float] = {}
        for d in detections:
            cls, conf = d["cls"], d["confidence"]
            count_by_class[cls] = count_by_class.get(cls, 0) + 1
            conf_sums[cls] = conf_sums.get(cls, 0.0) + conf
            conf_mins[cls] = min(conf_mins.get(cls, 1.0), conf)
        avg_conf = {c: conf_sums[c] / count_by_class[c] for c in count_by_class}
        min_conf = conf_mins
    else:
        # Video summaries don't carry per-object confidence -- count_by_class
        # is already aggregate, so confidence stats are simply unavailable.
        count_by_class = raw.get("count_by_class", {})
        avg_conf, min_conf = {}, {}

    state["total_objects"] = sum(count_by_class.values())
    state["count_by_class"] = count_by_class
    state["avg_confidence_by_class"] = avg_conf
    state["min_confidence_by_class"] = min_conf
    return state


# ==============================================================================
# NODE 2: ASSESS SEVERITY (rule-based, deterministic)
# ==============================================================================

def assess_severity(state: AgentState) -> AgentState:
    """
    Rule-based severity, per the brief: high person-count + low confidence
    where routes may be blocked (vehicles/debris present) = HIGH; a handful
    of confident detections = MEDIUM; a couple of detections = LOW; nothing
    detected = NONE. Deliberately not an LLM judgment call — see module docstring.
    """
    person_count = state["count_by_class"].get("person", 0)
    vehicle_count = state["count_by_class"].get("vehicle", 0)
    debris_count = state["count_by_class"].get("debris", 0)
    person_conf = state["avg_confidence_by_class"].get("person")

    reasons = []

    if state["total_objects"] == 0:
        state["severity"] = "NONE"
        state["severity_reasons"] = ["No people, vehicles, or debris detected in frame"]
        return state

    route_possibly_blocked = (vehicle_count > 0 or debris_count > 0)

    if person_count >= 5:
        if person_conf is not None and person_conf < LOW_CONFIDENCE_THRESHOLD:
            severity = "HIGH"
            reasons.append(
                f"{person_count} people detected but average confidence "
                f"({person_conf:.0%}) is below {LOW_CONFIDENCE_THRESHOLD:.0%} — "
                "likely undercounting a larger group, treat as worst case"
            )
        else:
            severity = "MEDIUM"
            reasons.append(f"{person_count} people detected with reasonable model confidence")
        if route_possibly_blocked:
            severity = "HIGH"
            reasons.append(f"Vehicles/debris present ({vehicle_count} vehicle(s), {debris_count} debris) — possible blocked egress route near a group of people")
    elif person_count >= 1:
        severity = "MEDIUM" if route_possibly_blocked else "LOW"
        reasons.append(f"{person_count} person(s) detected")
        if route_possibly_blocked:
            reasons.append(f"Vehicles/debris present ({vehicle_count} vehicle(s), {debris_count} debris) near detected person(s)")
    else:
        # only vehicles/debris, no people
        severity = "LOW"
        reasons.append(f"No people detected; {vehicle_count} vehicle(s), {debris_count} debris only")

    state["severity"] = severity
    state["severity_reasons"] = reasons
    return state


# ==============================================================================
# CONDITIONAL EDGE: any objects worth writing a narrative about?
# ==============================================================================

def has_objects(state: AgentState) -> Literal["generate_report", "skip_report"]:
    """Zero detections -> skip the LLM call entirely (no API cost/latency
    spent narrating an empty frame) and go straight to the (trivially
    "keep monitoring") recommendation."""
    return "generate_report" if state["total_objects"] > 0 else "skip_report"


# ==============================================================================
# NODE 3: GENERATE REPORT (LLM call — plain-language narrative only)
# ==============================================================================

def generate_report(state: AgentState) -> AgentState:
    """LLM turns the structured counts/severity into a readable incident
    summary. Degrades gracefully (rule-based fallback string) with no
    ANTHROPIC_API_KEY, mirroring Aegis AI's generate_narrative node."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        state["summary"] = _fallback_summary(state)
        return state

    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
        max_tokens=250,
        temperature=0.2,
    )

    counts_text = ", ".join(f"{v} {k}" for k, v in state["count_by_class"].items()) or "none"
    conf_text = ", ".join(
        f"{k}: avg {v:.0%}" for k, v in state["avg_confidence_by_class"].items()
    ) or "not available (video-aggregated detections)"

    prompt = f"""You are a disaster-response analyst AI writing a brief incident summary
for a drone operator, based on YOLOv8 object detections from aerial footage.

DETECTED: {counts_text}
CONFIDENCE: {conf_text}
SEVERITY (already determined by rules, do not re-derive it): {state['severity']}
WHY: {'; '.join(state['severity_reasons'])}

Write a 2-4 sentence plain-language summary of the scene and why it was rated
this severity. Be factual and concrete — reference the actual counts. Do not
invent details not in the data above (no locations, no injuries, no time of
day) and do not suggest an action — that's handled separately."""

    try:
        response = llm.invoke(prompt)
        state["summary"] = response.content
    except Exception as e:
        state["summary"] = f"[LLM call failed, falling back to rule-based summary: {e}] " + _fallback_summary(state)
    return state


def _fallback_summary(state: AgentState) -> str:
    counts_text = ", ".join(f"{v} {k}" for k, v in state["count_by_class"].items()) or "no objects"
    return (
        f"Detected {counts_text} ({state['total_objects']} total). "
        f"Severity: {state['severity']}. Reasons: {'; '.join(state['severity_reasons'])}."
    )


# ==============================================================================
# NODE 4: RECOMMEND ACTION (rule-based)
# ==============================================================================

def recommend_action(state: AgentState) -> AgentState:
    """Deterministic next-step recommendation from the severity rules table —
    same reasoning as Aegis AI's determine_recommendation: the action itself
    must be auditable, not something an LLM free-decided."""
    rules = ACTION_RULES[state["severity"]]
    state["recommendation"] = {
        "severity": state["severity"],
        "recommended_action": rules["action"],
        "urgency": rules["urgency"],
    }
    if state["total_objects"] == 0:
        state["summary"] = state.get("summary") or "No people, vehicles, or debris detected in this frame/video."
    return state


# ==============================================================================
# NODE 5: COMPILE REPORT
# ==============================================================================

def compile_report(state: AgentState) -> AgentState:
    state["final_report"] = {
        "detections": {
            "total_objects": state["total_objects"],
            "count_by_class": state["count_by_class"],
            "avg_confidence_by_class": state["avg_confidence_by_class"],
        },
        "severity": {
            "level": state["severity"],
            "reasons": state["severity_reasons"],
        },
        "summary": state["summary"],
        "recommendation": state["recommendation"],
    }
    return state


# ==============================================================================
# GRAPH CONSTRUCTION
# ==============================================================================

def build_agent_graph():
    """
    analyze_detections -> assess_severity
      -> [any objects?] -> generate_report -> recommend_action -> compile_report -> END
                        -> recommend_action (LLM call skipped) -> compile_report -> END
    """
    graph = StateGraph(AgentState)

    graph.add_node("analyze_detections", analyze_detections)
    graph.add_node("assess_severity", assess_severity)
    graph.add_node("generate_report", generate_report)
    graph.add_node("recommend_action", recommend_action)
    graph.add_node("compile_report", compile_report)

    graph.set_entry_point("analyze_detections")
    graph.add_edge("analyze_detections", "assess_severity")

    graph.add_conditional_edges(
        "assess_severity",
        has_objects,
        {
            "generate_report": "generate_report",
            "skip_report": "recommend_action",
        },
    )

    graph.add_edge("generate_report", "recommend_action")
    graph.add_edge("recommend_action", "compile_report")
    graph.add_edge("compile_report", END)

    return graph.compile()


# ==============================================================================
# PUBLIC ENTRY POINT
# ==============================================================================

def run_agent(raw_detections: dict) -> dict:
    """Run the full agent pipeline on a /detect/image or /detect/video response."""
    initial_state: AgentState = {
        "raw_detections": raw_detections,
        "total_objects": 0,
        "count_by_class": {},
        "avg_confidence_by_class": {},
        "min_confidence_by_class": {},
        "severity": "",
        "severity_reasons": [],
        "summary": "",
        "recommendation": {},
        "final_report": {},
    }
    agent = build_agent_graph()
    result = agent.invoke(initial_state)
    return result["final_report"]


# ==============================================================================
# STANDALONE TEST
# ==============================================================================

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("GARUD COPTERS CV AGENT — STANDALONE TEST")
    print("=" * 70)

    print("\n--- TEST 1: large group, low confidence, blocked route (-> HIGH) ---")
    detections_high = {
        "filename": "flood_scene_1.jpg", "width": 1280, "height": 720,
        "detections": (
            [{"cls": "person", "confidence": 0.42, "box": [0, 0, 10, 10]} for _ in range(6)]
            + [{"cls": "vehicle", "confidence": 0.71, "box": [0, 0, 10, 10]}]
        ),
        "count_by_class": {"person": 6, "vehicle": 1},
    }
    print(json.dumps(run_agent(detections_high), indent=2, default=str))

    print("\n--- TEST 2: single confident person, no obstruction (-> LOW) ---")
    detections_low = {
        "filename": "clear_area.jpg", "width": 1280, "height": 720,
        "detections": [{"cls": "person", "confidence": 0.91, "box": [0, 0, 10, 10]}],
        "count_by_class": {"person": 1},
    }
    print(json.dumps(run_agent(detections_low), indent=2, default=str))

    print("\n--- TEST 3: zero detections (-> NONE, LLM call skipped) ---")
    detections_none = {
        "filename": "empty_field.jpg", "width": 1280, "height": 720,
        "detections": [], "count_by_class": {},
    }
    print(json.dumps(run_agent(detections_none), indent=2, default=str))
