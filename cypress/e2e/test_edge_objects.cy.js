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

    it('Add edge device, edge usage journey, and recurrent edge processes with verification and editing', () => {
        // Edge device setup
        let edgeDeviceName = "Test Edge Device for Journey";
        let edgeRam = "32";
        let edgeCompute = "16";
        let lifespan = "12"

        // Edge usage journey setup
        let edgeUsageJourneyName = "Test Edge Usage Journey";
        let usageSpan = "10";
        let updatedUsageSpan = "11";

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
        cy.get('#EdgeUsageJourney_edge_device').select(edgeDeviceName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).should('exist');

        // Step 3: Add first recurrent edge process to the edge usage journey
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
        cy.get('#sidePanel').should('be.visible');

        // Click on add recurrent edge process button within the edge usage journey edit panel
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).find('div[id^="add-edge-process-to"]').click();
        cy.get('#RecurrentEdgeProcessFromForm_name').type(recurrentProcess1Name);
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').clear().type(compute1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').clear().type(ram1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_storage_needed').clear().type(storage1);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcess1Name).should('exist');

        // Step 4: Add second recurrent edge process
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).find('div[id^="add-edge-process-to"]').click();
        cy.get('#RecurrentEdgeProcessFromForm_name').type(recurrentProcess2Name);
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').clear().type(compute2);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').clear().type(ram2);
        cy.get('#RecurrentEdgeProcessFromForm_constant_storage_needed').clear().type(storage2);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcess2Name).should('exist');

        // Step 5: Edit edge usage journey and verify changes
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
        cy.get('#EdgeUsageJourney_usage_span').should('have.value', usageSpan);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(updatedUsageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge usage journey edit was saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
        cy.get('#EdgeUsageJourney_usage_span').should('have.value', updatedUsageSpan);
        cy.get('#btn-close-side-panel').click();

        // Step 6: Edit first recurrent edge process and verify changes
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcess1Name).click();
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').should('have.value', compute1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').should('have.value', ram1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_storage_needed').should('have.value', storage1);

        // Make edits
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').clear().type(updatedCompute1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').clear().type(updatedRam1);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify recurrent edge process edits were saved
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcess1Name).click();
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').should('have.value', updatedCompute1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').should('have.value', updatedRam1);
        cy.get('#RecurrentEdgeProcessFromForm_constant_storage_needed').should('have.value', storage1);
    });

    it('Enforce single edge usage journey to edge device constraint', () => {
        let firstEdgeComputerName = "First Edge Device";
        let secondEdgeComputerName = "Second Edge Device";
        let firstJourneyName = "First Edge Usage Journey";
        let secondJourneyName = "Second Edge Usage Journey";
        let edgeRam = "16";
        let edgeCompute = "8";
        let usageSpan = "2";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        // Step 1: Try to add edge usage journey without any edge devices - should show error modal
        cy.get('#btn-add-edge-usage-journey').click();
        // Verify error modal appears
        cy.get('#model-builder-modal').should("exist").should('be.visible');
        cy.reload();
        cy.get('#model-builder-modal').should('not.exist');

        // Step 2: Create first edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(firstEdgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", firstEdgeComputerName).should('exist');

        // Step 3: Create first edge usage journey - should work now
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(firstJourneyName);
        cy.get('#EdgeUsageJourney_edge_device').select(firstEdgeComputerName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).should('exist');

        // Step 4: Try to create second edge usage journey - should show error modal since edge device is taken
        cy.get('#btn-add-edge-usage-journey').click();
        // Verify error modal appears
        cy.get('#model-builder-modal').should("exist").should('be.visible');
        cy.reload();
        cy.get('#model-builder-modal').should('not.exist');

        // Step 5: Create second edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(secondEdgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", secondEdgeComputerName).should('exist');

        // Step 6: Create second edge usage journey - should work and only show second edge device in select
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(secondJourneyName);

        // Verify that only the second edge device is available in the select
        cy.get('#EdgeUsageJourney_edge_device option').should('have.length', 1);
        cy.get('#EdgeUsageJourney_edge_device option').contains(firstEdgeComputerName).should('not.exist');
        cy.get('#EdgeUsageJourney_edge_device option').contains(secondEdgeComputerName).should('exist');

        cy.get('#EdgeUsageJourney_edge_device').select(secondEdgeComputerName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).should('exist');
    });

    it('Verify recurrent edge process mirroring logic works correctly', () => {
        let firstEdgeComputerName = "First Mirror Edge Device";
        let secondEdgeComputerName = "Second Mirror Edge Device";
        let firstJourneyName = "First Mirror Edge Usage Journey";
        let secondJourneyName = "Second Mirror Edge Usage Journey";
        let recurrentProcessName = "Mirrored Recurrent Process";
        let updatedProcessName = "Updated Mirrored Process";
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

        // Step 2: Create first edge usage journey
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(firstJourneyName);
        cy.get('#EdgeUsageJourney_edge_device').select(firstEdgeComputerName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify first edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).should('exist');

        // Step 3: Add recurrent edge process to first journey
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).find('div[id^="add-edge-process-to"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#RecurrentEdgeProcessFromForm_name').type(recurrentProcessName);
        cy.get('#RecurrentEdgeProcessFromForm_constant_compute_needed').clear().type(processCompute);
        cy.get('#RecurrentEdgeProcessFromForm_constant_ram_needed').clear().type(processRam);
        cy.get('#RecurrentEdgeProcessFromForm_constant_storage_needed').clear().type(processStorage);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify recurrent edge process was created
        cy.getObjectCardFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcessName).should('exist');

        // Step 4: Create second edge device
        cy.get('#btn-add-edge-device').click();
        cy.get('#sidePanel').contains('div', 'Add new edge device').should('exist');
        cy.get('#EdgeComputer_name').type(secondEdgeComputerName);
        cy.get('#EdgeComputer_ram').clear().type(edgeRam);
        cy.get('#EdgeComputer_compute').clear().type(edgeCompute);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeComputer", secondEdgeComputerName).should('exist');

        // Step 5: Create second edge usage journey linked to the first recurrent edge process
        cy.get('#btn-add-edge-usage-journey').click();
        cy.get('#sidePanel').contains('div', 'Add new edge usage journey').should('exist');
        cy.get('#EdgeUsageJourney_name').type(secondJourneyName);
        cy.get('#EdgeUsageJourney_edge_device').select(secondEdgeComputerName);
        cy.get('#EdgeUsageJourney_usage_span').clear().type(usageSpan);
        // Link to the existing recurrent edge process using select_multiple
        cy.get('#select-new-object-EdgeUsageJourney_edge_processes').select(recurrentProcessName);
        cy.get('#add-btn-EdgeUsageJourney_edge_processes').click();
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify second edge usage journey was created
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).should('exist');

        // Step 6: Verify both edge usage journeys have recurrent edge process cards with the same name
        // Check first edge usage journey card contains the recurrent process
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).within(() => {
            cy.contains(recurrentProcessName).should('exist');
        });

        // Check second edge usage journey card contains the recurrent process
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).within(() => {
            cy.contains(recurrentProcessName).should('exist');
        });

        // Step 7: Edit the name of one recurrent edge process and verify mirroring
        cy.getObjectButtonFromObjectTypeAndName("RecurrentEdgeProcessFromForm", recurrentProcessName).click();
        cy.get('#RecurrentEdgeProcessFromForm_name').should('have.value', recurrentProcessName);
        cy.get('#RecurrentEdgeProcessFromForm_name').clear().type(updatedProcessName);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Step 8: Verify both edge usage journeys now show the updated process name in their cards
        // Check first edge usage journey card shows updated name
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", firstJourneyName).within(() => {
            cy.contains(updatedProcessName).should('exist');
            cy.contains(recurrentProcessName).should('not.exist');
        });

        // Check second edge usage journey card shows updated name
        cy.getObjectCardFromObjectTypeAndName("EdgeUsageJourney", secondJourneyName).within(() => {
            cy.contains(updatedProcessName).should('exist');
            cy.contains(recurrentProcessName).should('not.exist');
        });
    });
});
