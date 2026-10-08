"""
behavior_engine.py
Student360 behavior configuration.

IMPORTANT
---------
Classroom preset:
    attentive, not_attentive, phone_use, sleeping

Exam preset:
    cheating, non_cheating

Rules:
- non_cheating is NEVER converted to attentive.
- Classroom and exam "normal" states stay separate.
- A single weak alert frame is not enough to replace a normal state.
- Alert selection is based on repeated evidence + confidence, not only priority.
- This module is intentionally compatible with process_video.py, which imports:
      canonical_behavior
      behavior_priority
      BEHAVIOR_THRESHOLDS
"""

from collections import deque
from time import time


# ============================================================
# THRESHOLDS
# ============================================================

BEHAVIOR_THRESHOLDS = {
    # Classroom
    "attentive": 0.30,
    "not_attentive": 0.30,
    "phone_use": 0.25,
    "sleeping": 0.42,

    # Exam
    "cheating": 0.30,
    "non_cheating": 0.20,
}


# Number of observations required before an alert is confirmed.
CONFIRM_COUNTS = {
    "attentive": 3,
    "not_attentive": 3,
    "phone_use": 2,
    "sleeping": 3,

    # Keep cheating responsive, but never one-frame.
    "cheating": 2,
    "non_cheating": 2,
}


# Evidence windows in seconds.
EVIDENCE_WINDOWS = {
    "attentive": 1.00,
    "not_attentive": 2.00,
    "phone_use": 2.00,
    "sleeping": 2.50,

    "cheating": 2.00,
    "non_cheating": 1.20,
}


HISTORY_SIZE = 60
HISTORY_SECONDS = 2.50

# Short hold avoids flicker but does not keep a wrong alert for too long.
ALERT_HOLD_SECONDS = 0.90

GLOBAL_MIN_CONFIDENCE = 0.20


# ============================================================
# LABEL ALIASES
# ============================================================

ATTENTIVE_ALIASES = {
    "attentive",
    "normal",
    "focused",
    "focus",
}

NON_CHEATING_ALIASES = {
    "non_cheating",
    "noncheating",
    "not_cheating",
    "notcheating",
    "normal_exam",
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
    "using_mobile",
    "mobile_use",
    "phoneusing",
}

SLEEP_ALIASES = {
    "sleeping",
    "sleep",
    "drowsy",
    "drowsiness",
}

NOT_ATTENTIVE_ALIASES = {
    "not_attentive",
    "notattentive",
    "distracted",
    "not_focused",
    "inattentive",
    "distraction",
}

