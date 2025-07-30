Cypress.Commands.add("loadEfootprintTestModel", (filePath = 'cypress/fixtures/efootprint-model-system-data.json') => {
  cy.visit("/model_builder/");
  cy.get("#model-canva").should("be.visible");
  cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
  cy.get('input[type="file"]').selectFile(filePath);
  cy.get('input[type="file"]').should(($input) => {
          expect($input[0].files.length).to.equal(1);
          expect(filePath).to.satisfy(name => name.endsWith($input[0].files[0].name));
        });
  cy.intercept('POST', '/model_builder/upload-json').as('importModel');
  cy.get('button[type="submit"]').click();
  cy.wait('@importModel');
  cy.get("#sidePanelForm").should("not.exist");
});

Cypress.Commands.add('getObjectCardFromObjectTypeAndName', (objectType, name) => {
  return cy.contains(`div[id^="${objectType}"] p`, name).closest(`div[id^="${objectType}"]`);
});

Cypress.Commands.add('getObjectButtonFromObjectTypeAndName', (objectType, name) => {
  return cy.getObjectCardFromObjectTypeAndName(objectType, name).find(`button[id^="button-${objectType}-"]`);
});
