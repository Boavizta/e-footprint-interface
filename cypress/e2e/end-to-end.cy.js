beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe('Test de la page d\'accueil', () => {
    it('End to end user journey', () => {

        let ujNameOne = "Test E2E UJ 1";
        let ujNameTwo = "Test E2E UJ 2";
        let ujsOne = "Test E2E UJS 1";
        let ujsTwo = "Test E2E UJS 2";
        let server = "Test E2E Server";
        let service = "Test E2E Service";
        let jobOne = "Test E2E Job 1";
        let jobTwo = "Test E2E Job 2";
        let upNameOne = "Test E2E Usage Pattern 1";
        let defaultUj = "My first usage journey"

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.window().its('LeaderLine').should('exist');

        // Create UJ one and two
        cy.get('#btn-add-usage-journey').should('be.visible').click();
        cy.get('#sidePanelForm').should('be.visible');
        cy.get('#UsageJourney_name').should('exist').should('be.enabled').click().type(ujNameOne);
        cy.get('#btn-submit-form').should('be.enabled').should('be.visible').click();
        cy.get('#form-add-usage-journey').should('not.exist');
        cy.contains('div', ujNameOne).find("button").should('exist').should('be.visible');

        cy.get('#btn-add-usage-journey').should("be.visible").click();
        cy.get('#sidePanelForm').should('be.visible');
        cy.get('#UsageJourney_name').should('exist').should('be.enabled').click().type(ujNameTwo);
        cy.get('#btn-submit-form').should('be.enabled').should('be.visible').click();
        cy.get('#form-add-usage-journey').should('not.exist')
        cy.contains('div', ujNameTwo).find("button").should('exist').should('be.visible');

        // Add user journey steps to UJ 1
        cy.getObjectCardFromObjectTypeAndName("UsageJourney", ujNameOne).find('div[id^="add-step-to"]').click();
        cy.get('#sidePanel').contains('div', 'Add new usage journey step').should('exist');
        // Erase all the text in the input with id name
        cy.get('#UsageJourneyStep_name').clear();
        cy.get('#UsageJourneyStep_name').type(ujsOne);
        cy.get('#UsageJourneyStep_user_time_spent').type('10.1');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('exist').find('div').should('not.exist');
        // @ts-ignore
        cy.getObjectCardFromObjectTypeAndName("UsageJourney", ujNameOne)
            .should('have.class', 'leader-line-object');
        cy.getObjectCardFromObjectTypeAndName("UsageJourney", ujNameOne)
            .find('div[id^="add-step-to"]').click();
        cy.get('#sidePanel').contains('div', 'Add new usage journey step').should('exist');
        cy.get('#UsageJourneyStep_name').clear();
        cy.get('#UsageJourneyStep_name').type(ujsTwo);
        cy.get('#UsageJourneyStep_user_time_spent').type('20,2');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('exist').find('form').should('not.exist');
        cy.getObjectCardFromObjectTypeAndName("UsageJourney", ujNameOne)
            .should('have.class', 'leader-line-object');
        // Check that new UJ steps have been added
        cy.contains('div', ujsOne).should('exist');
        cy.contains('div', ujsTwo).should('exist');

        // Add server
        cy.get('#btn-add-server').click();
        cy.get('#sidePanel').contains('div', 'Add new server').should('exist');
        cy.get('#type_object_available').select('BoaviztaCloudServer');
        cy.get('#BoaviztaCloudServer_name').clear();
        cy.get('#BoaviztaCloudServer_name').type(server);
        cy.get('#BoaviztaCloudServer_instance_type').clear();
        cy.get('#BoaviztaCloudServer_instance_type').type("ent1-l");
        cy.get('#btn-submit-form').click();

        cy.getObjectCardFromObjectTypeAndName("BoaviztaCloudServer", server).should('have.class', 'list-group-item')
        cy.getObjectCardFromObjectTypeAndName("BoaviztaCloudServer", server).find('button[id^="add-service-to"]').click();
        cy.get('#WebApplication_name').clear();
        cy.get('#WebApplication_name').type(service);
        cy.get('#WebApplication_technology').select('php-symfony');
        cy.get('#btn-submit-form').click();
        cy.contains('div', service).find('button[id^="button"]').should('be.visible');

        // Add jobs
        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsOne).find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').click({force: true});
        cy.get('#service').should('be.visible').select(service);
        cy.get('#WebApplicationJob_name').clear();
        cy.get('#WebApplicationJob_name').type(jobOne);
        cy.get('#btn-submit-form').click();
        cy.contains('div', jobOne).find('button[id^="button"]').should('exist');

        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsTwo).find('button[hx-get="/model_builder/open-create-object-panel/Job/"]').click();
        cy.get('#service').should('be.visible').select("direct_server_call");
        cy.get('#sidePanel').should('be.visible');
        cy.get('#Job_name').clear();
        cy.get('#Job_name').type(jobTwo);
        cy.get('#btn-submit-form').click();
        cy.contains('div', jobTwo).find('button[id^="button"]').should('exist');

        // Add usagePattern
        cy.get('#add_usage_pattern').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#UsagePatternFromForm_name').clear();
        cy.get('#UsagePatternFromForm_name').type(upNameOne);

        cy.get('#start_date').click();
        cy.get('input[class="numInput cur-year"]').type('2026');
        cy.get('span[aria-label="January 1, 2026"]').click()
        cy.get('#modeling_duration_value').click();
        cy.get('#modeling_duration_value').invoke('val', '2').trigger('change');
        cy.get("#chartTimeseries").should('have.class', 'd-none');
        cy.get('#initial_usage_journey_volume').click();
        cy.get('#initial_usage_journey_volume').type('1000');
        cy.get("#chartTimeseries").should('not.have.class', 'd-none');
        cy.get('#net_growth_rate_in_percentage').click();
        cy.get('#net_growth_rate_in_percentage').invoke('val', '25').trigger('change');
        cy.get('#net_growth_rate_timespan').select('year');
        cy.get("#UsagePatternFromForm_usage_journey").select(ujNameOne);
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');
        cy.contains("div", upNameOne).find('button[id^="button"]').should('be.visible');

        // Delete UJ 2
        cy.getObjectButtonFromObjectTypeAndName("UsageJourney", ujNameTwo).click();
        cy.get('#sidePanel').find('button[hx-get^="/model_builder/ask-delete-object/"]')
            .should('be.visible').click();
        cy.get('button').contains('Yes, delete').should('be.visible').should('be.enabled').click();
        cy.get("#model-builder-modal").should("not.exist");
        cy.contains(`div[id*="UsageJourney"] p`, ujNameTwo).should('not.exist');

        //delete default card
        cy.getObjectButtonFromObjectTypeAndName("UsageJourney", defaultUj).click();
        cy.get('#sidePanel').find('button[hx-get^="/model_builder/ask-delete-object/"]')
            .should('be.visible').click();
        cy.get('button').contains('Yes, delete').should('be.visible').and('be.enabled').click();
        cy.contains(`div[id*="UsageJourney"] p`, defaultUj).should("not.exist");

        cy.get('#model-builder-modal').should('not.exist');

        cy.get('#btn-open-panel-result').click();
        cy.get('#lineChart').should('be.visible');
        cy.get('#graph-block').should('be.visible')
        cy.get('#result-block').should('be.visible').find('div[onclick="hidePanelResult()"]').click();
        cy.get('#lineChart').should('not.exist');
    });
});
