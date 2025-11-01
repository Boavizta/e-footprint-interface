# Refactoring Plan: Move Timeseries Generation from FromForm Classes to ExplainableQuantity Subclasses

## Overview
Replace the "FromForm" wrapper pattern with new ExplainableHourlyQuantities and ExplainableRecurrentQuantities subclasses that handle form-based timeseries generation internally, managed automatically by the generate_dynamic_form function.

## Phase 1: Create New Timeseries Extension Classes

### 1.1 Create ExplainableHourlyQuantitiesFromFormInputs
**File**: `model_builder/efootprint_extensions/explainable_hourly_quantities_from_form_inputs.py`

- Register with matcher: `lambda d: "form_inputs" in d and d["form_inputs"]["type"] == "growth_based"`
- **Store in JSON**:
  - `form_inputs`: dict with `type: "growth_based"`, `start_date` (UTC string), `modeling_duration_value`, `modeling_duration_unit`, `initial_volume`, `initial_volume_unit`, `initial_volume_timespan`, `net_growth_rate_in_percentage`, `net_growth_rate_timespan`
  - Also store computed `compressed_values`, `unit`, `start_date`, `timezone` (for parent class compatibility)
- **Lazy evaluation**: Check if `_value` is None; if so, recompute from `form_inputs` using growth rate logic (from TimeseriesForm.generate_hourly_starts)
- **Cache**: Store computed timeseries in `_value` after first computation
- **Methods**: `from_json_dict()`, `to_json()`, `__init__(form_inputs_dict, **kwargs)`
- **No local_timezone logic**: Use UTC start_date directly

### 1.2 Create ExplainableRecurrentQuantitiesFromConstant
**File**: `model_builder/efootprint_extensions/explainable_recurrent_quantities_from_constant.py`

- Register with matcher: `lambda d: "constant_value" in d and "constant_unit" in d`
- **Store in JSON**: `constant_value`, `constant_unit`, plus computed `recurring_values`, `unit`
- **Lazy evaluation**: Generate 168-element array when `.value` first accessed
- **Cache**: Store in `_value`
- **Methods**: `from_json_dict()`, `to_json()`, `__init__(constant_value, constant_unit, **kwargs)`

## Phase 2: Update Dynamic Form Generation

### 2.1 Modify generate_dynamic_form in class_structure.py (lines 81-225)

**Key changes**:

1. **Detection logic** - When encountering `ExplainableHourlyQuantities` or `ExplainableRecurrentQuantities` annotation:
   ```python
   # Check what type of timeseries this is based on the default value
   if attr_name in default_values:
       default_timeseries = default_values[attr_name]
       # Check class hierarchy to determine if it's form-editable
       if isinstance(default_timeseries, ExplainableHourlyQuantitiesFromFormInputs):
           input_type = "hourly_quantities_from_growth"
           # Extract form_inputs from default value
       elif isinstance(default_timeseries, ExplainableRecurrentQuantitiesFromConstant):
           input_type = "recurrent_quantities_from_constant"
           # Extract constant value
       else:
           # Base efootprint class - read-only display
           input_type = "timeseries_input" or "recurrent_timeseries_input"
   ```

2. **Form field structure** for editable timeseries:
   - `hourly_quantities_from_growth`: nested fields for start_date, modeling_duration (value+unit), initial_volume (value+unit+timespan), growth_rate (value+timespan)
   - `recurrent_quantities_from_constant`: single number input with unit

3. **Field ordering**:
   - Separate fields into `non_timeseries_fields` and `timeseries_fields` lists
   - Preserve original order within each group
   - Return: `non_timeseries_fields + timeseries_fields`

### 2.2 Create New Form Field Templates

**Template**: `model_builder/templates/model_builder/side_panels/dynamic_form_fields/hourly_quantities_from_growth.html`
- Replicate structure from current `timeseries_form.html`
- All inputs: start_date (datepicker), modeling_duration (value+unit select), initial_volume (value+unit+timespan select), growth_rate (value+timespan select)
- Include flatpickr initialization
- Include source tracking for each sub-input
- Include dynamic select logic for growth rate timespan (depends on volume timespan)

**Template**: `model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html`
- Number input with unit display
- Source tracking

**Keep existing templates** for read-only display:
- `timeseries_input.html` - unchanged (for base ExplainableHourlyQuantities)
- `recurrent_timeseries_input.html` - unchanged (for base ExplainableRecurrentQuantities)

## Phase 3: Update Object Creation/Edition Logic

