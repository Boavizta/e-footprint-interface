beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Test - Toolbars import/export/reboot", () => {
    let ujName = "Test E2E UJ";
    let ujsOne = "Test E2E UJ 1";
    let ujsTwo = "Test E2E UJ 2";
    let server = "Test E2E Server";
    let service = "Test E2E Service";
    let jobOne = "Test E2E Job 1";
    let jobTwo = "Test E2E Job 2";
    let upName = "Test E2E Usage Pattern";
    let newSystemName = "New_system_name";

    it("Import one JSON file when the model is empty and check that objects have been added", () => {
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

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+server.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsTwo.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobOne.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobTwo.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+service.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
    });

    it("Import a new JSON file when the model already contained objets to check previous objects are removed and" +
        "  new objets has been added", () => {
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

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+server.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsTwo.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobOne.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobTwo.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+service.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');

        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('input[type="file"]').then(($input) => {
          expect($input[0].files.length).to.equal(1);
          expect($input[0].files[0].name).to.equal('efootprint-model-system-data.json');
        });

        cy.window().then((win) => {
          cy.spy(win, 'initLeaderLines').as('initLeaderLines');
        });
        cy.get('button[type="submit"]').click();
        cy.get('@initLeaderLines').should('have.been.called');

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujName.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+server.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+ujsTwo.replaceAll(' ', '-')+'"]').should('exist').should('be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobOne.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+jobTwo.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
        cy.get('button[id^="button-id-"][id$="'+service.replaceAll(' ', '-')+'"]').should('exist').should('not.be.visible');
    });

    it("check if we reset the model all objets and leaderlines have been removed", () => {
        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.get('input[type="file"]').should("not.exist");

        cy.get('a[id="btn-reboot-modeling"]').click();
        cy.wait(500);

        cy.get('button[id^="button-id-"][id$="'+upName.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+ujName.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+server.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+ujsOne.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+ujsTwo.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+jobOne.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="button-id-"][id$="'+jobTwo.replaceAll(' ', '-')+'"]').should('not.exist');
        cy.get('button[id^="id-"][id$="'+service.replaceAll(' ', '-')+'"]').should('not.exist');

        //there is only one card and it must cointain the text "My first usage journey"
        cy.get('div[class*="card"]').should('have.length',1);
        cy.get('div[class*="card"]').should('contain.text','My first usage journey');
        cy.get('div[class*="card"]').should('contain.text','My first usage journey step');
    });

    it("Change the name of the model and check that the name has been changed", () => {
        cy.visit("/model_builder/");
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.get('input[type="file"]').should("not.exist");

        cy.get('#btn-change-system-name').should('exist').click()
        cy.get('#name').should('exist').clear().type(newSystemName);
        cy.get('#btn-submit-form').should('exist').click();
        cy.get('#system-name').should('contain.text', newSystemName);
        //refresh the page to check that the name is still there
        cy.reload();
        cy.get('#system-name').should('contain.text', newSystemName);
    });

    it("Export a model and check that the file has been downloaded and is correctly named", () => {
        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('button[type="submit"]').click();
        cy.get('input[type="file"]').should("not.exist");

        let now = new Date();
        let nowUtc = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
        let day = String(nowUtc.getDate()).padStart(2, '0');
        let month = String(nowUtc.getMonth() + 1).padStart(2, '0');
        let year = nowUtc.getFullYear();
        let hours = String(nowUtc.getHours()).padStart(2, '0');
        let minutes = String(nowUtc.getMinutes()).padStart(2, '0');
        let fileName = `${year}-${month}-${day} ${hours}_${minutes} UTC system 1.e-f.json`;

        //to get the filedownload in cypress, we need to remove the target blank attribute
        cy.intercept('GET', '**/download-json/**').as('fileDownload');
        cy.get('a[href="download-json/"]')
          .invoke('removeAttr', 'target')
          .click();

        cy.wait('@fileDownload').then((interception) => {
            const contentDisposition = interception.response.headers['content-disposition'];
            expect(contentDisposition).to.include('attachment');
            expect(contentDisposition).to.include(fileName);
        });

    });
});
