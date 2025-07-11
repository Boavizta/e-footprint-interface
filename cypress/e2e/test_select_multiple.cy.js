beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Calculated attributes", () => {
    it("Navigate between calculated attributes", () => {
        let ujsOne = "Test E2E UJ 1";
        let jobOne = "Test E2E Job 1";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data-multiple.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('input[type="file"]').then(($input) => {
          expect($input[0].files.length).to.equal(1);
          expect($input[0].files[0].name).to.equal('efootprint-model-system-data-multiple.json');
        });
        cy.get('button[type="submit"]').click();
        cy.get('#button-id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1').click();
        cy.get('#add-btn-UsageJourneyStep_jobs').click();
        cy.get('#btn-submit-form').click();
        cy.get('#icon_accordion_id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1').click();
        cy.get('#id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1_id-5f350a-Test-E2E-Job-2').should('exist');
        cy.get('#button-id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1').click();
        cy.get('#remove-id-5f350a-Test-E2E-Job-2').click();
        cy.get('#btn-submit-form').click();
        cy.get('#icon_accordion_id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1').click();
        cy.get('id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1_id-5f350a-Test-E2E-Job-2').should('not.exist');
        cy.get('#button-id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1').click();
        cy.get('#remove-id-4f5352-Test-E2E-Job-1').click();
        cy.get('#btn-submit-form').click();
        cy.get('id-9a4204-Test-E2E-UJ_id-f9b3b3-Test-E2E-UJ-1_id-4f5352-Test-E2E-Job-1').should('not.exist');
    });
});
