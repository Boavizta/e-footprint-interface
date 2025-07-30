beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Select multiple", () => {
    it("Test select multiple behaviours", () => {
        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data-multiple.json');
        // The cy.wait(100) are for js to have time to execute
        cy.getObjectButtonFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").should("exist").click();
        cy.wait(100);
        cy.get('#add-btn-UsageJourneyStep_jobs').should("exist").click();
        cy.wait(100);
        cy.get('#btn-submit-form').should("exist").click();
        cy.wait(100);
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").contains('div', 'Test E2E Job 2').should('exist');
        cy.getObjectButtonFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").should("exist").click();
        cy.wait(100);
        cy.get('#remove-id-5f350a-Test-E2E-Job-2').should("exist").click();
        cy.wait(100);
        cy.get('#btn-submit-form').should("exist").click();
        cy.wait(100);
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").contains('div', 'Test E2E Job 2').should('not.exist');
        cy.getObjectButtonFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").should("exist").click();
        cy.wait(100);
        cy.get('#remove-id-4f5352-Test-E2E-Job-1').should("exist").click();
        cy.wait(100);
        cy.get('#btn-submit-form').should("exist").click();
        cy.wait(100);
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").contains('div', 'Test E2E Job 1').should('not.exist');
    });
});
