import "cypress-real-events";

beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Test - Result panel", () => {
    let ujNameTwo = "Test E2E UJ 2";

    it("Check if the model cannot be calculated then the modal exception is displayed and the result panel not showed", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').should("exist").click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.get('input[type="file"]').should("not.exist");

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });

        cy.get('button').should("exist").contains('Go back').should('be.exist');
    });

    it("Check that when the model can be calculated the panel is displayed and can be swiped down", () => {
        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data.json');
        // Wait for htmx to load the page
        cy.wait(50);
        cy.get("#panel-result-btn").should('exist').should('be.visible').should('have.class', 'w-100');
        cy.intercept("GET", "/model_builder/result-chart/").as("openResults")
        cy.get('#btn-open-panel-result').should('be.visible').click()
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });
        cy.wait("@openResults"); // wait for the result panel to be fully loaded
        cy.get('#result-block').should('exist').find('div[onclick="hidePanelResult()"]')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 400 })
        .realTouch('end', { x: 100, y: 400 });
    });

    it("check if an exception modal is displayed when the calculation is launched with an UsageJourney without any" +
    " UserJourneyStep", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').should("exist").click();
        let fileTest = 'cypress/fixtures/model-test-uj-not-linked-to-uj-step.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.get('input[type="file"]').should("not.exist");

        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });

        cy.get('button').contains('Go back').should('be.exist');
        cy.get("#exception-msg").should("exist")
            .should("include.text","The following usage journey(s) have no usage journey step")
            .should("include.text",ujNameTwo)
    });

    it("Check if labels on bar chart has been updated when granularity changed", () => {
        let upName = "Test E2E Usage Pattern";
        let nbElementInit;
        let nbElementsMonthlyGranularity;
        let nbElementsYearlyGranularity;
        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data.json');

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.intercept("GET", "/model_builder/result-chart/").as("openResults")
        cy.get('#btn-open-panel-result')
        .realTouch('start', { x: 100, y: 300 })
        .realTouch('move', { x: 100, y: 200 })
        .realTouch('end', { x: 100, y: 200 });
        cy.wait("@openResults"); // wait for the result panel to be displayed

        cy.window().its('charts').should('exist');
        cy.window().its('charts').its('barChart').should('exist').then((chart) => {
            nbElementInit = chart.data.labels.length;
        });

        // Wait for all js loading
        cy.wait(200);
        cy.get('#results_temporal_granularity').should('exist').select('month');
        cy.get('#results_temporal_granularity').should('have.value', 'month');

        cy.window().its('charts').its('barChart').should('exist').then((chart) => {
            nbElementsMonthlyGranularity = chart.data.labels.length;
            expect(nbElementInit).to.be.lessThan(nbElementsMonthlyGranularity);
        });

        cy.get('#results_temporal_granularity').select('year');
         cy.window().its('charts').its('barChart').then((chart) => {
            nbElementsYearlyGranularity = chart.data.labels.length;
            expect(nbElementInit).to.be.equal(nbElementsYearlyGranularity);
        });
    });

    it("Check that sources are displayed and can be downloaded", () => {
        let upName = "Test E2E Usage Pattern";
        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data.json');

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('#btn-open-panel-result').should("exist").click()

        //get button with text Sources
        cy.get('#header-btn-result-sources').should('be.visible').click();
        cy.get('#source-block').should('have.class', 'd-block');
        cy.get('#graph-block').should('have.class', 'd-none');

        let now = new Date();
        let nowUtc = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
        let day = String(nowUtc.getDate()).padStart(2, '0');
        let month = String(nowUtc.getMonth() + 1).padStart(2, '0');
        let year = nowUtc.getFullYear();
        let hours = String(nowUtc.getHours()).padStart(2, '0');
        let minutes = String(nowUtc.getMinutes()).padStart(2, '0');
        let fileName = `${year}-${month}-${day} ${hours}:${minutes}_UTC system 1_sources.xlsx`;

        //to get the filedownload in cypress, we need to remove the target blank attribute
        cy.intercept('GET', '**/download-sources/**').as('fileDownload');
        cy.get('#download-sources').click()
          .invoke('removeAttr', 'target')
          .click();

        cy.wait('@fileDownload').then((interception) => {
            const contentDisposition = interception.response.headers['content-disposition'];
            expect(contentDisposition).to.include('attachment');
            expect(contentDisposition).to.include(fileName);
        });

    });

    it("Check edition when the result panel is open and model recomputation", () => {
        let serverTest = "Test-E2E-Server"
        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data.json');

        cy.get('button[id^="button-id-"][id$="'+serverTest.replaceAll(' ', '-')+'"]').should('be.enabled').click()
        cy.get('#sidePanelForm').should('exist').should('be.visible');
        cy.get("#Storage_data_replication_factor").should('be.visible').type("1000")
        cy.intercept("GET", "/model_builder/result-chart/").as("openResults")
        cy.get('#btn-open-panel-result').click()
        cy.wait("@openResults"); // wait for the result panel to be fully loaded
        cy.get('#barChartTitle').should('be.visible').should('contain.text', "Yearly CO2 emissions")
        cy.get('#panel-result-btn').should('have.class', 'result-width')
        cy.window().then((win) => {
            cy.spy(win, 'displayLoaderResult').as('displayLoaderResult');
        });
        cy.window().then((win) => {
            cy.spy(win, 'drawBarResultChart').as('drawBarResultChart');
        });
        cy.intercept("POST", "/model_builder/edit-object/id-fb1308-Test-E2E-Server/").as("editServer")
        cy.get('#btn-submit-form').click();
        cy.get('@displayLoaderResult').should('have.been.called');
        cy.get('@drawBarResultChart').should('have.been.called');
        cy.wait("@editServer");
        cy.get('#panel-result-btn').should('not.have.class', 'result-width')
    });
});
