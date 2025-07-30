beforeEach(() => {
  cy.clearCookies();
  cy.clearLocalStorage();
});

describe("Calculated attributes", () => {
    it("Navigate between calculated attributes", () => {
        let ujsOne = "Test E2E UJ 1";
        let jobOne = "Test E2E Job 1";

        cy.loadEfootprintTestModel('cypress/fixtures/efootprint-model-system-data-multiple.json');

        cy.getObjectCardFromObjectTypeAndName("UsageJourneyStep", ujsOne).find("svg[id^='icon_accordion_']").should('be.visible').click();
        cy.getObjectButtonFromObjectTypeAndName("WebApplicationJob", jobOne).should('exist').click();
        cy.get("button[data-bs-target='#collapseCalculatedAttributesWebApplicationJob']").should('exist').click();

        cy.get("button[data-bs-target='#collapse-calculated_attributes_hourly_occurrences_per_usage_pattern").should('be.enabled').click();
        cy.get('button[hx-get="/model_builder/get_explainable_hourly_quantity_chart_and_explanation/id-4f5352-Test-E2E-Job-1/hourly_occurrences_per_usage_pattern/id-77cd46-UP3"').should("exist").click();
        cy.window().its('calculatedAttributesChart').should('exist');
        cy.get('button[hx-get="/model_builder/get_explainable_hourly_quantity_chart_and_explanation/id-4f5352-Test-E2E-Job-1/hourly_avg_occurrences_across_usage_patterns/"').should("exist").click();
        cy.window().its('calculatedAttributesChart').should('exist');
        cy.get('button[hx-get="/model_builder/get_calculated_attribute_explanation/id-4f5352-Test-E2E-Job-1/request_duration/"').should("exist").click();
        cy.get("#ancestors-formula-and-children-request_duration-in-id-4f5352-Test-E2E-Job-1").should("exist");
    });
});
