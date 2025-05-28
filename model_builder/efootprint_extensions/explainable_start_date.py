from datetime import datetime

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


@ExplainableObject.register_subclass(lambda d: "type" in d and d["type"] == "date")
class ExplainableStartDate(ExplainableObject):
    @classmethod
    def from_json_dict(cls, d):
        source = d.get("source") if d.get("source", None) else None
        return cls(datetime.strptime(d["value"], "%Y-%m-%d"), label=d["label"], source=source)

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {"type": "date", "value": datetime.strftime(self.value, "%Y-%m-%d")}
        output_dict.update(super().to_json(with_calculated_attributes_data))
        return output_dict
