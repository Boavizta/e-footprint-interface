"""
Test constants for e-footprint interface tests.
Centralizes commonly used test data to improve maintainability.
"""

# Common test IDs
TEST_SYSTEM_ID = "uuid-system-1"
TEST_SERVER_ID = "uuid-Server-1"
TEST_STORAGE_ID = "uuid-Default-SSD-storage-1"
TEST_USAGE_JOURNEY_ID = "uuid-Daily-video-usage"
TEST_UJ_STEP_ID = "uuid-20-min-streaming-on-Youtube"

# Test object names
TEST_UJ_NAME = "Test UJ"
TEST_UJS_NAME = "Test UJS"
TEST_SERVER_NAME = "Test Server"
TEST_SERVICE_NAME = "Test Service"
TEST_JOB_NAME = "Test Job"
TEST_UP_NAME = "Test Usage Pattern"

# Common form data templates
USAGE_PATTERN_FORM_DATA = {
    "csrfmiddlewaretoken": "test_token",
    "UsagePatternFromForm_start_date": "2025-02-01",
    "UsagePatternFromForm_modeling_duration_value": "5",
    "UsagePatternFromForm_modeling_duration_unit": "month",
    "UsagePatternFromForm_net_growth_rate_in_percentage": "10",
    "UsagePatternFromForm_net_growth_rate_timespan": "month",
    "UsagePatternFromForm_initial_usage_journey_volume": "10000",
    "UsagePatternFromForm_initial_usage_journey_volume_timespan": "month",
}

EDGE_USAGE_PATTERN_FORM_DATA = {
    "csrfmiddlewaretoken": "test_token",
    "EdgeUsagePatternFromForm_start_date": "2025-02-01",
    "EdgeUsagePatternFromForm_modeling_duration_value": "5",
    "EdgeUsagePatternFromForm_modeling_duration_unit": "month",
    "EdgeUsagePatternFromForm_net_growth_rate_in_percentage": "10",
    "EdgeUsagePatternFromForm_net_growth_rate_timespan": "month",
    "EdgeUsagePatternFromForm_initial_usage_journey_volume": "10000",
    "EdgeUsagePatternFromForm_initial_usage_journey_volume_timespan": "month",
}

WEB_APPLICATION_FORM_DATA = {
    "type_object_available": "WebApplication",
    "WebApplication_technology": "php-symfony",
    "WebApplication_base_ram_consumption": "2",
    "WebApplication_bits_per_pixel": "0.1",
    "WebApplication_static_delivery_cpu_cost": "4.0",
    "WebApplication_ram_buffer_per_user": "50",
}

WEB_APPLICATION_JOB_FORM_DATA = {
    "type_object_available": "WebApplicationJob",
    "WebApplicationJob_implementation_details": "aggregation-code-side",
    "WebApplicationJob_data_transferred": "150",
    "WebApplicationJob_data_stored": "100",
}

GPU_SERVER_FORM_DATA = {
    "type_object_available": "GPUServer",
    "GPUServer_average_carbon_intensity": "100",
    "GPUServer_average_carbon_intensity_unit": "g/kWh",
    "GPUServer_base_compute_consumption": "0",
    "GPUServer_base_compute_consumption_unit": "gpu",
    "GPUServer_base_ram_consumption": "0",
    "GPUServer_base_ram_consumption_unit": "GB",
    "GPUServer_carbon_footprint_fabrication_per_gpu": "150",
    "GPUServer_carbon_footprint_fabrication_per_gpu_unit": "kg/gpu",
    "GPUServer_carbon_footprint_fabrication_without_gpu": "2500",
    "GPUServer_carbon_footprint_fabrication_without_gpu_unit": "kg",
    "GPUServer_compute": "4",
    "GPUServer_compute_unit": "gpu",
    "GPUServer_gpu_idle_power": "50",
    "GPUServer_gpu_idle_power_unit": "W/gpu",
    "GPUServer_gpu_power": "400",
    "GPUServer_gpu_power_unit": "W/gpu",
    "GPUServer_lifespan": "6",
    "GPUServer_lifespan_unit": "yr",
    "GPUServer_power_usage_effectiveness": "1.2",
    "GPUServer_ram_per_gpu": "80",
    "GPUServer_ram_per_gpu_unit": "GB/gpu",
    "GPUServer_server_type": "serverless",
    "GPUServer_utilization_rate": "1",
    "storage_form_data": '{"type_object_available":"Storage","Storage_name":"Storage 1",'
                        '"Storage_data_replication_factor":"3","Storage_data_storage_duration":"5",'
                        '"Storage_data_storage_duration_unit":"yr","Storage_storage_capacity":"1",'
                        '"Storage_storage_capacity_unit":"TB",'
                        '"Storage_carbon_footprint_fabrication_per_storage_capacity":"160",'
                        '"Storage_carbon_footprint_fabrication_per_storage_capacity_unit":"kg/TB",'
                        '"Storage_power_per_storage_capacity":"1.3",'
                        '"Storage_power_per_storage_capacity_unit":"W/TB","Storage_idle_power":"0",'
                        '"Storage_idle_power_unit":"W","Storage_base_storage_need":"0",'
                        '"Storage_base_storage_need_unit":"TB","Storage_lifespan":"6",'
                        '"Storage_lifespan_unit":"yr"}',
}

EDGE_DEVICE_FORM_DATA = {
    "type_object_available": "EdgeComputer",
    "EdgeComputer_base_compute_consumption": "0",
    "EdgeComputer_base_compute_consumption_unit": "cpu_core",
    "EdgeComputer_base_ram_consumption": "0",
    "EdgeComputer_base_ram_consumption_unit": "GB",
    "EdgeComputer_carbon_footprint_fabrication": "150",
    "EdgeComputer_carbon_footprint_fabrication_unit": "kg",
    "EdgeComputer_compute": "4",
    "EdgeComputer_compute_unit": "cpu_core",
    "EdgeComputer_idle_power": "50",
    "EdgeComputer_idle_power_unit": "W",
    "EdgeComputer_power": "400",
    "EdgeComputer_power_unit": "W",
    "EdgeComputer_lifespan": "6",
    "EdgeComputer_lifespan_unit": "yr",
    "storage_form_data": '{"type_object_available":"EdgeStorage","EdgeStorage_name":"EdgeStorage 1",'
                        '"EdgeStorage_storage_capacity":"1",'
                        '"EdgeStorage_storage_capacity_unit":"TB",'
                        '"EdgeStorage_carbon_footprint_fabrication_per_storage_capacity":"160",'
                        '"EdgeStorage_carbon_footprint_fabrication_per_storage_capacity_unit":"kg/TB",'
                        '"EdgeStorage_power_per_storage_capacity":"1.3",'
                        '"EdgeStorage_power_per_storage_capacity_unit":"W/TB","EdgeStorage_idle_power":"0",'
                        '"EdgeStorage_idle_power_unit":"W","EdgeStorage_base_storage_need":"0",'
                        '"EdgeStorage_base_storage_need_unit":"TB","EdgeStorage_lifespan":"6",'
                        '"EdgeStorage_lifespan_unit":"yr"}',
}

# System data templates
MINIMAL_SYSTEM_DATA = {
    "efootprint_version": "9.1.4",
    "System": {
        TEST_SYSTEM_ID: {
            "name": "system 1",
            "id": TEST_SYSTEM_ID,
            "usage_patterns": []
        }
    }
}

# HTTP status codes for better readability
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
