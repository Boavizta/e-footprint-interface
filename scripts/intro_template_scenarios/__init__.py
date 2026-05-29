"""Python scenario constructors — the committed source of truth for the
introductory template JSONs.

Each module exposes a ``build_system()`` returning a runnable ``System``.
``scripts/build_intro_templates.py`` runs them through
``efootprint.api_utils.system_to_json`` to (re)generate the committed JSONs.
The build script flips ``_use_name_as_id`` before importing efootprint so the
serialized ids are readable and stable across regenerations.
"""
