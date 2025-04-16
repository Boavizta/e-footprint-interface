describe("Test - Forms panel", () => {
        let uj = "Test E2E UJ";
        let ujsOne = "Test E2E UJ 1";
        let ujsTwo = "Test E2E UJ 2";
        let service = "Test E2E Service";
        let jobOne = "Test E2E Job 1";
        let jobTwo = "Test E2E Job 2";

    it("Check that the UJS list is not displayed when adding a UJ with no UJS in the system, then check that it is displayed after having created a UJS", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job-no-uj-step.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.wait(500);
        cy.get("#btn-submit-form").click();
        cy.wait(500);

        cy.get('button[id^="button-id-"][id$="'+uj.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#UsageJourney_uj_steps').should('exist').should('not.be.visible');

        cy.get('#btn-add-usage-journey').click();
        cy.get('#UsageJourney_uj_steps').should('exist').should('not.be.visible');

         cy.get('button[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="'+uj.replaceAll(' ',
         '-')+'"]').click();
         cy.get("#btn-submit-form").click()

        cy.get('button[id^="button-id-"][id$="'+uj.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#UsageJourney_uj_steps').should('exist').should('be.visible');

        cy.get('#btn-add-usage-journey').click();
        cy.get('#UsageJourney_uj_steps').should('exist').should('be.visible');
    });

    it("Check that the jobs list in not displayed when adding a UJS with no job in the system, then check that it is displayed after having created a job", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.wait(500);
        cy.get("#btn-submit-form").click();
        cy.wait(500);

        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#UsageJourneyStep_jobs').should('exist').should('not.be.visible');
        cy.get('button[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="'+uj.replaceAll(' ',
         '-')+'"]').click();
        cy.get('#UsageJourneyStep_jobs').should('exist').should('not.be.visible');
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ',
        '-')+'"]').click();
        cy.get("#btn-submit-form").click();

        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#UsageJourneyStep_jobs').should('exist').should('be.visible');
        cy.get('button[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="'+uj.replaceAll(' ',
         '-')+'"]').click();
        cy.get('#UsageJourneyStep_jobs').should('exist').should('be.visible');
    });

});
