"""Unit tests for the cached dict-relationship registry and its resolution helpers."""
from unittest.mock import MagicMock

import pytest
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job, JobBase
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep

from model_builder.domain.services.object_linking_service import (
    dict_attr_names_for_class, dict_membership_specs, dict_relationship_registry, resolve_dict_attr)


def test_registry_is_exactly_the_known_weighted_relationships():
    """Exact pin: a new (or dropped) `ExplainableObjectDict[X]` init annotation in the library must
    surface as a deliberate update here (and bring its wording in `field_ui_config.json` — see the
    membership-wording consistency test)."""
    assert set(dict_relationship_registry()) == {
        (UsageJourney, "uj_steps", UsageJourneyStep),
        (UsageJourneyStep, "jobs", JobBase),
        (RecurrentServerNeed, "jobs", JobBase),
        (EdgeDeviceGroup, "sub_group_counts", EdgeDeviceGroup),
        (EdgeDeviceGroup, "edge_device_counts", EdgeDevice),
    }


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
    with pytest.raises(ValueError, match="cannot be linked into any dict attribute"):
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
