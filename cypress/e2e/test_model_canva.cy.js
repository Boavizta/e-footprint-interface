describe("Test - Model Canva div", () => {
    let ujsOne = "Test E2E UJ 1";
        let ujsTwo = "Test E2E UJ 2";
        let service = "Test E2E Service";
        let jobOne = "Test E2E Job 1";
        let jobTwo = "Test E2E Job 2";

    it("Try to create a new job without servers in your model", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="uid-my-first-usage-journey-step-1"]').click();
        cy.get("#exception-msg").should("exist")
            .should("include.text","Please create a server before adding a job")
    });

    it("Edit UsageJourney name and make sure its UsageJourneyStep is still there", () => {
        cy.visit("/model_builder/");
        cy.get("#button-uid-my-first-usage-journey-1").click();
        cy.get('#btn-submit-form').click();
        cy.wait(500);
        cy.get("#button-uid-my-first-usage-journey-1_uid-my-first-usage-journey-step-1").should("exist");
    });

    it("Try to create a new job on a empty UJ Step to check the button 'add new job' and the newest is correctly" +
        " positioned", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.wait(500);
        cy.get("#btn-submit-form").click();
        cy.wait(500);
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ', '-')+'"]').click();
        cy.get('#service').select(service);
        cy.get('#WebApplicationJob_name').type(jobOne);
        cy.get('#btn-submit-form').click();

        cy.wait(1000);
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsTwo.replaceAll(' ', '-')+'"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#service').select(service);
        cy.get('#WebApplicationJob_name').type(jobTwo);
        cy.get('#btn-submit-form').click();

        cy.get("button[id^='button-id-'][id$='"+jobOne.replaceAll(' ', '-')+"']").should('exist');
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist');

        cy.get('div[id^="flush-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').within(() => {
            cy.get("button[id^='button-id-'][id$='"+jobOne.replaceAll(' ', '-')+"']").then(($firstButton) => {
                cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ', '-')+'"]').then(($secondButton) => {
                    const firstTop = $firstButton[0].getBoundingClientRect().top;
                    const secondTop = $secondButton[0].getBoundingClientRect().top;
                    expect(secondTop).to.be.greaterThan(firstTop);
                });
            });
        });
    });

});
