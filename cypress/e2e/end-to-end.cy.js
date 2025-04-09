beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe('Test de la page d\'accueil', () => {
    it('Ouvre la page d\'accueil et interagit avec un bouton', () => {

        let ujNameOne = "Test E2E UJ 1";
        let ujNameTwo = "Test E2E UJ 2";
        let ujsOne = "Test E2E UJS 1";
        let ujsTwo = "Test E2E UJS 2";
        let server = "Test E2E Server";
        let service = "Test E2E Service";
        let jobOne = "Test E2E Job 1";
        let jobTwo = "Test E2E Job 2";
        let upNameOne = "Test E2E Usage Pattern 1";
        let defaulId = "button-uid-my-first-usage-journey-1"

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.wait(500);
        cy.window().its('LeaderLine')

        //delete default card
        cy.get('button[id="'+defaulId+'"]').click();
        cy.wait(500);
        cy.get('button[hx-get^="/model_builder/ask-delete-object/"][hx-get$="/model_builder/ask-delete-object/uid-my-first-usage-journey-1/"]').should('be.visible').click();
        cy.wait(500);
        cy.get('button').contains('Yes, delete').should('be.enabled').click();

        // Create UJ one and two
        cy.get('#btn-add-usage-journey').click();
        cy.get('#btn-add-usage-journey').should('be.visible');
        cy.get('#UsageJourney_name').clear();
        cy.get('#UsageJourney_name').type(ujNameOne);
        cy.get('#btn-submit-form').click();
        cy.get('#form-add-usage-journey').should('not.exist');

        cy.wait(500);

        cy.get('#btn-add-usage-journey').click();
        cy.get('#UsageJourney_name').clear();
        cy.get('#btn-submit-form').click();
        cy.get('#UsageJourney_name').then(($input) => {
            expect($input[0].validationMessage).to.not.be.empty;
        });
        cy.get('#UsageJourney_name').type(ujNameTwo);
        cy.get('#btn-submit-form').click();
        cy.get('#form-add-usage-journey').should('not.exist');

        // User journeys must be visible then add user journey steps to UJ 1
        cy.get('div[id$="'+ujNameOne.replaceAll(' ', '-')+'"]').should('have.class', 'leader-line-object')
        cy.get('div[id$="'+ujNameTwo.replaceAll(' ', '-')+'"]').should('have.class', 'leader-line-object')
        cy.get('div[id$="'+ujNameOne.replaceAll(' ', '-')+'"]')
          .contains('button', 'Add usage journey step')
          .click();
        cy.get('#sidePanel').contains('div', 'Add new usage journey step').should('be.visible');
        //erase all the text in the input with id name
        cy.get('#UsageJourneyStep_name').clear();
        cy.get('#UsageJourneyStep_name').type(ujsOne);
        cy.get('#UsageJourneyStep_user_time_spent').type('10.1');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('exist').find('div').should('not.exist');
        // @ts-ignore
        cy.get('div[id$="'+ujNameOne.replaceAll(' ', '-')+'"]').should('have.class', 'leader-line-object')
        cy.get('div[id$="'+ujNameOne.replaceAll(' ', '-')+'"]')
          .contains('button', 'Add usage journey step')
          .click();
        cy.get('#sidePanel').contains('div', 'Add new usage journey step').should('be.visible');
        cy.get('#UsageJourneyStep_name').clear();
        cy.get('#UsageJourneyStep_name').type(ujsTwo);
        cy.get('#UsageJourneyStep_user_time_spent').type('20,2');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('exist').find('form').should('not.exist');
        cy.get('div[id$="'+ujNameOne.replaceAll(' ', '-')+'"]').should('have.class', 'leader-line-object')
        //on vérifie que les deux ujs ont bien été ajoutés
        cy.get('div[id*="'+ujNameOne.replaceAll(' ', '-')+'"]').find('div[id*="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist');
        cy.get('div[id*="'+ujNameOne.replaceAll(' ', '-')+'"]').find('div[id*="'+ujsTwo.replaceAll(' ', '-')+'"]').should('exist');

        // Add server
        cy.get('#btn-add-server').click();
        cy.get('#sidePanel').contains('div', 'Add new server').should('be.visible');
        cy.get('#type_object_available').select('BoaviztaCloudServer');
        cy.get('#BoaviztaCloudServer_name').clear();
        cy.get('#BoaviztaCloudServer_name').type(server);
        cy.get('#BoaviztaCloudServer_instance_type').clear();
        cy.get('#BoaviztaCloudServer_instance_type').type("ent1-l");
        cy.get('#btn-submit-form').click();

        cy.get('div[id$="'+server.replaceAll(' ', '-')+'"]').should('have.class', 'list-group-item')
        // get the button with attribute hx-get begin with '/model_builder/open-create-service-panel/' and ended with 'Test-E2E-Server'
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Service/"][hx-vals*="'+server.replaceAll(' ', '-')+'"]').click();
        cy.get('#WebApplication_name').clear();
        cy.get('#WebApplication_name').type(service);
        cy.get('#WebApplication_technology').select('php-symfony');
        cy.get('#btn-submit-form').click();
        cy.get('button[hx-get^="/model_builder/open-edit-object-panel/"][hx-get$="'+service.replaceAll(' ', '-')+'/"]').should('be.visible');

        // Add jobs
        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsOne.replaceAll(' ', '-')+'"]').click();
        cy.get('#service').select(service);
        cy.get('#WebApplicationJob_name').clear();
        cy.get('#WebApplicationJob_name').type(jobOne);
        cy.get('#btn-submit-form').click();
        cy.get('button[hx-get^="/model_builder/open-edit-object-panel/"][hx-get$="'+jobOne.replaceAll(' ', '-')+'/"]').should('be.visible');

        cy.get('button[hx-get="/model_builder/open-create-object-panel/Job/"][hx-vals*="'+ujsTwo.replaceAll(' ', '-')+'"]').click();
        cy.get('#sidePanel').should('be.visible');
        cy.get('#service').select(service);
        cy.get('#WebApplicationJob_name').clear();
        cy.get('#WebApplicationJob_name').type(jobTwo);
        cy.get('#btn-submit-form').click();
        cy.get('button[hx-get^="/model_builder/open-edit-object-panel/"][hx-get$="'+jobTwo.replaceAll(' ', '-')+'/"]').should('be.visible');

        // Add usagePattern
        cy.get('button').contains('Add usage pattern').click();
        cy.wait(500);
        cy.get('#sidePanel').should('be.visible');
        cy.get('#UsagePatternFromForm_name').clear();
        cy.get('#UsagePatternFromForm_name').type(upNameOne);

        //get input  with name start_date in #modal-timeseries-chart
        cy.get('#start_date').click();
        cy.get('input[class="numInput cur-year"]').type('2026');
        cy.get('span[aria-label="January 1, 2026"]').click()
        cy.get('#modeling_duration_value').click();
        cy.get('#modeling_duration_value').invoke('val', '2').trigger('change');
        cy.get('#net_growth_rate_in_percentage').click();
        cy.get('#net_growth_rate_in_percentage').invoke('val', '25').trigger('change');
        cy.get('#net_growth_rate_timespan').select('year');
        cy.get('#btn-submit-form').click();
        cy.get('#sidePanel').should('not.contain.html');
        cy.get('button[id^="button-id-"][id$="'+upNameOne.replaceAll(' ', '-')+'"]').should('be.visible');
        cy.get('button[id^="button-id-"][id$="Test-E2E-UJ-2"]').click();
        cy.wait(500);
        cy.get('button[hx-get^="/model_builder/ask-delete-object/"][hx-get$="'+ujNameTwo.replaceAll(' ', '-')+'/"]').should('be.visible').click();
        cy.wait(500);
        cy.get('button').contains('Yes, delete').should('be.enabled').click();
        cy.get("#model-builder-modal").should("not.exist");
        cy.get('button[id^="button-id-"][id$="Test-E2E-UJ-2"]').should('not.exist');

        cy.get('#btn-open-panel-result').click();
        cy.get('#lineChart').should('be.visible');
        cy.get('#graph-block').should('be.visible')
        cy.get('#result-block').should('be.visible').find('div[onclick="hidePanelResult()"]').click();
        cy.get('#lineChart').should('not.exist');
    });
});