CHEATING_ALIASES = {
    "cheating",
    "malpractice",
    "cheat",
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_behavior(label: str) -> str:
    value = str(label or "").strip().lower()
    return value.replace("-", "_").replace(" ", "_")


def canonical_behavior(label: str) -> str:
    value = normalize_behavior(label)

    if value in ATTENTIVE_ALIASES:
        return "attentive"

    if value in NON_CHEATING_ALIASES:
        return "non_cheating"

    if value in PHONE_ALIASES:
        return "phone_use"

    if value in SLEEP_ALIASES:
        return "sleeping"

    if value in NOT_ATTENTIVE_ALIASES:
        return "not_attentive"

    if value in CHEATING_ALIASES:
        return "cheating"

    # Keep generic detector labels harmless.
    if value in {"person", "human", "student"}:
        return "person"

    return value


def behavior_priority(label: str) -> int:
    """
    Priority is only a tie-breaker after a behavior has already earned
    confirmation. It must not make one weak cheating/sleeping frame win.
    """
    value = canonical_behavior(label)

    return {
        "cheating": 100,
        "phone_use": 95,
        "sleeping": 90,
        "not_attentive": 70,
        "attentive": 10,
        "non_cheating": 10,
        "person": 0,
    }.get(value, 20)


# ============================================================
# HELPERS
# ============================================================

CLASSROOM_LABELS = {
    "attentive",
    "not_attentive",
    "phone_use",
    "sleeping",
}

EXAM_LABELS = {
    "cheating",
    "non_cheating",
}


def _behavior_mode(label: str):
    label = canonical_behavior(label)

    if label in EXAM_LABELS:
        return "exam"

    if label in CLASSROOM_LABELS:
        return "classroom"

    return None


def _normal_label_for_mode(mode: str) -> str:
    return "non_cheating" if mode == "exam" else "attentive"


# ============================================================
# GENERIC STABILIZER
# ============================================================

class BehaviorStabilizer:
    """
    Generic per-student stabilizer.

    process_video.py has its own dedicated live stabilizers, but other
    Student360 routes can safely use this class.

    Key protections:
    - classroom/exam history is not mixed;
    - non_cheating is never changed to attentive;
    - one weak alert cannot win;
    - when evidence is mixed, normal state wins;
    - priority is only used after confirmation.
    """

    def __init__(self):
        self.states = {}

    def reset(self):
        self.states.clear()

    def _new_state(self, mode="classroom"):
        now = time()
        normal = _normal_label_for_mode(mode)

        return {
            "mode": mode,
            "confirmed": normal,
            "confirmed_confidence": 1.0,
            "history": deque(maxlen=HISTORY_SIZE),
            "last_update": now,
            "last_change": now,
            "last_alert": 0.0,
        }

    def _get_state(self, student_id, mode=None):
        key = str(student_id)

        if key not in self.states:
            self.states[key] = self._new_state(mode or "classroom")

        state = self.states[key]

        # If the preset changes, reset history so classroom evidence cannot
        # contaminate exam state or vice versa.
        if mode and state.get("mode") != mode:
            self.states[key] = self._new_state(mode)
            state = self.states[key]

        return state

    def current(self, student_id):
        state = self._get_state(student_id)

        return {
            "label": state["confirmed"],
            "confidence": float(state["confirmed_confidence"]),
            "stable": True,
        }

    @staticmethod
    def _average(samples):
        if not samples:
            return 0.0
        return sum(float(item[1]) for item in samples) / len(samples)

    def update(self, student_id, raw_label, confidence, now=None):
        now = time() if now is None else float(now)

        label = canonical_behavior(raw_label)
        mode = _behavior_mode(label)

        # Ignore labels that are not part of either preset.
        if mode is None:
            state = self._get_state(student_id)
            state["last_update"] = now
            return self.current(student_id)

        state = self._get_state(student_id, mode=mode)
        confidence = float(confidence or 0.0)

        # Remove old observations.
        while (
            state["history"]
            and now - float(state["history"][0][2]) > HISTORY_SECONDS
        ):
            state["history"].popleft()

        threshold = max(
            float(BEHAVIOR_THRESHOLDS.get(label, GLOBAL_MIN_CONFIDENCE)),
            GLOBAL_MIN_CONFIDENCE,
        )

        # Normal labels are always valid observations.
        # Alert labels must pass their confidence gate first.
        if label in {"attentive", "non_cheating"}:
            state["history"].append((label, confidence, now))
        elif confidence >= threshold:
            state["history"].append((label, confidence, now))
            state["last_alert"] = now

        normal_label = _normal_label_for_mode(mode)

        if mode == "exam":
            alert_labels = {"cheating"}
        else:
            alert_labels = {
                "phone_use",
                "sleeping",
                "not_attentive",
            }

        confirmed_alerts = []

        for candidate in alert_labels:
            window = EVIDENCE_WINDOWS.get(candidate, 2.0)

            samples = [
                item
                for item in state["history"]
                if item[0] == candidate
                and now - float(item[2]) <= window
            ]

            required = int(CONFIRM_COUNTS.get(candidate, 3))

            if len(samples) < required:
                continue

            average = self._average(samples)

            if average < float(
                BEHAVIOR_THRESHOLDS.get(
                    candidate,
                    GLOBAL_MIN_CONFIDENCE,
                )
            ):
                continue

            # Extra exam protection:
            # cheating should occupy a meaningful share of recent exam
            # observations before replacing non_cheating.
            if mode == "exam":
                recent_exam = [
                    item
                    for item in state["history"]
                    if item[0] in EXAM_LABELS
                    and now - float(item[2]) <= EVIDENCE_WINDOWS["cheating"]
                ]

                cheating_ratio = (
                    len(samples) / len(recent_exam)
                    if recent_exam
                    else 0.0
                )

                if cheating_ratio < 0.50:
                    continue

            confirmed_alerts.append(
                (
                    average,
                    len(samples),
                    behavior_priority(candidate),
                    candidate,
                )
            )

        if confirmed_alerts:
            # Confidence first, then evidence count, then priority.
            # This prevents high-priority cheating/sleeping from winning
            # merely because of its label.
            confirmed_alerts.sort(reverse=True)
            average, _, _, winner = confirmed_alerts[0]

            state["confirmed"] = winner
            state["confirmed_confidence"] = average
            state["last_change"] = now
            state["last_update"] = now

            return self.current(student_id)

        # Briefly hold a confirmed alert to avoid flicker.
        if (
            state["confirmed"] != normal_label
            and now - float(state["last_alert"]) <= ALERT_HOLD_SECONDS
        ):
            state["last_update"] = now
            return self.current(student_id)

        # Return to the correct normal state for the selected preset.
        normal_window = EVIDENCE_WINDOWS.get(normal_label, 1.0)

        normal_samples = [
            item
            for item in state["history"]
            if item[0] == normal_label
            and now - float(item[2]) <= normal_window
        ]

        if normal_samples:
            normal_average = self._average(normal_samples)
        else:
            normal_average = 1.0

        state["confirmed"] = normal_label
        state["confirmed_confidence"] = normal_average
        state["last_change"] = now
        state["last_update"] = now

        return self.current(student_id)