### 3.1 Modify object_creation_and_edition_utils.py

Update `create_efootprint_obj_from_post_data()` to:
- Detect compound timeseries inputs in POST data
- Construct `form_inputs` dict from POST fields
- Create ExplainableHourlyQuantitiesFromFormInputs or ExplainableRecurrentQuantitiesFromConstant instances
- Pass to modeling object constructors as init parameters

### 3.2 Handle Edition
- When editing, form should display the `form_inputs` values stored in JSON
- User edits inputs ’ new timeseries object created with updated form_inputs

## Phase 4: Remove FromForm Classes

### 4.1 Delete Files
- `model_builder/efootprint_extensions/usage_pattern_from_form.py`
- `model_builder/efootprint_extensions/edge_usage_pattern_from_form.py`
- `model_builder/efootprint_extensions/recurrent_edge_workload_from_form.py`
- `model_builder/efootprint_extensions/recurrent_edge_process_from_form.py`
- `model_builder/efootprint_extensions/timeseries_form.py`
- `model_builder/templates/model_builder/side_panels/usage_pattern/timeseries_form.html`

### 4.2 Remove Web Wrapper Classes & Special Logic
- Remove `UsagePatternFromFormWeb`, `EdgeUsagePatternFromFormWeb`
- Remove `UsagePatternFromFormWebBaseClass` from `usage_pattern_web_base_class.py`
- Remove `generate_attributes_to_skip_in_forms()` function
- Remove special `add_template` and `edit_template` overrides
- Keep base `UsagePatternWeb`, `EdgeUsagePatternWeb` (base classes remain usable via Python API)

### 4.3 Update Class Registries
- Remove FromForm classes from `all_efootprint_classes.py` ’ `MODELING_OBJECT_CLASSES_DICT`
- Remove FromForm mappings from `efootprint_to_web_mapping.py`
- Add new extension classes to registries

### 4.4 Update Configuration Files
- `form_type_object.json`: Remove FromForm entries, keep base class entries
- `form_fields_reference.json`: Add/update entries for new compound form fields

## Phase 5: Testing & Validation

### 5.1 Core Functionality Tests
- Create UsagePattern with growth-based hourly quantities via form
- Edit existing UsagePattern, verify form displays original form inputs
- Create EdgeUsagePattern (same tests)
- Create RecurrentEdgeWorkload with constant value
- Create RecurrentEdgeProcess with constant values
- Load from JSON, verify lazy evaluation works correctly
- Verify cached values don't recompute unnecessarily

### 5.2 Backward Compatibility
- Base UsagePattern/EdgeUsagePattern still work when created directly via Python API with pre-computed timeseries
- These show as read-only in forms (using existing timeseries_input.html template)

### 5.3 Future Extensibility
- Verify new timeseries generation methods can be added by just creating new ExplainableHourlyQuantities subclasses
- No changes needed to FromForm wrapper pattern

## Key Implementation Details

### Detection Strategy (Critical)
```python
# In generate_dynamic_form, when annotation is ExplainableHourlyQuantities:
from model_builder.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import ExplainableHourlyQuantitiesFromFormInputs

if issubclass(annotation, ExplainableHourlyQuantities):
    default = default_values[attr_name]

    # Check instance type to determine form input type
    if type(default).__name__ == 'ExplainableHourlyQuantitiesFromFormInputs':
        input_type = "hourly_quantities_from_growth"
        # extract form_inputs dict from default
    else:
        # Base class or other subclass ’ read-only
        input_type = "timeseries_input"
```

### Field Ordering (Critical)
```python
# At end of generate_dynamic_form:
non_timeseries_fields = []
timeseries_fields = []

for field in structure_fields:
    if field["input_type"] in ["hourly_quantities_from_growth", "recurrent_quantities_from_constant",
                                "timeseries_input", "recurrent_timeseries_input"]:
        timeseries_fields.append(field)
    else:
        non_timeseries_fields.append(field)

structure_fields = non_timeseries_fields + timeseries_fields
# Same for structure_fields_advanced
```

### No Local Timezone Logic
- ExplainableHourlyQuantitiesFromFormInputs uses UTC start_date directly
- No need for `update_local_timezone_start_date()` method
- Simpler computation in generate_hourly_values()

## Benefits
-  No class explosion
-  Automatic form generation
-  Maintainable and extensible
-  Backward compatible with base classes
-  Future-proof for new generation methods

## Migration Strategy
- Version upgrade handler will be implemented together at the end
- Focus on new implementation first