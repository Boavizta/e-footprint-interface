beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Calculus graph", () => {
    it("Make sure simple calculus graph opens", () => {
        let ujsOne = "Test E2E UJ 1";
        let jobOne = "Test E2E Job 1";

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

        cy.get("svg[id^='icon_accordion_id-'][id*='"+ujsOne.replaceAll(' ', '-')+"']").should('be.visible').click();
        cy.get("button[id^='button-id-'][id$='"+jobOne.replaceAll(' ', '-')+"']").should('exist').click();
        cy.get("button[data-bs-target='#collapseCalculatedAttributesWebApplicationJob']").should('exist').click();

        cy.get("button[data-bs-target='#collapse-calculated_attributes-ram_needed").should('be.enabled').click();
        cy.get("a[href^='/model_builder/display-calculus-graph/'][href$='ram_needed/']").then(($a) => {
            const url = $a.prop('href');
            cy.visit(url);cy.get('iframe').should('exist');
            cy.get('iframe').each(($iframe) => {
                cy.wrap($iframe)
                    .its('0.contentDocument.body')
                    .should('not.be.empty')
                    .then((body) => {
                        cy.wrap(body).find('script[type="text/javascript"]').should('exist');
                        cy.wrap(body).find('#mynetwork').should('exist');
                    });
            });
        });
    });

    it("Make sure complex calculus graph opens", () => {
        let ujsOne = "Test E2E UJ 1";
        let jobOne = "Test E2E Job 1";

        cy.visit("/");
        cy.get('#btn-start-modeling-my-service').click();
        cy.get('#model-canva').should('be.visible');
        cy.get('button[hx-get="/model_builder/open-import-json-panel/"]').click();
        let fileTest = 'cypress/fixtures/efootprint-model-system-data-multiple.json'
        cy.get('input[type="file"]').selectFile(fileTest);
        cy.get('input[type="file"]').then(($input) => {
          expect($input[0].files.length).to.equal(1);
          expect($input[0].files[0].name).to.equal('efootprint-model-system-data-multiple.json');
        });
        cy.get('button[type="submit"]').click();

        cy.get("svg[id^='icon_accordion_id-'][id*='"+ujsOne.replaceAll(' ', '-')+"']").should('be.visible').click();
        cy.get("button[id^='button-id-'][id$='"+jobOne.replaceAll(' ', '-')+"']").should('exist').click();
        cy.get("button[data-bs-target='#collapseCalculatedAttributesWebApplicationJob']").should('exist').click();

        cy.get("button[data-bs-target='#collapse-calculated_attributes_hourly_occurrences_per_usage_pattern").should('be.enabled').click();
        cy.get("a[href^='/model_builder/display-calculus-graph/id-4f5352-Test-E2E-Job-1/hourly_occurrences_per_usage_pattern/id-77cd46-UP3']").then(($a) => {
            const url = $a.prop('href');
            cy.visit(url);
            cy.get('iframe').should('exist');
            cy.get('iframe').each(($iframe) => {
                cy.wrap($iframe)
                    .its('0.contentDocument.body')
                    .should('not.be.empty')
                    .then((body) => {
                        cy.wrap(body).find('script[type="text/javascript"]').should('exist');
                        cy.wrap(body).find('#mynetwork').should('exist');
                    });
            });
        });
    });
});
