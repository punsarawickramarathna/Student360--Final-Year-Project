"""
Student360 behavior configuration used by the live AI pipeline.

Important:
- Thresholds here are raw evidence gates, not final decisions.
- Final decisions are stabilized temporally in process_video.py.
"""

from collections import deque
from time import time

BEHAVIOR_THRESHOLDS = {
    "attentive": 0.30,
    "not_attentive": 0.35,
    "phone_use": 0.25,
    "sleeping": 0.52,
    "cheating": 0.35,
}

CONFIRM_COUNTS = {
    "not_attentive": 5,
    "phone_use": 2,
    "sleeping": 6,
    "cheating": 4,
    "attentive": 3,
}

EVIDENCE_WINDOWS = {
    "not_attentive": 1.20,
    "phone_use": 2.00,
    "sleeping": 1.60,
    "cheating": 1.20,
}

HISTORY_SIZE = 40
HISTORY_SECONDS = 1.50
ALERT_HOLD_SECONDS = 1.00
GLOBAL_MIN_CONFIDENCE = 0.20

ATTENTIVE_ALIASES = {
    "attentive", "normal", "person", "focused"
}

PHONE_ALIASES = {
    "phone_use", "phone", "using_phone", "phone_usage", "phoneuse",
    "cell_phone", "cellphone", "mobile_phone", "mobile", "using_mobile",
    "mobile_use", "phoneusing"
}

SLEEP_ALIASES = {
    "sleeping", "sleep", "drowsy", "drowsiness"
}

NOT_ATTENTIVE_ALIASES = {
    "not_attentive", "notattentive", "distracted", "not_focused",
    "inattentive", "distraction"
}

CHEATING_ALIASES = {
    "cheating", "malpractice", "cheat"
}


def normalize_behavior(label: str) -> str:
    value = str(label or "").strip().lower()
    return value.replace("-", "_").replace(" ", "_")


def canonical_behavior(label: str) -> str:
    value = normalize_behavior(label)
    if value in ATTENTIVE_ALIASES:
        return "attentive"
    if value in PHONE_ALIASES:
        return "phone_use"
    if value in SLEEP_ALIASES:
        return "sleeping"
    if value in NOT_ATTENTIVE_ALIASES:
        return "not_attentive"
    if value in CHEATING_ALIASES:
        return "cheating"
    return value


def behavior_priority(label: str) -> int:
    return {
        "cheating": 100,
        "malpractice": 100,
        "sleeping": 90,
        "phone_use": 95,
        "not_attentive": 70,
        "attentive": 10,
        "person": 0,
    }.get(canonical_behavior(label), 20)


class BehaviorStabilizer:
    """Generic fallback stabilizer for code paths outside the live route."""

    def __init__(self):
        self.states = {}

    def reset(self):
        self.states.clear()

    def _new_state(self):
        now = time()
        return {
            "confirmed": "attentive",
            "confirmed_confidence": 1.0,
            "history": deque(maxlen=HISTORY_SIZE),
            "last_update": now,
            "last_change": now,
            "last_alert": 0.0,
        }

    def _get_state(self, student_id):
        key = str(student_id)
        if key not in self.states:
            self.states[key] = self._new_state()
        return self.states[key]

    def current(self, student_id):
        state = self._get_state(student_id)
        return {
            "label": state["confirmed"],
            "confidence": float(state["confirmed_confidence"]),
            "stable": True,
        }

    def update(self, student_id, raw_label, confidence, now=None):
        now = time() if now is None else now
        state = self._get_state(student_id)
        label = canonical_behavior(raw_label)
        confidence = float(confidence or 0.0)

        while state["history"] and now - state["history"][0][2] > HISTORY_SECONDS:
            state["history"].popleft()

        if label != "person":
            threshold = max(
                float(BEHAVIOR_THRESHOLDS.get(label, GLOBAL_MIN_CONFIDENCE)),
                GLOBAL_MIN_CONFIDENCE,
            )
            if label == "attentive" or confidence >= threshold:
                state["history"].append((label, confidence, now))
                if label != "attentive":
                    state["last_alert"] = now

        candidates = []
        labels = {item[0] for item in state["history"]}
        for candidate in labels:
            if candidate == "attentive":
                continue
            window = EVIDENCE_WINDOWS.get(candidate, 1.20)
            samples = [
                item for item in state["history"]
                if item[0] == candidate and now - item[2] <= window
            ]
            required = CONFIRM_COUNTS.get(candidate, 4)
            if len(samples) < required:
                continue
            average = sum(item[1] for item in samples) / len(samples)
            threshold = max(
                float(BEHAVIOR_THRESHOLDS.get(candidate, GLOBAL_MIN_CONFIDENCE)),
                GLOBAL_MIN_CONFIDENCE,
            )
            if average >= threshold:
                candidates.append(
                    (behavior_priority(candidate), average, len(samples), candidate)
                )

        if candidates:
            candidates.sort(reverse=True)
            _, average, _, winner = candidates[0]
            state["confirmed"] = winner
            state["confirmed_confidence"] = average
            state["last_change"] = now
            return self.current(student_id)

        if state["confirmed"] != "attentive":
            if now - state["last_alert"] <= ALERT_HOLD_SECONDS:
                return self.current(student_id)

        attentive = [
            x for x in state["history"]
            if x[0] == "attentive" and now - x[2] <= 0.8
        ]
        if len(attentive) >= CONFIRM_COUNTS["attentive"]:
            state["confirmed"] = "attentive"
            state["confirmed_confidence"] = (
                sum(x[1] for x in attentive) / len(attentive)
                if attentive else 1.0
            )
            state["last_change"] = now

        return self.current(student_id)
