beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Test - Model Canva div", () => {
    let ujsOne = "Test E2E UJ 1";
        let ujsTwo = "Test E2E UJ 2";
        let service = "Test E2E Service";
        let jobOne = "Test E2E Job 1";
        let jobTwo = "Test E2E Job 2";

    it("Try to create a new job without servers in your model", () => {
        cy.visit("/model_builder/");
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "My first usage journey step").find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').should("exist").click();
        cy.get("#exception-msg").should("exist")
            .should("include.text","Please go to the infrastructure section and create a server before adding a job")
    });

    it("Edit UsageJourney name and make sure its UsageJourneyStep is still there", () => {
        cy.visit("/model_builder/");
        cy.getObjectButtonFromObjectTypeAndName("UsageJourney", "My first usage journey").should("exist").click();
        cy.get('#btn-submit-form').should("exist").click();
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "My first usage journey step").should("exist");
    });

    it("Try to create a new job on a empty UJ Step to check the button 'add new job' and the newest is correctly" +
        " positioned", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').should("exist").click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get("#btn-submit-form").should("exist").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsOne).find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').click();
        cy.get('#service').should("exist").select(service);
        cy.get('#WebApplicationJob_name').type(jobOne);
        cy.get('#btn-submit-form').click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsTwo).find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#service').should("exist").select(service);
        cy.get('#WebApplicationJob_name').type(jobTwo);
        cy.get('#btn-submit-form').click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.getObjectButtonFromObjectTypeAndName("WebApplicationJob", jobOne).should('exist');
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsOne).find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').should('exist');

        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").find('button[data-bs-target^="#flush-"]').should('exist').click()
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", "Test E2E UJ 1").find('div[id^="flush-"]').within(() => {
            cy.getObjectButtonFromObjectTypeAndName("WebApplicationJob", jobOne).then(($firstButton) => {
                cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"]').then(($secondButton) => {
                    const firstTop = $firstButton[0].getBoundingClientRect().top;
                    const secondTop = $secondButton[0].getBoundingClientRect().top;
                    expect(secondTop).to.be.greaterThan(firstTop);
                });
            });
        });
    });

});
