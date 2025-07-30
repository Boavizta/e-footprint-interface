beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

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
        cy.get('#sidePanel').contains('div', 'Add new server').should('exist');
        cy.get('#type_object_available').select('GPUServer');
        cy.get('#GPUServer_name').type(server);
        cy.get('#GPUServer_compute').type(16);

        cy.get('#btn-submit-form').click();
        cy.getObjectCardFromObjectTypeAndName("GPUServer", server).should('have.class', 'list-group-item')
        cy.getObjectCardFromObjectTypeAndName("GPUServer", server).find('button[id^="add-service-to"]').click();
        cy.get('#GenAIModel_name').type(service);
        cy.get('#GenAIModel_provider').select(providerName1);
        cy.get('#GenAIModel_model_name').type(modelName1);
        cy.get('#btn-submit-form').click();

        //edit du service
        cy.getObjectButtonFromObjectTypeAndName("GenAIModel", service).click();

        cy.get('#GenAIModel_provider').select(providerName2);
        cy.get('#GenAIModel_model_name').clear().type(modelName2);
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
        cy.get('#sidePanel').contains('div', 'Add new server').should('exist');
        cy.get('#type_object_available').select('GPUServer');
        cy.get('#GPUServer_name').type(server);
        cy.get('#btn-submit-form').click();

        cy.getObjectCardFromObjectTypeAndName("GPUServer", server).should('have.class', 'list-group-item')
        cy.getObjectCardFromObjectTypeAndName("GPUServer", server).find('button[id^="add-service-to"]').click();
        cy.get('#GenAIModel_name').type(service);
        cy.get('#GenAIModel_provider').select('openai');
        cy.get('#GenAIModel_model_name').type('gpt-4');
        cy.get('#btn-submit-form').click();

        cy.get('#model-builder-modal').should('be.visible');
        cy.get('#model-builder-modal').contains('but is asked');
    });
    it("Install new service and its server through external service button", () => {
        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.get('#btn-add-external-api').click();
        cy.get('#GenAIModel_provider').select('openai');
        cy.get('#GenAIModel_model_name').clear('gpt-4');
        cy.get('#GenAIModel_model_name').type('gpt-4');
        cy.get('#btn-submit-form').click();
        cy.getObjectCardFromObjectTypeAndName('GPUServer', 'Generative AI model 1 API servers').should("be.visible");
        cy.getObjectCardFromObjectTypeAndName("GenAIModel", "Generative AI model 1").should("exist");
    });
});
