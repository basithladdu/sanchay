"""Local, explainable ML recommendations bounded by deterministic safety.

The model in this module is intentionally small enough to audit.  It is a
multiclass logistic-regression classifier trained from the disclosed synthetic
seed profiles in ``data/recommendation_training.csv``.  It recommends one of
keep, cleanup review, or archive review from metadata and recovery evidence.

The prediction is never deletion authority.  Callers must constrain cleanup to
files with deterministic recovery evidence and must keep unique files outside
all cleanup executors.  The seed data demonstrates the inference path; it is
not a production accuracy claim or a substitute for future local usage history.
"""
from dataclasses import dataclass
from functools import lru_cache
import csv
import hashlib
import math
from pathlib import Path

from . import storage


MODEL_NAME = "sanchay_local_action_classifier"
MODEL_VERSION = 1
MODEL_TYPE = "multiclass_logistic_regression"
CLASSES = ("keep", "cleanup_review", "archive_review")
FEATURE_NAMES = (
    "unchanged_age",
    "size_scale",
    "recent_access",
    "history_depth",
    "observed_activity",
    "duplicate",
    "disposable",
    "tracked",
    "unique",
    "archive_worthy",
    "temporary",
)
TRAINING_DATA = Path(__file__).with_name("data") / "recommendation_training.csv"
TRAINING_ITERATIONS = 1800
LEARNING_RATE = 0.35
L2_PENALTY = 0.01
MIN_ACTION_CONFIDENCE = 0.45

ARCHIVE_EXTENSIONS = frozenset({
    ".7z", ".bak", ".csv", ".db", ".doc", ".docx", ".dump", ".gz",
    ".iso", ".jpeg", ".jpg", ".json", ".mkv", ".mov", ".mp3",
    ".mp4", ".ods", ".odt", ".pdf", ".png", ".ppt", ".pptx",
    ".raw", ".sql", ".sqlite", ".sqlite3", ".tar", ".tif", ".tiff",
    ".txt", ".wav", ".xls", ".xlsx", ".zip",
})
TEMPORARY_EXTENSIONS = frozenset({
    ".cache", ".class", ".log", ".o", ".obj", ".pyc", ".temp", ".tmp",
})
FEATURE_LABELS = {
    "unchanged_age": "long unchanged period",
    "size_scale": "allocated storage impact",
    "recent_access": "positive recent-access evidence",
    "history_depth": "repeated local observations",
    "observed_activity": "observed access or modification activity",
    "duplicate": "byte-confirmed duplicate evidence",
    "disposable": "regenerable cache/build evidence",
    "tracked": "clean Git restoration evidence",
    "unique": "no deterministic recovery copy",
    "archive_worthy": "preservation-oriented file type",
    "temporary": "temporary/build-oriented file type",
}


class ModelUnavailable(RuntimeError):
    """Raised when the bundled model data cannot be loaded or trained."""


@dataclass(frozen=True)
class _Model:
    weights: tuple
    training_examples: int
    training_accuracy: float
    dataset_sha256: str


