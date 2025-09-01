beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe('Test edge devices', () => {
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
});
