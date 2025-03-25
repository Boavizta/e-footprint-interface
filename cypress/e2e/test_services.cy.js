describe('Test services', () => {
    it('Try to install a new service on a server and edit it', () => {
        let server = "Test E2E Server";
        let service = "Test E2E Service";
        let providerName1 = "openai";
        let modelName1 = "gpt-4";
        let providerName2 = "mistralai";
        let modelName2 = "mistral-small";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        cy.get('#btn-add-server').click();
        cy.get('#sidePanel').contains('div', 'Add new server').should('be.visible');
        cy.get('#name').type(server);
        cy.get('#type_object_available').select('GPUServer');

        // get ram_per_gpu and compute inside the #collapse_GPUServer
        cy.get('#collapse_GPUServer_server').within(() => {
            cy.get('#ram_per_gpu').focus().type('{selectall}{backspace}512').blur();
            cy.get('#compute').focus().type('{selectall}{backspace}10').blur();
        });
        cy.get('#btn-submit-form').click();
        cy.get('div[id$="'+server.replaceAll(' ', '-')+'"]').should('have.class', 'list-group-item')
        cy.get('button[hx-get^="/model_builder/open-create-service-panel"][hx-get$="'+server.replaceAll(' ', '-')+'/"]').click();
        cy.get('#name').type(service);
        cy.get('#provider').select(providerName1);
        cy.get('#model_name').type(modelName1);
        cy.get('#btn-submit-form').click();

        //edit du service
        cy.get('button').contains(service).click();

        cy.get('#provider').select(providerName2);
        cy.get('#model_name').clear().type(modelName2);
        cy.get('#btn-submit-form').click();

        cy.get('#sidePanel').should('not.contain.html');
    });

    it('Try to install LLM on too small GPU server and make sure error modal is raised', () => {
        let server = "Test E2E Server";
        let service = "Test E2E Service";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');

        cy.get('#btn-add-server').click();
        cy.get('#sidePanel').contains('div', 'Add new server').should('be.visible');
        cy.get('#name').type(server);
        cy.get('#type_object_available').select('GPUServer');
        cy.get('#btn-submit-form').click();

        cy.get('div[id$="'+server.replaceAll(' ', '-')+'"]').should('have.class', 'list-group-item')
        cy.get('button[data-bs-target^="#flush-"][data-bs-target$="'+server.replaceAll(' ', '-')+'"]').click();
        cy.get('button[hx-get^="/model_builder/open-create-service-panel"][hx-get$="'+server.replaceAll(' ', '-')+'/"]').click();
        cy.get('#name').type(service);
        cy.get('#provider').select('openai');
        cy.get('#model_name').type('gpt-4');
        cy.get('#sidePanel form').find('button[type="submit"]').click();

        cy.get('#model-builder-modal').should('be.visible');
        cy.get('#model-builder-modal').contains('but is asked');
    });
});
