"""
Student360 Behavior Stabilization Engine

Purpose:
- Keep behavior labels stable in live video.
- Avoid one-frame false sleeping / phone-use detections.
- Allow phone-use detections at a realistic confidence level.
- Keep the public API used by process_video.py unchanged.
"""

from collections import deque
from time import time


# ============================================================
# BEHAVIOR CONFIGURATION
# ============================================================

# IMPORTANT:
# The previous phone threshold was 0.70.
# That was too strict for the phone-use detector in this project.
#
# Phone use is usually a small-object detection, so we allow
# lower raw confidence and rely on temporal confirmation to
# suppress false positives.
BEHAVIOR_THRESHOLDS = {
    "attentive": 0.45,
    "not_attentive": 0.55,
    "phone_use": 0.30,
    "sleeping": 0.55,
    "cheating": 0.70,
}

# Number of accepted observations required before switching
# INTO an alert behavior.
#
# Phone use is intentionally faster because the phone is a
# small object and may disappear from YOLO detection briefly.
CONFIRM_COUNTS = {
    "not_attentive": 4,
    "phone_use": 2,
    "sleeping": 5,
    "cheating": 6,
    "attentive": 4,
}

HISTORY_SIZE = 20
HISTORY_SECONDS = 2.0

# Number of attentive observations required before leaving
# an already-confirmed alert.
ATTENTIVE_RELEASE_COUNT = 5

# Extremely weak detections are ignored before they enter history.
GLOBAL_MIN_CONFIDENCE = 0.20


# ============================================================
# LABEL ALIASES
# ============================================================

ATTENTIVE_ALIASES = {
    "attentive",
    "normal",
    "person",
    "focused",
}

PHONE_ALIASES = {
    "phone_use",
    "phone",
    "using_phone",
    "phone_usage",
    "phoneuse",
    "cell_phone",
    "cellphone",
    "mobile_phone",
    "mobile",
}

SLEEP_ALIASES = {
    "sleeping",
    "sleep",
}

NOT_ATTENTIVE_ALIASES = {
    "not_attentive",
    "notattentive",
    "distracted",
    "not_focused",
}

CHEATING_ALIASES = {
    "cheating",
    "malpractice",
}


def normalize_behavior(label: str) -> str:
    value = str(label or "").strip().lower()
    value = value.replace("-", "_").replace(" ", "_")
    return value


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
    value = canonical_behavior(label)

    return {
        "cheating": 100,
        "sleeping": 90,
        "phone_use": 80,
        "not_attentive": 70,
        "attentive": 10,
    }.get(value, 20)


# ============================================================
# STABILIZER
# ============================================================

class BehaviorStabilizer:
    """
    Maintains one confirmed behavior state per student.

    A single YOLO prediction cannot immediately change an alert
    state. Repeated evidence is required.
    """

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
        }

    def _get_state(self, student_id):
        student_id = str(student_id)

        if student_id not in self.states:
            self.states[student_id] = self._new_state()

        return self.states[student_id]

    def current(self, student_id: str):
        state = self._get_state(student_id)

        return {
            "label": state["confirmed"],
            "confidence": float(state["confirmed_confidence"]),
            "stable": True,
        }

    def update(
        self,
        student_id: str,
        raw_label: str,
        confidence: float,
        now: float | None = None,
    ):
        now = time() if now is None else now

        state = self._get_state(student_id)

        label = canonical_behavior(raw_label)
        confidence = float(confidence or 0.0)

        # Remove stale evidence.
        while state["history"] and (
            now - state["history"][0][2] > HISTORY_SECONDS
        ):
            state["history"].popleft()

        state["last_update"] = now

        threshold = BEHAVIOR_THRESHOLDS.get(
            label,
            GLOBAL_MIN_CONFIDENCE,
        )

        threshold = max(
            float(threshold),
            GLOBAL_MIN_CONFIDENCE,
        )

        # Weak prediction does not enter history.
        if confidence < threshold:
            return self.current(student_id)

        state["history"].append(
            (label, confidence, now)
        )

        # Gather recent evidence by behavior.
        evidence = {}

        for item_label, item_conf, item_time in state["history"]:
            if now - item_time <= HISTORY_SECONDS:
                evidence.setdefault(
                    item_label,
                    []
                ).append(
                    (item_conf, item_time)
                )

        if not evidence:
            return self.current(student_id)

        # Candidate ranking:
        # 1. number of observations
        # 2. average confidence
        # 3. behavior priority
        candidates = []

        for candidate, samples in evidence.items():
            average = sum(
                sample[0] for sample in samples
            ) / len(samples)

            candidates.append(
                (
                    len(samples),
                    average,
                    behavior_priority(candidate),
                    candidate,
                )
            )

        candidates.sort(reverse=True)

        _, average_confidence, _, candidate = candidates[0]

        current = state["confirmed"]

        # ====================================================
        # ALERT BEHAVIOR
        # ====================================================

        if candidate != "attentive":

            required_count = CONFIRM_COUNTS.get(
                candidate,
                5,
            )

            required_confidence = BEHAVIOR_THRESHOLDS.get(
                candidate,
                GLOBAL_MIN_CONFIDENCE,
            )

            candidate_count = len(
                evidence.get(candidate, [])
            )

            if (
                candidate_count >= required_count
                and average_confidence >= required_confidence
            ):
                if current != candidate:
                    state["confirmed"] = candidate
                    state["confirmed_confidence"] = average_confidence
                    state["last_change"] = now
                else:
                    state["confirmed_confidence"] = average_confidence

        # ====================================================
        # RETURN TO ATTENTIVE
        # ====================================================

        else:
            attentive_samples = evidence.get(
                "attentive",
                [],
            )

            attentive_count = len(
                attentive_samples
            )

            if attentive_count >= ATTENTIVE_RELEASE_COUNT:

                attentive_average = sum(
                    sample[0]
                    for sample in attentive_samples
                ) / attentive_count

                if current != "attentive":
                    state["confirmed"] = "attentive"
                    state["confirmed_confidence"] = attentive_average
                    state["last_change"] = now
                else:
                    state["confirmed_confidence"] = attentive_average

        return self.current(student_id)
