import unittest
from copy import deepcopy

from model_builder.version_upgrade_handlers import upgrade_interface_version_pre_14


class TestVersionUpgradeHandlers(unittest.TestCase):
    def test_upgrade_usage_pattern_from_form(self):
        """Test transformation of UsagePatternFromForm to UsagePattern."""
        input_dict = {
            "efootprint_version": "13.0.0",
            "UsagePatternFromForm": {
                "uuid-test-pattern": {
                    "name": "Test Usage Pattern",
                    "id": "uuid-test-pattern",
                    "start_date": {
                        "label": "start date from user data",
                        "value": "2026-01-01",
                        "source": {"name": "user data", "link": None}
                    },
                    "modeling_duration_value": {
                        "label": "modeling duration value",
                        "value": 3.0,
                        "unit": "dimensionless",
                        "source": {"name": "user data", "link": None}
                    },
                    "modeling_duration_unit": {
                        "label": "modeling duration unit",
                        "value": "year",
                        "source": {"name": "user data", "link": None}
                    },
                    "initial_usage_journey_volume": {
                        "label": "initial usage journey volume",
                        "value": 3000.0,
                        "unit": "dimensionless",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "initial_usage_journey_volume_timespan": {
                        "label": "initial usage journey volume timespan",
                        "value": "year",
                        "source": {"name": "user data", "link": None}
                    },
                    "net_growth_rate_in_percentage": {
                        "label": "net growth rate in percentage",
                        "value": 10.0,
                        "unit": "dimensionless",
                        "source": {"name": "user data", "link": None}
                    },
                    "net_growth_rate_timespan": {
                        "label": "net growth rate timespan",
                        "value": "year",
                        "source": {"name": "user data", "link": None}
                    },
                    "usage_journey": "uuid-journey",
                    "devices": ["uuid-device"],
                    "network": "uuid-network",
                    "country": "uuid-country"
                }
            }
        }

        expected_dict = {
            "efootprint_version": "13.0.0",
            "UsagePattern": {
                "uuid-test-pattern": {
                    "name": "Test Usage Pattern",
                    "id": "uuid-test-pattern",
                    "hourly_usage_journey_starts": {
                        "form_inputs": {
                            "start_date": "2026-01-01",
                            "modeling_duration_value": 3.0,
                            "modeling_duration_unit": "year",
                            "initial_volume": 3000.0,
                            "initial_volume_timespan": "year",
                            "net_growth_rate_in_percentage": 10.0,
                            "net_growth_rate_timespan": "year",
                        },
                        "label": "hourly_usage_journey_starts in Test Usage Pattern",
                        "source": {"name": "user data", "link": None}
                    },
                    "usage_journey": "uuid-journey",
                    "devices": ["uuid-device"],
                    "network": "uuid-network",
                    "country": "uuid-country"
                }
            }
        }

        result = upgrade_interface_version_pre_14(deepcopy(input_dict))
        self.assertEqual(result, expected_dict)
        self.assertNotIn("UsagePatternFromForm", result)
        self.assertIn("UsagePattern", result)

    def test_upgrade_edge_usage_pattern_from_form(self):
        """Test transformation of EdgeUsagePatternFromForm to EdgeUsagePattern."""
        input_dict = {
            "efootprint_version": "13.0.0",
            "EdgeUsagePatternFromForm": {
                "uuid-edge-pattern": {
                    "name": "Test Edge Usage Pattern",
                    "id": "uuid-edge-pattern",
                    "start_date": {
                        "label": "start date",
                        "value": "2025-06-01",
                        "source": {"name": "user data", "link": None}
                    },
                    "modeling_duration_value": {
                        "label": "modeling duration value",
                        "value": 6.0,
                        "unit": "dimensionless",
                        "source": {"name": "user data", "link": None}
                    },
                    "modeling_duration_unit": {
                        "label": "modeling duration unit",
                        "value": "month",
                        "source": {"name": "user data", "link": None}
                    },
                    "initial_edge_usage_journey_volume": {
                        "label": "initial volume",
                        "value": 5000.0,
                        "unit": "dimensionless",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "initial_edge_usage_journey_volume_timespan": {
                        "label": "initial volume timespan",
                        "value": "month",
                        "source": {"name": "user data", "link": None}
                    },
                    "net_growth_rate_in_percentage": {
                        "label": "growth rate",
                        "value": 5.0,
                        "unit": "dimensionless",
                        "source": {"name": "user data", "link": None}
                    },
                    "net_growth_rate_timespan": {
                        "label": "growth timespan",
                        "value": "month",
                        "source": {"name": "user data", "link": None}
                    },
                    "edge_usage_journey": "uuid-edge-journey"
                }
            }
        }

        expected_dict = {
            "efootprint_version": "13.0.0",
            "EdgeUsagePattern": {
                "uuid-edge-pattern": {
                    "name": "Test Edge Usage Pattern",
                    "id": "uuid-edge-pattern",
                    "hourly_edge_usage_journey_starts": {
                        "form_inputs": {
                            "start_date": "2025-06-01",
                            "modeling_duration_value": 6.0,
                            "modeling_duration_unit": "month",
                            "initial_volume": 5000.0,
                            "initial_volume_timespan": "month",
                            "net_growth_rate_in_percentage": 5.0,
                            "net_growth_rate_timespan": "month",
                        },
                        "label": "hourly_edge_usage_journey_starts in Test Edge Usage Pattern",
                        "source": {"name": "user data", "link": None}
                    },
                    "edge_usage_journey": "uuid-edge-journey"
                }
            }
        }

        result = upgrade_interface_version_pre_14(deepcopy(input_dict))
        self.assertEqual(result, expected_dict)
        self.assertNotIn("EdgeUsagePatternFromForm", result)
        self.assertIn("EdgeUsagePattern", result)

    def test_upgrade_recurrent_edge_process_from_form(self):
        """Test transformation of RecurrentEdgeProcessFromForm to RecurrentEdgeProcess."""
        input_dict = {
            "efootprint_version": "13.0.0",
            "RecurrentEdgeProcessFromForm": {
                "uuid-edge-process": {
                    "name": "Test Edge Process",
                    "id": "uuid-edge-process",
                    "constant_compute_needed": {
                        "label": "constant compute needed",
                        "value": 2.5,
                        "unit": "cpu_core",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "constant_ram_needed": {
                        "label": "constant ram needed",
                        "value": 4.0,
                        "unit": "GB_ram",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "constant_storage_needed": {
                        "label": "constant storage needed",
                        "value": 100.0,
                        "unit": "GB",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "edge_device": "uuid-edge-device"
                }
            }
        }

        expected_dict = {
            "efootprint_version": "13.0.0",
            "RecurrentEdgeProcess": {
                "uuid-edge-process": {
                    "name": "Test Edge Process",
                    "id": "uuid-edge-process",
                    "recurrent_compute_needed": {
                        "form_inputs": {
                            "constant_value": 2.5,
                            "constant_unit": "cpu_core",
                        },
                        "label": "constant compute needed",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "recurrent_ram_needed": {
                        "form_inputs": {
                            "constant_value": 4.0,
                            "constant_unit": "GB_ram",
                        },
                        "label": "constant ram needed",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "recurrent_storage_needed": {
                        "form_inputs": {
                            "constant_value": 100.0,
                            "constant_unit": "GB",
                        },
                        "label": "constant storage needed",
                        "source": {"name": "hypothesis", "link": None}
                    },
                    "edge_device": "uuid-edge-device"
                }
            }
        }

        result = upgrade_interface_version_pre_14(deepcopy(input_dict))
        self.assertEqual(result, expected_dict)
        self.assertNotIn("RecurrentEdgeProcessFromForm", result)
        self.assertIn("RecurrentEdgeProcess", result)

    def test_upgrade_recurrent_workload_from_form(self):
        """Test transformation of RecurrentWorkloadFromForm to RecurrentWorkload."""
        input_dict = {
            "efootprint_version": "13.0.0",
            "RecurrentWorkloadFromForm": {
                "uuid-workload": {
                    "name": "Test Workload",
                    "id": "uuid-workload",
                    "constant_workload": {
                        "label": "constant workload",
                        "value": 1000.0,
                        "unit": "occurrence",
                        "source": {"name": "user data", "link": None},
                    },
                    "edge_device": "uuid-edge-device"
                }
            }
        }

        expected_dict = {
            "efootprint_version": "13.0.0",
            "RecurrentWorkload": {
                "uuid-workload": {
                    "name": "Test Workload",
                    "id": "uuid-workload",
                    "recurrent_workload": {
                        "form_inputs": {
                            "constant_value": 1000.0,
                            "constant_unit": "occurrence",
                        },
                        "label": "constant workload",
                        "source": {"name": "user data", "link": None},
                    },
                    "edge_device": "uuid-edge-device"
                }
            }
        }

        result = upgrade_interface_version_pre_14(deepcopy(input_dict))
        self.assertEqual(result, expected_dict)
        self.assertNotIn("RecurrentWorkloadFromForm", result)
        self.assertIn("RecurrentWorkload", result)


if __name__ == "__main__":
    unittest.main()