def _softmax(values):
    largest = max(values)
    exponentials = [math.exp(value - largest) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def _read_training_data():
    try:
        payload = TRAINING_DATA.read_bytes()
    except OSError as exc:
        raise ModelUnavailable(f"cannot read bundled training data: {exc}") from exc
    try:
        text = payload.decode("utf-8")
        reader = csv.DictReader(text.splitlines())
        required = set(FEATURE_NAMES) | {"label"}
        if set(reader.fieldnames or ()) != required:
            raise ValueError("training columns do not match the model feature schema")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            label = row["label"]
            if label not in CLASSES:
                raise ValueError(f"unsupported label on line {line_number}: {label}")
            features = tuple(float(row[name]) for name in FEATURE_NAMES)
            if any(not math.isfinite(value) or value < 0 or value > 1
                   for value in features):
                raise ValueError(f"feature outside [0, 1] on line {line_number}")
            rows.append((features, CLASSES.index(label)))
    except (TypeError, ValueError) as exc:
        raise ModelUnavailable(f"invalid bundled training data: {exc}") from exc
    if not rows or {label for _, label in rows} != set(range(len(CLASSES))):
        raise ModelUnavailable("training data must contain every recommendation class")
    return rows, hashlib.sha256(payload).hexdigest()


def _predict_probabilities(weights, features):
    vector = (1.0,) + tuple(features)
    logits = [sum(weight * value for weight, value in zip(row, vector))
              for row in weights]
    return _softmax(logits)


@lru_cache(maxsize=1)
def _trained_model():
    examples, dataset_sha256 = _read_training_data()
    class_count = len(CLASSES)
    feature_count = len(FEATURE_NAMES) + 1
    weights = [[0.0] * feature_count for _ in range(class_count)]

    for _ in range(TRAINING_ITERATIONS):
        gradients = [[0.0] * feature_count for _ in range(class_count)]
        for features, expected in examples:
            vector = (1.0,) + features
            probabilities = _predict_probabilities(weights, features)
            for class_index in range(class_count):
                error = probabilities[class_index] - (class_index == expected)
                for feature_index, value in enumerate(vector):
                    gradients[class_index][feature_index] += error * value
        scale = 1.0 / len(examples)
        for class_index in range(class_count):
            for feature_index in range(feature_count):
                regularization = (
                    0.0 if feature_index == 0
                    else L2_PENALTY * weights[class_index][feature_index]
                )
                weights[class_index][feature_index] -= LEARNING_RATE * (
                    gradients[class_index][feature_index] * scale + regularization)

    correct = sum(
        max(range(class_count),
            key=lambda index: _predict_probabilities(weights, features)[index]) == expected
        for features, expected in examples
    )
    return _Model(
        weights=tuple(tuple(row) for row in weights),
        training_examples=len(examples),
        training_accuracy=correct / len(examples),
        dataset_sha256=dataset_sha256,
    )


def model_card():
    """Return auditable provenance and safety limitations for the local model."""
    model = _trained_model()
    return {
        "name": MODEL_NAME,
        "version": MODEL_VERSION,
        "type": MODEL_TYPE,
        "learned_inference": True,
        "training": {
            "dataset": "in-house synthetic expert-labelled storage profiles",
            "dataset_path": "sanchay/data/recommendation_training.csv",
            "dataset_sha256": model.dataset_sha256,
            "examples": model.training_examples,
            "training_accuracy": round(model.training_accuracy, 4),
            "validation_boundary": (
                "training fit is disclosed only to prove the learned inference path; "
                "it is not a production accuracy or generalisation claim"
            ),
        },
        "inputs": list(FEATURE_NAMES),
        "privacy": {
            "file_contents_used": False,
            "personal_attributes_used": False,
            "network_required": False,
        },
        "responsible_use": {
            "protected_or_owner_attributes_used": False,
            "uncertainty_policy": (
                f"recommendations below {MIN_ACTION_CONFIDENCE:.0%} class confidence "
                "abstain to keep"
            ),
            "positive_evidence_policy": (
                "observed use supports keeping; lack of observed use is never deletion proof"
            ),
            "known_limitations": (
                "small synthetic bootstrap data, filesystem timestamp policy, and "
                "in-memory repeated-scan history limit generalisation"
            ),
        },
        "safety_boundary": (
            "the model may rank review actions but cannot bypass credential, managed-path, "
            "hardlink, identity, recovery-evidence, permission, or human-confirmation gates"
        ),
    }


def update_activity_profiles(previous_files, current_files, profiles=None):
    """Update positive activity evidence between completed in-memory scans.

    A changed mtime or an advanced atime is evidence of activity. No observed
    change is only a weak model feature and never becomes deletion permission.
    Replaced inodes start a new profile so activity is not inherited by a
    different file at the same path.
    """
    previous = {info.path: info for info in previous_files or ()}
    existing = profiles or {}
    updated = {}
    for info in current_files:
        prior_info = previous.get(info.path)
        prior_profile = existing.get(info.path, {})
        same_identity = (
            prior_info is not None
            and (getattr(prior_info, "device", None), prior_info.inode)
            == (getattr(info, "device", None), info.inode)
        )
        if not same_identity:
            updated[info.path] = {
                "observations": 1,
                "access_events": 0,
                "modification_events": 0,
            }
            continue
        accessed = float(info.atime) > float(prior_info.atime) + 1
        modified = (
            getattr(info, "mtime_ns", None) != getattr(prior_info, "mtime_ns", None)
            if (getattr(info, "mtime_ns", None) is not None
                and getattr(prior_info, "mtime_ns", None) is not None)
            else float(info.mtime) > float(prior_info.mtime) + 1
        )
        updated[info.path] = {
            "observations": max(1, int(prior_profile.get("observations", 1))) + 1,
            "access_events": max(0, int(prior_profile.get("access_events", 0)))
                             + int(accessed),
            "modification_events": max(
                0, int(prior_profile.get("modification_events", 0))) + int(modified),
        }
    return updated


def features_for(info, evidence_kind, now, activity=None):
    """Extract bounded metadata-only features for one local file."""
    age_seconds = max(0.0, float(now) - float(info.mtime))
    unchanged_age = min(1.0, age_seconds / (365 * 86400))
    allocated = max(0, int(storage.allocated_bytes(info)))
    size_scale = min(1.0, math.log2(allocated + 1) / 40.0)
    suffix = Path(str(info.path).replace("\\", "/")).suffix.lower()

    # A recent atime strictly newer than mtime is positive evidence for keeping
    # a file.  Its absence is never treated as proof that the file is unused.
    atime = float(getattr(info, "atime", 0) or 0)
    recent_access = float(
        atime > float(info.mtime) + 1
        and 0 <= float(now) - atime <= 30 * 86400
    )
    activity = activity or {}
    observations = max(1, int(activity.get("observations", 1)))
    intervals = max(0, observations - 1)
    access_events = max(0, int(activity.get("access_events", 0)))
    modification_events = max(0, int(activity.get("modification_events", 0)))
    history_depth = min(1.0, intervals / 4.0)
    observed_activity = (
        min(1.0, (access_events + modification_events) / intervals)
        if intervals else 0.0
    )
    return {
        "unchanged_age": round(unchanged_age, 6),
        "size_scale": round(size_scale, 6),
        "recent_access": recent_access,
        "history_depth": round(history_depth, 6),
        "observed_activity": round(observed_activity, 6),
        "duplicate": float(evidence_kind == "duplicate"),
        "disposable": float(evidence_kind == "disposable"),
        "tracked": float(evidence_kind == "tracked"),
        "unique": float(evidence_kind == "unique"),
        "archive_worthy": float(suffix in ARCHIVE_EXTENSIONS),
        "temporary": float(suffix in TEMPORARY_EXTENSIONS),
    }


def _factor_trace(model, features, selected_index, runner_up_index):
    selected = model.weights[selected_index]
    runner_up = model.weights[runner_up_index]
    factors = []
    for feature_index, name in enumerate(FEATURE_NAMES, start=1):
        value = features[name]
        if not value:
            continue
        contribution = (selected[feature_index] - runner_up[feature_index]) * value
        factors.append({
            "feature": name,
            "label": FEATURE_LABELS[name],
            "value": value,
            "contribution": round(contribution, 6),
            "direction": "supports" if contribution >= 0 else "opposes",
        })
    factors.sort(key=lambda item: (-abs(item["contribution"]), item["feature"]))
    return factors[:4]


def assess(info, evidence_kind, now, activity=None):
    """Return a constrained, explainable Keep/Cleanup/Archive assessment."""
    model = _trained_model()
    feature_map = features_for(info, evidence_kind, now, activity=activity)
    values = tuple(feature_map[name] for name in FEATURE_NAMES)
    probabilities = _predict_probabilities(model.weights, values)

    # Unique files can be kept or archived, never cleaned. Evidence-backed
    # files can be kept or reviewed for cleanup. The learned model operates
    # inside this deterministic action space.
    allowed = (
        ("keep", "archive_review")
        if evidence_kind == "unique" else
        ("keep", "cleanup_review")
    )
    allowed_indexes = [CLASSES.index(action) for action in allowed]
    selected_index = max(allowed_indexes, key=lambda index: probabilities[index])
    selected_action = CLASSES[selected_index]
    confidence = probabilities[selected_index]
    abstained = confidence < MIN_ACTION_CONFIDENCE
    if abstained:
        selected_action = "keep"
        selected_index = CLASSES.index("keep")

    runner_up_index = max(
        (index for index in range(len(CLASSES)) if index != selected_index),
        key=lambda index: probabilities[index],
    )
    raw_action = CLASSES[max(range(len(CLASSES)), key=lambda index: probabilities[index])]
    safety_override = raw_action not in allowed
    cold_review_probability = 1.0 - probabilities[CLASSES.index("keep")]
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "recommended_action": selected_action,
        "raw_model_action": raw_action,
        "confidence": round(confidence, 6),
        "probabilities": {
            action: round(probabilities[index], 6)
            for index, action in enumerate(CLASSES)
        },
        "usage_assessment": {
            "state": (
                "potentially_cold_review"
                if selected_action in {"cleanup_review", "archive_review"}
                else "active_or_uncertain"
            ),
            "cold_review_probability": round(cold_review_probability, 6),
            "boundary": (
                "learned metadata signal, not proof that a file is unused; absence of "
                "an observed event never authorizes cleanup"
            ),
        },
        "features": feature_map,
        "top_factors": _factor_trace(
            model, feature_map, selected_index, runner_up_index),
        "abstained": abstained,
        "safety_override_applied": safety_override,
        "boundary": (
            "metadata-only learned recommendation; deterministic recovery and action "
            "gates retain final authority"
        ),
    }
