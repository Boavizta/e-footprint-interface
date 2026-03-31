const {
    computeUsageJourneyVolume,
    shouldDisplayTimeseriesChart
} = require('../theme/static/scripts/usage_pattern_timeseries.js');
const { DateTime, Duration } = require("luxon");
global.luxon = { DateTime, Duration };

test(
    'usage journey volume array has right length - yearly case', () => {
    let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 10, "month", 1000, "month")
    expect(Object.keys(dailyUsageJourneyVolume).length).toBe(365);
});

/*
With luxon when a month is shifted in days, 1 month equal to 30 days
 */
test(
    'First daily usage journey volume is computed correctly when no growth - monthly case', () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 0, "month", 1000, "month")
        let firstDay = Object.keys(dailyUsageJourneyVolume)[0];
        let computedValue = dailyUsageJourneyVolume[firstDay];
        let expectedValue = 1000 / 30;
        expect(computedValue).toBeCloseTo(expectedValue, 2);
    }
)

/*
With luxon when a year  is shifted in days, 1 year equal to 365 days
 */
test(
    'First daily usage journey volume is computed correctly when no growth - yearly case', () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 0, "month", 1000, "year")
        let firstDay = Object.keys(dailyUsageJourneyVolume)[0];
        let computedValue = dailyUsageJourneyVolume[firstDay];
        let expectedValue = 1000 / 365;
        expect(computedValue).toBeCloseTo(expectedValue, 2);
    }
)

test(
    "Sum over initial usage journey volume timespan is equal to user input - yearly case", () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 0, "month", 1000, "year")
        let sumOver365FirstDays = 0;
        for (let i = 0; i < 365; i++) {
            sumOver365FirstDays += dailyUsageJourneyVolume[Object.keys(dailyUsageJourneyVolume)[i]];
        }
        expect(sumOver365FirstDays).toBeCloseTo(1000, 2);
    }
)

test(
    "Sum over initial usage journey volume timespan is equal to user input - monthly case", () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 0, "month", 1000, "month")
        let sumOver365FirstDays = 0;
        for (let i = 0; i < 30; i++) {
            sumOver365FirstDays += dailyUsageJourneyVolume[Object.keys(dailyUsageJourneyVolume)[i]];
        }
        expect(sumOver365FirstDays).toBeCloseTo(1000, 2);
    }
)

test(
    'Daily growth rate is correctly computed - monthly case', () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 20, "month", 1000, "month")
        let firstDay = Object.keys(dailyUsageJourneyVolume)[0];
        let secondDay = Object.keys(dailyUsageJourneyVolume)[1];
        let dailyGrowthRate = dailyUsageJourneyVolume[secondDay]/dailyUsageJourneyVolume[firstDay];
        let expectedValue = (1 + 0.2)**(1/30);
        expect(dailyGrowthRate).toBeCloseTo(expectedValue, 4);
    }
)

test(
    'Daily growth rate is correctly computed - yearly case', () => {
        let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        '2021-01-01', 1, "year", 30, "year", 1000, "month")
        let firstDay = Object.keys(dailyUsageJourneyVolume)[0];
        let secondDay = Object.keys(dailyUsageJourneyVolume)[1];
        let dailyGrowthRate = dailyUsageJourneyVolume[secondDay]/dailyUsageJourneyVolume[firstDay];
        let expectedValue = (1 + 0.3)**(1/365);
        expect(dailyGrowthRate).toBeCloseTo(expectedValue, 4);
    }
)

test("Timeseries chart stays desktop-only", () => {
    window.innerWidth = 1199;
    expect(shouldDisplayTimeseriesChart()).toBe(false);

    window.innerWidth = 1200;
    expect(shouldDisplayTimeseriesChart()).toBe(true);
})
