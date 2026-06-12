"""Unit tests for the cached dict-relationship registry and its resolution helpers."""
from typing import get_args, get_origin
from unittest.mock import MagicMock

import pytest
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job, JobBase
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.services.object_linking_service import (
    dict_attr_names_for_class, dict_membership_specs, dict_relationship_registry, resolve_dict_attr)


def test_registry_matches_every_explainable_object_dict_init_annotation():
    """The cached map must cover exactly the ExplainableObjectDict[X] init annotations of all classes."""
    expected = set()
    for parent_class in MODELING_OBJECT_CLASSES_DICT.values():
        for attr_name, param in get_init_signature_params(parent_class).items():
            annotation_origin = get_origin(param.annotation)
            if isinstance(annotation_origin, type) and issubclass(annotation_origin, ExplainableObjectDict):
                type_arg = get_args(param.annotation)[0]
                child_class = MODELING_OBJECT_CLASSES_DICT[type_arg] if isinstance(type_arg, str) else type_arg
                expected.add((parent_class, attr_name, child_class))

    assert set(dict_relationship_registry()) == expected


def test_registry_covers_the_known_weighted_relationships():
    assert {
        (UsageJourney, "uj_steps", UsageJourneyStep),
        (UsageJourneyStep, "jobs", JobBase),
        (RecurrentServerNeed, "jobs", JobBase),
        (EdgeDeviceGroup, "sub_group_counts", EdgeDeviceGroup),
        (EdgeDeviceGroup, "edge_device_counts", EdgeDevice),
    } <= set(dict_relationship_registry())


@pytest.mark.parametrize(
    ("parent_class", "key_class", "expected_attr"),
    [
        (UsageJourney, UsageJourneyStep, "uj_steps"),
        (UsageJourneyStep, Job, "jobs"),
        (RecurrentServerNeed, Job, "jobs"),
        (EdgeDeviceGroup, EdgeDeviceGroup, "sub_group_counts"),
        (EdgeDeviceGroup, EdgeDevice, "edge_device_counts"),
    ],
)
def test_resolve_dict_attr_per_parent_and_key_class(parent_class, key_class, expected_attr):
    assert resolve_dict_attr(MagicMock(spec=parent_class), MagicMock(spec=key_class)) == expected_attr


def test_resolve_dict_attr_rejects_unmatched_pair():
    journey = UsageJourney("Journey", uj_steps=[])
    other_journey = UsageJourney("Other journey", uj_steps=[])
    with pytest.raises(ValueError, match="cannot be unambiguously linked"):
        resolve_dict_attr(journey, other_journey)


def test_dict_membership_specs_for_jobs_cover_steps_and_recurrent_server_needs():
    assert set(dict_membership_specs(Job)) == {(UsageJourneyStep, "jobs"), (RecurrentServerNeed, "jobs")}


def test_dict_membership_specs_for_steps_and_devices():
    assert set(dict_membership_specs(UsageJourneyStep)) == {(UsageJourney, "uj_steps")}
    assert set(dict_membership_specs(EdgeDevice)) == {(EdgeDeviceGroup, "edge_device_counts")}


def test_dict_attr_names_for_class():
    assert dict_attr_names_for_class(EdgeDeviceGroup) == ["sub_group_counts", "edge_device_counts"]
    assert dict_attr_names_for_class(UsageJourney) == ["uj_steps"]
    assert dict_attr_names_for_class(Job) == []
