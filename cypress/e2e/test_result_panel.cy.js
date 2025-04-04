import "cypress-real-events";
describe("Test - Result panel", () => {
    let ujNameTwo = "Test E2E UJ 2";

    it("Check if the model cannot be calculated if the modal exception is displayed and the result panel not showed", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });

        cy.get('#panel-result-btn').should('not.have.css', 'height', '93vh');
        cy.get('button').contains('Go back').should('be.exist');
    });

    it("Check that when the model can be calculated the panel is displayed and can be swiped down", () => {
        let upName = "Test E2E Usage Pattern";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('input[type="file"]').then(($input) => {
          expect($input[0].files.length).to.equal(1);
          expect($input[0].files[0].name).to.equal('efootprint-model-system-data.json');
        });
        cy.get('button[type="submit"]').click();
        cy.wait(500);
        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });
        cy.wait(500);
        cy.get('#inner-panel-result').should('be.visible').find('div[onclick="hidePanelResult()"]')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 400 })
        .realTouch('end', { x: 100, y: 400 });
    });

    it("check if an exception modal is displayed when the calculation is launched with an UsageJourney without any" +
    " UserJourneyStep", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/model-test-uj-not-linked-to-uj-step.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });

        cy.get('#panel-result-btn').should('not.have.css', 'height', '93vh');
        cy.get('button').contains('Go back').should('be.exist');
        cy.get("#exception-msg").should("exist")
            .should("include.text","The following usage journey(s) have no usage journey step")
            .should("include.text",ujNameTwo)
    });

    it("Check if labels on bar chart has been updated when granularity changed", () => {
        let upName = "Test E2E Usage Pattern";
        cy.visit("/model_builder/");
        cy.get('#model-canva').should('be.visible');
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.wait(500);
        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });

        cy.window().its('charts').should('exist');
        cy.get('#results_temporal_granularity').select('month');
        cy.window().its('charts').its('barChart').then((chart) => {
            chart.data.labels.forEach(label => {
                expect(label.length).to.be.greaterThan(6);
            });
        });

        cy.get('#results_temporal_granularity').select('year');
         cy.window().its('charts').its('barChart').then((chart) => {
            chart.data.labels.forEach(label => {
                expect(label.length).to.equal(4);
            });
        });
    });

});
