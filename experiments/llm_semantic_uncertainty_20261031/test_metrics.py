import math

import pytest

from metrics import empirical_entropy, modal_consistency, cpc, validate_profile, cluster_from_entailments


def test_entropy_and_consistency_for_distinct_and_identical_meanings():
    assert empirical_entropy([0] * 10) == 0
    assert modal_consistency([0] * 10) == 1
    assert empirical_entropy([0, 0, 1, 1]) == pytest.approx(math.log(2))
    assert modal_consistency([0, 0, 1, 1]) == 0.5
    with pytest.raises(ValueError):
        empirical_entropy([])


def test_semantic_clustering_requires_both_entailment_directions():
    pairs = {(0, 1): True, (1, 0): False, (0, 2): True, (2, 0): True,
             (1, 2): False, (2, 1): False}
    assert cluster_from_entailments(3, pairs) == [0, 1, 0]


def test_profile_validation_rejects_invalid_coefficients_and_missing_fields():
    profile = dict(dominant_semantic="residential", production_multiplier=1.1,
                   attraction_weight=0.9, free_flow_cost_factor=1.0, summary="Residential area.")
    assert validate_profile(profile) == profile
    with pytest.raises(ValueError):
        validate_profile(dict(profile, free_flow_cost_factor=0.1))
    with pytest.raises(ValueError):
        validate_profile(dict(profile, production_multiplier=True))
    with pytest.raises(ValueError):
        validate_profile({})


def test_cpc_does_not_conflate_shape_stability_with_observed_accuracy():
    assert cpc([0.2, 0.8], [0.2, 0.8]) == pytest.approx(1)
    assert cpc([1, 0], [0, 1]) == 0
    with pytest.raises(ValueError):
        cpc([1, -1], [1, 0])
