beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe('Test edge objects', () => {
    it('Add an edge device, verify creation, then edit and verify changes', () => {
        let edgeDeviceName = "Test E2E Edge Device";
        let originalRam = "16";
        let updatedRam = "8";
        let originalCompute = "8";
        let updatedCompute = "16";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        // Add edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#type_object_available').select('EdgeComputer');
        cy.get('#EdgeComputer_name').type(edgeDeviceName);
        cy.get('#EdgeComputer_ram').clear().type(originalRam);
        cy.get('#EdgeComputer_compute').clear().type(originalCompute);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", edgeDeviceName).should('have.class', 'list-group-item');

        // Edit the edge device
        cy.getObjectButtonFromObjectTypeAndName("EdgeComputer", edgeDeviceName).click();
        cy.get('#sidePanel').should('be.visible');

        // Verify current values
        cy.get('#EdgeComputer_ram').should('have.value', originalRam);
        cy.get('#EdgeComputer_compute').should('have.value', originalCompute);

        // Make changes
        cy.get('#EdgeComputer_ram').clear().type(updatedRam);
        cy.get('#EdgeComputer_compute').clear().type(updatedCompute);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify changes were saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeComputer", edgeDeviceName).click();
        cy.get('#EdgeComputer_ram').should('have.value', updatedRam);
        cy.get('#EdgeComputer_compute').should('have.value', updatedCompute);
    });

    it('Add edge device with advanced parameters', () => {
        let edgeDeviceName = "Advanced Edge Device";
        let customLifespan = "3";
        let customCarbonFootprint = "100";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        // Add edge device with advanced options
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#type_object_available').select('EdgeComputer');
        cy.get('#EdgeComputer_name').type(edgeDeviceName);

        // Open advanced options
        cy.get('#display-advanced-EdgeComputer').click();
        cy.get('#advanced-EdgeComputer').should('be.visible');

        // Set advanced parameters
        cy.get('#EdgeComputer_lifespan').clear().type(customLifespan);
        cy.get('#EdgeComputer_carbon_footprint_fabrication').clear().type(customCarbonFootprint);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", edgeDeviceName).should('exist');

        // Verify advanced parameters were saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeComputer", edgeDeviceName).click();
        cy.get('#display-advanced-EdgeComputer').click();
        cy.get('#advanced-EdgeComputer').should('be.visible');
        cy.get('#EdgeComputer_lifespan').should('have.value', customLifespan);
        cy.get('#EdgeComputer_carbon_footprint_fabrication').should('have.value', customCarbonFootprint);
    });

    it('Add edge device, edge usage journey, edge function and recurrent edge processes with verification and editing', () => {
        // Edge device setup
        let edgeDeviceName = "Test Edge Device for Journey";
        let edgeRam = "32";
        let edgeCompute = "16";
        let lifespan = "12"

        // Edge usage journey setup
        let edgeUsageJourneyName = "Test Edge Usage Journey";
        let usageSpan = "10";
        let updatedUsageSpan = "11";

        // Edge function setup
        let edgeFunctionName = "Edge Function 1";

        // Recurrent edge process setup
        let recurrentProcess1Name = "Background Process 1";
        let compute1 = "2.5";
        let ram1 = "4.5";
        let storage1 = "100";
        let updatedCompute1 = "3.5";
        let updatedRam1 = "5.5";

        let recurrentProcess2Name = "Background Process 2";
        let compute2 = "1.5";
        let ram2 = "2.5";
        let storage2 = "50";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        // Step 1: Add edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#type_object_available').select('EdgeComputer');
        cy.get('#EdgeComputer_name').type(edgeDeviceName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get("#EdgeComputer_lifespan").clear().type(lifespan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", edgeDeviceName).should('exist');

        // Step 2: Add edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(edgeUsageJourneyName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).should('exist');

        // Step 3: Add edge function to the edge usage journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).find('div[id^="add-step-to"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#EdgeFunction_name').type(edgeFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge function was created
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).should('exist');

        // Step 4: Add first recurrent edge process to the edge function
        // First expand the edge function card to reveal the add button
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeDeviceNeedBase/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_device').select(edgeDeviceName);
        // When selecting an EdgeComputer, only RecurrentEdgeProcess is available and is auto-selected
        // The type selection is hidden when there's only one option, so we don't need to select it
        cy.get('#RecurrentEdgeProcess_name').type(recurrentProcess1Name);
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').clear().type(compute1);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').clear().type(ram1);
        cy.get('#RecurrentEdgeProcess_recurrent_storage_needed__constant_value').clear().type(storage1);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcess", recurrentProcess1Name).should('exist');

        // Step 5: Add second recurrent edge process
        // The edge function card auto-collapses after adding the first child, so expand it again
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeDeviceNeedBase/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_device').select(edgeDeviceName);
        // When selecting an EdgeComputer, only RecurrentEdgeProcess is available and is auto-selected
        // The type selection is hidden when there's only one option, so we don't need to select it
        cy.get('#RecurrentEdgeProcess_name').type(recurrentProcess2Name);
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').clear().type(compute2);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').clear().type(ram2);
        cy.get('#RecurrentEdgeProcess_recurrent_storage_needed__constant_value').clear().type(storage2);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcess", recurrentProcess2Name).should('exist');

        // Step 6: Edit edge usage journey and verify changes
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
        cy.get('#EdgeUsageJourney_usage_span').should('have.value', usageSpan);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(updatedUsageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge usage journey edit was saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
        cy.get('#EdgeUsageJourney_usage_span').should('have.value', updatedUsageSpan);
        cy.get('#btn-close-side-panel').click();

        // Step 7: Edit first recurrent edge process and verify changes
        // First expand the edge function card to reveal the recurrent edge process button
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeProcess", recurrentProcess1Name).click();
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').should('have.value', compute1);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').should('have.value', ram1);
        cy.get('#RecurrentEdgeProcess_recurrent_storage_needed__constant_value').should('have.value', storage1);

        // Make edits
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').clear().type(updatedCompute1);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').clear().type(updatedRam1);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify recurrent edge process edits were saved
        // Expand the edge function card again to access the recurrent edge process
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeProcess", recurrentProcess1Name).click();
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').should('have.value', updatedCompute1);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').should('have.value', updatedRam1);
        cy.get('#RecurrentEdgeProcess_recurrent_storage_needed__constant_value').should('have.value', storage1);
    });

    it('Create multiple edge usage journeys with edge functions and verify they can share edge devices', () => {
        let firstEdgeComputerName = "First Edge Device";
        let secondEdgeComputerName = "Second Edge Device";
        let firstJourneyName = "First Edge Usage Journey";
        let secondJourneyName = "Second Edge Usage Journey";
        let firstFunctionName = "First Function";
        let secondFunctionName = "Second Function";
        let edgeRam = "16";
        let edgeCompute = "8";
        let usageSpan = "2";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        // Step 1: Create first edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(firstEdgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", firstEdgeComputerName).should('exist');

        // Step 2: Create second edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(secondEdgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", secondEdgeComputerName).should('exist');

        // Step 3: Create first edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(firstJourneyName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).should('exist');

        // Step 4: Add edge function to first journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).find('div[id^="add-step-to"]').click();
        cy.get('#EdgeFunction_name').type(firstFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Step 5: Create second edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(secondJourneyName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).should('exist');

        // Step 6: Add edge function to second journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).find('div[id^="add-step-to"]').click();
        cy.get('#EdgeFunction_name').type(secondFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify both edge functions were created
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", firstFunctionName).should('exist');
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", secondFunctionName).should('exist');
    });

    it('Verify edge function mirroring logic works correctly', () => {
        let edgeComputerName = "Mirror Edge Device";
        let firstJourneyName = "First Mirror Edge Usage Journey";
        let secondJourneyName = "Second Mirror Edge Usage Journey";
        let edgeFunctionName = "Mirrored Edge Function";
        let updatedFunctionName = "Updated Mirrored Function";
        let recurrentProcessName = "Mirrored Recurrent Process";
        let edgeRam = "16";
        let edgeCompute = "8";
        let usageSpan = "3";
        let processCompute = "2.0";
        let processRam = "3.0";
        let processStorage = "50";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get("#btn-reboot-modeling").click();
        cy.get('#model-canva').should('be.visible');

        // Step 1: Create edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(edgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", edgeComputerName).should('exist');

        // Step 2: Create first edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(firstJourneyName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).should('exist');

        // Step 3: Add edge function to first journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).find('div[id^="add-step-to"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#EdgeFunction_name').type(edgeFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge function was created
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).should('exist');

        // Step 4: Add recurrent edge process to edge function
        // First expand the edge function card to reveal the add button
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeDeviceNeedBase/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_device').select(edgeComputerName);
        // When selecting an EdgeComputer, only RecurrentEdgeProcess is available and is auto-selected
        // The type selection is hidden when there's only one option, so we don't need to select it
        cy.get('#RecurrentEdgeProcess_name').type(recurrentProcessName);
        cy.get('#RecurrentEdgeProcess_recurrent_compute_needed__constant_value').clear().type(processCompute);
        cy.get('#RecurrentEdgeProcess_recurrent_ram_needed__constant_value').clear().type(processRam);
        cy.get('#RecurrentEdgeProcess_recurrent_storage_needed__constant_value').clear().type(processStorage);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcess", recurrentProcessName).should('exist');

        // Step 5: Create second edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(secondJourneyName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        // Link to the existing edge function using select_multiple
        cy.get('#select-new-object-EdgeUsageJourney_edge_functions').select(edgeFunctionName);
        cy.get('#add-btn-EdgeUsageJourney_edge_functions').click();
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).should('exist');

        // Step 6: Verify both edge usage journeys have edge function cards with the same name
        // Check first edge usage journey card contains the edge function
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).within(() => {
            cy.contains(edgeFunctionName).should('exist');
        });

        // Check second edge usage journey card contains the edge function
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).within(() => {
            cy.contains(edgeFunctionName).should('exist');
        });

        // Step 7: Edit the name of the edge function and verify mirroring
        cy.getObjectButtonFromObjectTypeAndName("EdgeFunction", edgeFunctionName).click();
        cy.get('#EdgeFunction_name').should('have.value', edgeFunctionName);
        cy.get('#EdgeFunction_name').clear().type(updatedFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Step 8: Verify both edge usage journeys now show the updated function name in their cards
        // Check first edge usage journey card shows updated name
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).within(() => {
            cy.contains(updatedFunctionName).should('exist');
            cy.contains(edgeFunctionName).should('not.exist');
        });

        // Check second edge usage journey card shows updated name
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).within(() => {
            cy.contains(updatedFunctionName).should('exist');
            cy.contains(edgeFunctionName).should('not.exist');
        });
    });

    it("Create EdgeDevice with CPU and RAM components, add RecurrentEdgeDeviceNeed with component needs", () => {
        let edgeDeviceName = "Test Edge Device with Components";
        let cpuComponentName = "Test CPU Component";
        let ramComponentName = "Test RAM Component";
        let edgeUsageJourneyName = "Test Edge Usage Journey";
        let edgeFunctionName = "Test Edge Function";
        let recurrentEdgeDeviceNeedName = "Test Recurrent Edge Device Need";
        let cpuComponentNeedName = "CPU Need";
        let ramComponentNeedName = "RAM Need";
        let cpuNeedValue = "2.0";
        let ramNeedValue = "4.0";
        let updatedCpuNeedValue = "3.0";

        cy.visit("/model_builder/");

        // Step 1: Create EdgeDevice
        cy.get("#btn-add-edge-device").should("be.visible").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#type_object_available").select("EdgeDevice");
        cy.get("#EdgeDevice_name").should("be.visible").type(edgeDeviceName);
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");

        // Verify EdgeDevice was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).should("exist");

        // Step 2: Add CPU component to the EdgeDevice
        // First expand the EdgeDevice accordion to reveal the add button
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('button[hx-get*="/model_builder/open-create-object-panel/EdgeComponent/"]').click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#type_object_available").select("EdgeCPUComponent");
        cy.get("#EdgeCPUComponent_name").should("be.visible").type(cpuComponentName);
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");

        // Verify CPU component was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).within(() => {
            cy.contains(cpuComponentName).should("exist");
        });

        // Step 3: Add RAM component to the EdgeDevice
        // The accordion auto-collapses after adding the first component, so expand it again
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('button[hx-get*="/model_builder/open-create-object-panel/EdgeComponent/"]').click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#type_object_available").select("EdgeRAMComponent");
        cy.get("#EdgeRAMComponent_name").should("be.visible").type(ramComponentName);
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");

        // Verify RAM component was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).within(() => {
            cy.contains(ramComponentName).should("exist");
        });

        // Step 4: Create EdgeUsageJourney
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(edgeUsageJourneyName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).should('exist');

        // Step 5: Add EdgeFunction to the edge usage journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).find('div[id^="add-step-to"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#EdgeFunction_name').type(edgeFunctionName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge function was created
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).should('exist');

        // Step 6: Add RecurrentEdgeDeviceNeed to the edge function
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('.chevron-btn').click();
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeDeviceNeedBase/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_device').select(edgeDeviceName);
        // When selecting an EdgeDevice (not EdgeComputer/EdgeAppliance), only RecurrentEdgeDeviceNeed is available and is auto-selected
        // The type selection is hidden when there's only one option, so we don't need to select it
        cy.get('#RecurrentEdgeDeviceNeed_name').type(recurrentEdgeDeviceNeedName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify RecurrentEdgeDeviceNeed was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).should('exist');

        // Step 7: Add RecurrentEdgeComponentNeed for CPU
        // First expand the EdgeFunction accordion to reveal the RecurrentEdgeDeviceNeed
        // Use specific selector to get only the top-level chevron button (not nested children's chevrons)
        cy.getObjectCardFromObjectTypeAndName("EdgeFunction", edgeFunctionName).first().find('.accordion-header > .chevron-btn').first().click();
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeComponentNeed/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_component').select(cpuComponentName);
        cy.get('#RecurrentEdgeComponentNeed_name').type(cpuComponentNeedName);
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_value').clear().type(cpuNeedValue);
        // Verify the unit was automatically set to cpu_core
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_unit').should('have.value', 'cpu_core');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify CPU component need was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).within(() => {
            cy.contains(cpuComponentNeedName).should('exist');
        });

        // Step 8: Add RecurrentEdgeComponentNeed for RAM
        // The accordion auto-collapses after adding the first component need, so expand RecurrentEdgeDeviceNeed again
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('.accordion-header > .chevron-btn').first().click();
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeComponentNeed/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#edge_component').select(ramComponentName);
        cy.get('#RecurrentEdgeComponentNeed_name').type(ramComponentNeedName);
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_value').clear().type(ramNeedValue);
        // Verify the unit was automatically set to GB_ram
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_unit').should('have.value', 'GB_ram');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify RAM component need was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).within(() => {
            cy.contains(ramComponentNeedName).should('exist');
        });

        // Step 9: Verify unit changes dynamically when switching components
        // Expand RecurrentEdgeDeviceNeed again
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('.accordion-header > .chevron-btn').first().click();
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('button[hx-get="/model_builder/open-create-object-panel/RecurrentEdgeComponentNeed/"]').click();
        cy.get('#sidePanel').should('be.visible');

        // Select CPU and verify unit is cpu_core
        cy.get('#edge_component').select(cpuComponentName);
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_unit').should('have.value', 'cpu_core');

        // Switch to RAM and verify unit changes to GB_ram
        cy.get('#edge_component').select(ramComponentName);
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_unit').should('have.value', 'GB_ram');

        // Close the side panel - this may trigger an unsaved changes modal
        cy.get('#btn-close-side-panel').click();

        // Wait a moment for modal to appear if it's going to
        cy.wait(500);

        // Check if modal is visible and click "Yes, Continue" if it is
        cy.get('body').then($body => {
            const modal = $body.find('#unsavedModal.show');
            if (modal.length > 0) {
                cy.wrap(modal).contains('button', 'Yes, Continue').click();
            }
        });

        // Wait for side panel to be fully closed
        cy.get('#sidePanel').should('not.contain.html');

        // Step 10: Edit CPU component need and verify changes
        // Expand RecurrentEdgeDeviceNeed to access the component needs
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first().find('.accordion-header > .chevron-btn').first().click();
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeComponentNeed", cpuComponentNeedName).click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_value').should('have.value', cpuNeedValue);
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_value').clear().type(updatedCpuNeedValue);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edit was saved
        // Expand RecurrentEdgeDeviceNeed to verify the edit
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeDeviceNeed", recurrentEdgeDeviceNeedName).first()
            .find('.accordion-header > .chevron-btn').first().click();
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeComponentNeed", cpuComponentNeedName).click();
        cy.get('#RecurrentEdgeComponentNeed_recurrent_need__constant_value')
            .should('have.value', updatedCpuNeedValue);
    });

    it("Create EdgeDevice, add CPU component, then remove component", () => {
        let edgeDeviceName = "Test Edge Device";
        let cpuComponentName = "Test CPU Component";

        cy.visit("/model_builder/");

        // Step 1: Create EdgeDevice
        cy.get("#btn-add-edge-device").should("be.visible").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#type_object_available").select("EdgeDevice");
        cy.get("#EdgeDevice_name").should("be.visible").type(edgeDeviceName);
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");

        // Verify EdgeDevice was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).should("exist");

        // Step 2: Add CPU component to the EdgeDevice
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('button[hx-get*="/model_builder/open-create-object-panel/EdgeComponent/"]').click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#type_object_available").select("EdgeCPUComponent");
        cy.get("#EdgeCPUComponent_name").should("be.visible").type(cpuComponentName);
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");

        // Verify CPU component was created and is visible in the EdgeDevice card
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).within(() => {
            cy.contains(cpuComponentName).should("exist");
        });

        // Step 3: Delete the CPU component
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).find('.chevron-btn').click();
        cy.getObjectButtonFromObjectTypeAndName("EdgeCPUComponent", cpuComponentName).should("be.visible").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get('button[hx-get^="/model_builder/ask-delete-object/"]').should("be.visible").click();
        cy.get('button').contains('Yes, delete').should("be.visible").should("be.enabled").click();
        cy.get("#model-builder-modal").should("not.exist");

        // Verify CPU component was removed from the EdgeDevice card
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).within(() => {
            cy.contains(cpuComponentName).should("not.exist");
        });
    });
});
