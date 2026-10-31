"""Empirical uncertainty metrics and strict structured-output validation."""

from collections import Counter
import math


LABELS = ["residential", "employment", "commercial", "education", "medical",
          "transport_hub", "industrial", "recreation", "tourism", "food_nightlife",
          "public_service", "mixed_activity"]
BOUNDS = {"production_multiplier": (0.5, 2.0), "attraction_weight": (0.5, 2.0),
          "free_flow_cost_factor": (0.8, 1.2)}


def empirical_entropy(labels):
    if not labels:
        raise ValueError("Empty samples have no empirical entropy")
    n = len(labels)
    return -sum((count / n) * math.log(count / n) for count in Counter(labels).values())


def modal_consistency(labels):
    if not labels:
        raise ValueError("Empty samples have no consistency")
    return max(Counter(labels).values()) / len(labels)


def validate_profile(profile):
    if set(profile) != {"dominant_semantic", "summary", *BOUNDS}:
        raise ValueError("Unexpected or missing profile fields")
    if profile["dominant_semantic"] not in LABELS:
        raise ValueError("Unrecognized semantic category")
    if not isinstance(profile["summary"], str) or not profile["summary"].strip():
        raise ValueError("Missing semantic summary")
    for field, (low, high) in BOUNDS.items():
        value = profile[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Invalid coefficient: " + field)
    return profile


def cluster_from_entailments(size, directed):
    representatives, labels = [], []
    for index in range(size):
        match = next((k for k, ref in enumerate(representatives)
                      if directed[(ref, index)] and directed[(index, ref)]), None)
        if match is None:
            match = len(representatives)
            representatives.append(index)
        labels.append(match)
    return labels


def cpc(left, right):
    if len(left) != len(right) or not left or any(not math.isfinite(x) or x < 0 for x in [*left, *right]):
        raise ValueError("CPC requires equally sized finite nonnegative vectors")
    total = sum(left) + sum(right)
    if total == 0:
        raise ValueError("CPC denominator is zero")
    return 2 * sum(min(a, b) for a, b in zip(left, right)) / total
