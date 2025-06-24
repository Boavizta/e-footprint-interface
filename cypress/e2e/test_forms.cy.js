beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Test - Forms panel", () => {
        let uj = "Test E2E UJ";
        let ujsOne = "Test E2E UJ 1";
        let serverOne = "Test E2E Server 1";
        let serverTwo = "Test E2E Server 2";

    it("Check that the UJS list is displayed and disabled when adding a UJ with no UJS in the system, then check" +
        " that it is enabled after having created a UJS", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job-no-uj-step.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('button[id^="button-id-"][id$="' + uj.replaceAll(' ', '-') + '"]').should('exist').click();
        cy.get("#sidePanelForm").should('exist').should('be.visible');
        cy.get('#select-new-object-UsageJourney_uj_steps').should('exist').should('not.be.enabled');
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('div[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="' + uj.replaceAll(' ',
        '-') + '"]').should('exist').click();
        cy.get("#btn-submit-form").should('exist').click();
        cy.get("#sidePanelForm").should('not.exist');
        cy.get('button[id^="button-id-"][id$="' + uj.replaceAll(' ', '-') + '"]').should('exist').click();
        cy.get('#select-new-object-UsageJourney_uj_steps').should('exist').should('be.not.enabled');
        cy.get('#btn-add-usage-journey').click();
        cy.get('#select-new-object-UsageJourney_uj_steps').should('exist').should('be.enabled');
    });

    it("Check that the jobs list in not displayed when adding a UJS with no job in the system, then check that it is displayed after having created a job", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#UsageJourneyStep_jobs').should('exist').should('not.be.visible');
        cy.get('div[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="'+uj.replaceAll(' ',
         '-')+'"]').click();
        cy.get('#select-new-object-UsageJourneyStep_jobs').should('exist').should('not.be.enabled');
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ',
        '-')+'"]').click();
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');


        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#select-new-object-UsageJourneyStep_jobs').should('exist').should('be.not.enabled');
        cy.get('div[hx-get="/model_builder/open-create-object-panel/UsageJourneyStep"][hx-vals*="'+uj.replaceAll(' ',
         '-')+'"]').click();
        cy.get('#select-new-object-UsageJourneyStep_jobs').should('exist').should('be.enabled');
    });

    it("Try to create a server with and without edit fields into advanced options", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-no-job.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get("#btn-add-server").should('be.enabled').click();
        cy.get("#sidePanelForm").should('be.visible');
        cy.get("#type_object_available").should('be.visible').select('Server');
        cy.get("#Server_name").clear().type(serverOne);
        cy.get("#Server_average_carbon_intensity").clear().type('700');
        cy.get("#advanced-Server").should('be.not.visible');
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get("#btn-add-server").should('be.enabled').click();
        cy.get("#sidePanelForm").should('be.visible');
        cy.get("#type_object_available").select('Server');
        cy.get("#advanced-Server").should('be.not.visible');
        cy.get("#Server_name").clear().type(serverTwo);
        cy.get("#Server_average_carbon_intensity").clear().type('800');
        cy.get("#display-advanced-Server").click();
        cy.get("#advanced-Server").should('be.visible');
        cy.get("#Server_power").clear().type('888');
        cy.get("#display-advanced-Server").click();
        cy.get("#advanced-Server").should('be.not.visible');
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('button[id^="button-id-"][id$="'+serverOne.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get("#Server_average_carbon_intensity").should('have.value', '700');
        cy.get("#advanced-Server").should('be.not.visible');
        cy.get("#display-advanced-Server").click();
        cy.get("#advanced-Server").should('be.visible');
        cy.get("#Server_power").should('have.value', '300');
        cy.get('button[id^="button-id-"][id$="'+serverTwo.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get("#Server_average_carbon_intensity").should('have.value', '800');
        cy.get("#advanced-Server").should('be.not.visible');
        cy.get("#display-advanced-Server").click();
        cy.get("#advanced-Server").should('be.visible');
        cy.get("#Server_power").should('have.value', '888');
    });

    it("Check that object keep units defined in model", () => {
        let serverName = 'cloud server test'
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/test-unit-edit.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get("#btn-submit-form").click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('button[id^="button-id-"][id$="'+serverName.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#Storage_data_storage_duration_unit').should('have.value', 'month');
        cy.get('#Storage_data_storage_duration').clear().type('3');
        cy.get('#btn-submit-form').click();
        cy.get("#sidePanelForm").should('not.exist');

        cy.get('button[id^="button-id-"][id$="'+serverName.replaceAll(' ', '-')+'"]').should('exist').click();
        cy.get('#Storage_data_storage_duration_unit').should('have.value', 'month');
        cy.get('#Storage_data_storage_duration').should('have.value', '3');
    });

    it("Check sources are displayed in the form with the right values before and after addition and edition", () => {
        cy.visit("/model_builder/");
        cy.get("#add_usage_pattern").should("exist").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#modeling_duration_value").should("be.visible").should("be.enabled").clear().type("2");
        cy.get("#source-net_growth_rate_in_percentage").should("contain.text","source : e-footprint hypothesis");
        cy.get("#source-modeling_duration_value").should("contain.text","source : user data");
        cy.get("#initial_usage_journey_volume").should('be.visible').type("1000");
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");
        cy.get("button[id^='button-id-'][id$='Usage-pattern-1']").should("exist").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#source-net_growth_rate_in_percentage").should("contain.text","source : e-footprint hypothesis");
        cy.get("#source-modeling_duration_value").should("contain.text","source : user data");
        cy.get("#net_growth_rate_in_percentage").clear().type("5");
        cy.get("#source-net_growth_rate_in_percentage").should("contain.text","source : user data");
        cy.get("#btn-submit-form").should("be.visible").click();
        cy.get("#sidePanelForm").should("not.exist");
        cy.get("button[id^='button-id-'][id$='Usage-pattern-1']").should("exist").click();
        cy.get("#sidePanelForm").should("be.visible");
        cy.get("#source-net_growth_rate_in_percentage").should("contain.text","source : user data");
        cy.get("#source-modeling_duration_value").should("contain.text","source : user data");
    });

});
