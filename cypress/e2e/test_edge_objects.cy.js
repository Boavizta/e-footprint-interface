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
        cy.get('#EdgeDevice_name').type(edgeDeviceName);
        cy.get('#EdgeDevice_ram').clear().type(originalRam);
        cy.get('#EdgeDevice_compute').clear().type(originalCompute);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).should('have.class', 'list-group-item');

        // Edit the edge device
        cy.getObjectButtonFromObjectTypeAndName("EdgeDevice", edgeDeviceName).click();
        cy.get('#sidePanel').should('be.visible');

        // Verify current values
        cy.get('#EdgeDevice_ram').should('have.value', originalRam);
        cy.get('#EdgeDevice_compute').should('have.value', originalCompute);

        // Make changes
        cy.get('#EdgeDevice_ram').clear().type(updatedRam);
        cy.get('#EdgeDevice_compute').clear().type(updatedCompute);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify changes were saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeDevice", edgeDeviceName).click();
        cy.get('#EdgeDevice_ram').should('have.value', updatedRam);
        cy.get('#EdgeDevice_compute').should('have.value', updatedCompute);
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
        cy.get('#EdgeDevice_name').type(edgeDeviceName);

        // Open advanced options
        cy.get('#display-advanced-EdgeDevice').click();
        cy.get('#advanced-EdgeDevice').should('be.visible');

        // Set advanced parameters
        cy.get('#EdgeDevice_lifespan').clear().type(customLifespan);
        cy.get('#EdgeDevice_carbon_footprint_fabrication').clear().type(customCarbonFootprint);

        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).should('exist');

        // Verify advanced parameters were saved
        cy.getObjectButtonFromObjectTypeAndName("EdgeDevice", edgeDeviceName).click();
        cy.get('#display-advanced-EdgeDevice').click();
        cy.get('#advanced-EdgeDevice').should('be.visible');
        cy.get('#EdgeDevice_lifespan').should('have.value', customLifespan);
        cy.get('#EdgeDevice_carbon_footprint_fabrication').should('have.value', customCarbonFootprint);
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
        cy.get('#EdgeDevice_name').type(edgeDeviceName);
        cy.get('#EdgeDevice_ram').clear().type(edgeRam);
        cy.get('#EdgeDevice_compute').clear().type(edgeCompute);
        cy.get("#EdgeDevice_lifespan").clear().type(lifespan);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');

        // Verify edge device was created
        cy.getObjectCardFromObjectTypeAndName("EdgeDevice", edgeDeviceName).should('exist');

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
        cy.getObjectButtonFromObjectTypeAndName("EdgeUsageJourney", edgeUsageJourneyName).click();
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
});
