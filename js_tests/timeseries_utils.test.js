const {
    cumulativeSumFromArray,
    generateTimeIndexLabels
} = require('../theme/static/scripts/timeseries_utils.js');
const { DateTime, Duration } = require("luxon");
global.luxon = { DateTime, Duration };
const {join} = require("node:path");
const {readFileSync} = require("node:fs");

test(
    'Check generateTimeIndexLabels return an Array with the right number of elements and check' +
    ' each elements of the list with Month parameter' +
    ' ', () => {
        let startDate = "2025-06-01";
        let granularity = "month";
        let nbValues = 24;

        let csvPath = join(__dirname, "timeseries_files_test/list_month.csv");
        let csvContent = readFileSync(csvPath, "utf8");
        let lines = csvContent.trim().split("\n");
        let expectedData = lines.slice(1);

        let result = generateTimeIndexLabels(startDate, granularity, nbValues);
        expect(result.length).toBe(24);
        expect(result).toEqual(expectedData);
    }
)

test(
    'Check generateTimeIndexLabels return an Array with the right number of elements and check' +
    ' each elements of the list with Year parameter' +
    ' ', () => {
        let startDate = "2025-06-01";
        let granularity = "year";
        let nbValues = 20;

        let csvPath = join(__dirname, "timeseries_files_test/list_year.csv");
        let csvContent = readFileSync(csvPath, "utf8");
        let lines = csvContent.trim().split("\n");
        let expectedData = lines.slice(1);

        let result = generateTimeIndexLabels(startDate, granularity, nbValues)
        expect(result.length).toBe(20);
        expect(result).toEqual(expectedData);
    }
)

test(
    'Check cumulativeSumFromArray return an Dict with the right number of' +
    ' elements and check index', () => {
        const arrayEmissions = [
            744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744,
            744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744
        ]
        let expected_emissions = [
            744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016, 8760,
            9504, 10176, 10920, 11640, 12384, 13104, 13848, 14592, 15312, 16056, 16776, 17520
        ];
        let result = cumulativeSumFromArray(arrayEmissions);
        expect(expected_emissions).toEqual(result);
    }
)
