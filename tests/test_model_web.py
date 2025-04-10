import unittest
from unittest.mock import MagicMock
import pandas as pd
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities, EmptyExplainableObject

from model_builder.model_web import ModelWeb
import pint_pandas

from efootprint.constants.units import u

class TestModelWeb(unittest.TestCase):
    def setUp(self):
        self.model_web = ModelWeb.__new__(ModelWeb)

        self.model_web.system = MagicMock()
        self.model_web.system.total_energy_footprints = {
            "Servers": pd.DataFrame(
                {"value": [1, 2]}, index=pd.date_range("2023-01-01 00:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Storage": pd.DataFrame(
                {"value": [3, 4]}, index=pd.date_range("2023-01-01 01:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Devices": pd.DataFrame(
                {"value": [5, 6]}, index=pd.date_range("2023-01-02 02:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Network": pd.DataFrame(
                {"value": [7, 8]}, index=pd.date_range("2023-01-01 03:00", periods=2, freq='h'), dtype="pint[kg]")
        }
        self.model_web.system.total_fabrication_footprints = {
            "Servers": pd.DataFrame(
                {"value": [9, 10]}, index=pd.date_range("2023-01-01 00:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Storage": pd.DataFrame(
                {"value": [11, 12]}, index=pd.date_range("2023-01-01 01:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Devices": pd.DataFrame(
                {"value": [13, 14]}, index=pd.date_range("2023-01-02 02:00", periods=2, freq='h'), dtype="pint[kg]"),
            "Network": EmptyExplainableObject()
        }

        for footprint_dict in [
            self.model_web.system.total_energy_footprints, self.model_web.system.total_fabrication_footprints]:
            for key, df in footprint_dict.items():
                if not isinstance(df, EmptyExplainableObject):
                    footprint_dict[key] = ExplainableHourlyQuantities(df, label="test")

    def test_get_reindexed_system_energy_and_fabrication_footprint(self):
        energy_footprints, fabrication_footprints, combined_index = (
            self.model_web.get_reindexed_system_energy_and_fabrication_footprint_as_df_dict())

        # Check if the indices are correctly reindexed
        ref_combined_index = pd.date_range("2023-01-01 00:00", periods=28, freq='h')
        for df in energy_footprints.values():
            self.assertTrue(df.index.equals(ref_combined_index))
        for df in fabrication_footprints.values():
            self.assertTrue(df.index.equals(ref_combined_index))

        # Check if the values are correctly filled with 0
        for df in energy_footprints.values():
            self.assertTrue((df.loc[pd.Timestamp("2023-01-01 13:00")]["value"] == 0 * u.kg))
        for df in fabrication_footprints.values():
            self.assertTrue((df.loc[pd.Timestamp("2023-01-01 13:00")]["value"] == 0 * u.kg))

    def test_system_emissions(self):
        emissions = self.model_web.system_emissions

        self.assertListEqual(emissions["dates"], ["2023-01-01", "2023-01-02"])
        self.assertListEqual(emissions["values"]["Servers_and_storage_energy"], [10, 0])
        self.assertListEqual(emissions["values"]["Devices_energy"], [0, 11])
        self.assertListEqual(emissions["values"]["Network_energy"], [15, 0])
        self.assertListEqual(emissions["values"]["Servers_and_storage_fabrication"], [42, 0])
        self.assertListEqual(emissions["values"]["Devices_fabrication"], [0, 27])

if __name__ == '__main__':
    unittest.main()
