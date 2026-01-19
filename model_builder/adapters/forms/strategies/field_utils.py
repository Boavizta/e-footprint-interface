"""Utility functions for field transformations and manipulations."""


def apply_field_defaults(form_sections: list, field_defaults: dict) -> None:
    """Apply field default values based on config.

    Args:
        form_sections: List of form sections to modify in place
        field_defaults: Dict mapping field names to default config:
            - 'default_by_label': Set selected value by matching option label
    """
    for section in form_sections:
        for field in section.get('fields', []):
            attr_name = field.get('attr_name')
            if attr_name in field_defaults:
                default_config = field_defaults[attr_name]
                if 'default_by_label' in default_config:
                    label_to_find = default_config['default_by_label']
                    for option in field.get('options', []):
                        if option.get('label') == label_to_find:
                            field['selected'] = option['value']
                            break


def apply_field_transforms(form_sections: list, field_transforms: dict) -> None:
    """Apply field transformations to form sections based on config.

    Args:
        form_sections: List of form sections to modify in place
        field_transforms: Dict mapping field names to transform config:
            - 'multiselect_to_single': Convert multiselect list to single select
    """
    for section in form_sections:
        apply_field_transforms_to_fields(section.get('fields', []), field_transforms)


def apply_field_transforms_to_fields(fields: list, field_transforms: dict) -> None:
    """Apply field transformations to a list of fields.

    Args:
        fields: List of field dicts to modify in place
        field_transforms: Dict mapping field names to transform config
    """
    for field in fields:
        attr_name = field.get('attr_name')
        if attr_name in field_transforms:
            transform_config = field_transforms[attr_name]
            if transform_config.get('multiselect_to_single'):
                convert_multiselect_to_single(field)


def convert_multiselect_to_single(field: dict) -> None:
    """Convert a multiselect field to a single select field.

    Takes options from 'unselected' (for creation) or combines
    'selected' + 'unselected' (for edition).
    """
    selected = field.get('selected', [])
    if len(selected) == 0:
        # Creation context: use unselected options
        options = field.get('unselected', [])
        field.update({
            'input_type': 'select_object',
            'options': options,
            'selected': options[0]['value'] if options else None
        })
    else:
        # Edition context: combine selected + unselected
        unselected = field.get('unselected', [])
        options = selected + unselected
        field.update({
            'input_type': 'select_object',
            'options': options,
            'selected': selected[0]['value']
        })

    field.pop('unselected', None)


def has_meaningful_dynamic_data(dynamic_form_data: dict) -> bool:
    """Check if dynamic_form_data has meaningful content worth including.

    Returns False for trivial cases like single-class forms with no dynamic lists/selects.
    This avoids breaking forms where the JS expects meaningful switch data.
    """
    if not dynamic_form_data:
        return False

    switch_values = dynamic_form_data.get('switch_values', [])
    dynamic_lists = dynamic_form_data.get('dynamic_lists', [])
    dynamic_selects = dynamic_form_data.get('dynamic_selects', [])

    # Meaningful if: multiple switch values, or has dynamic lists, or has dynamic selects
    has_multiple_classes = len(switch_values) > 1
    has_dynamic_lists = len(dynamic_lists) > 0
    has_dynamic_selects = len(dynamic_selects) > 0

    return has_multiple_classes or has_dynamic_lists or has_dynamic_selects
