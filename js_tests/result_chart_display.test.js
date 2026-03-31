const {
    bestDisplayUnit,
    formatDisplayNumber,
    formatEmissionsQuantity,
    formatQuantityForDisplay,
} = require("../theme/static/scripts/result_charts/display.js");

test("bestDisplayUnit keeps kilogram values when they already fit well", () => {
    expect(bestDisplayUnit(420, "kg")).toBe("kg");
});

test("bestDisplayUnit promotes kilogram values to tonnes when appropriate", () => {
    expect(bestDisplayUnit(4200, "kg")).toBe("t");
});

test("formatQuantityForDisplay rounds to three significant figures", () => {
    expect(formatQuantityForDisplay(1234, "kg")).toEqual({
        value: 1.23,
        unit: "t",
        formattedValue: "1.23",
    });
});

test("formatQuantityForDisplay trims trailing zeroes", () => {
    expect(formatQuantityForDisplay(1200, "kg")).toEqual({
        value: 1.2,
        unit: "t",
        formattedValue: "1.2",
    });
});

test("formatDisplayNumber normalizes negative zero", () => {
    expect(formatDisplayNumber(-0)).toBe("0");
});

test("formatEmissionsQuantity builds the tooltip label with dynamic unit scaling", () => {
    expect(formatEmissionsQuantity(0.00042, "t")).toBe("420 g CO2-eq");
});
