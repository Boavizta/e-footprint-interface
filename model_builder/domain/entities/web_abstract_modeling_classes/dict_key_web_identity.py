from dataclasses import dataclass

from efootprint.abstract_modeling_classes.modeling_object import css_escape


@dataclass(frozen=True)
class DictKeyWebIdentity:
    """Template- and route-facing identity for a computed-dict key."""

    efootprint_id: str
    name: str

    @classmethod
    def from_key(cls, key: object) -> "DictKeyWebIdentity":
        key_name = str(key)
        return cls(efootprint_id=getattr(key, "id", key_name), name=key_name)

    @property
    def route_id(self) -> str:
        return css_escape(self.efootprint_id)

    def matches(self, candidate_id: str) -> bool:
        return candidate_id in (self.efootprint_id, self.route_id)
