window.chartJSOptions = {
    responsive: true,
    scales: {
        x: {
            offset: true,
            stacked: true,
            type: 'time',
            time: {
                tooltipFormat: 'yyyy',
                unit: 'year'
            },
            title: { display: false },
            grid: { display: false }
        },
        y: {
            stacked: true,
            title: {
                display: true,
                text: "Total CO2 emissions in metric tons",
                color: "rgb(107,114,128)"
            },
        },
    },
    plugins: {
        legend: {
            position: "bottom",
        },
        title: {
            display: true,
            text: 'Total CO2 emissions in metric tons',
            color: "rgb(107,114,128)"
        },
        tooltip: {
            mode: "index",
            intersect: false,
        },
    },
}

window.baseChartConfigByHardwareType = {
    'Servers_and_storage_energy': {
        label: "Servers and storage usage",
        backgroundColor: "#C6FFF9",
    },
    'Devices_energy': {
        label: "Devices usage",
        backgroundColor: "#44E0D9",
    },
    'Network_energy': {
        label: "Network usage",
        backgroundColor: "#00A3A1",
    },
    'Servers_and_storage_fabrication': {
        label: "Servers and storage fabrication",
        backgroundColor: "#DEECF8",
    },
    'Devices_fabrication': {
        label: "Devices fabrication",
        backgroundColor: "#A3CDED",
    }
}

function drawResultChart(chartType, resultsTemporalGranularity){
    let chartData = {labels: [], datasets: []}

    for (const hardwareType of Object.keys(window.hardwareTypeDailyEmissions)) {
        let hardwareTypeDataAndConfig = {...window.baseChartConfigByHardwareType[hardwareType]};
        let chartValues = Object.values(
            sumDailyValuesByDisplayGranularity(
                window.hardwareTypeDailyEmissions[hardwareType], resultsTemporalGranularity));
        if(chartType === "line"){
            chartValues = cumulativeSumFromArray(chartValues)
            hardwareTypeDataAndConfig["borderWidth"] = 1;
            hardwareTypeDataAndConfig["fill"] = true;
        }
        hardwareTypeDataAndConfig["data"] = chartValues;
        chartData["datasets"].push(hardwareTypeDataAndConfig);
    }

    chartData.labels = generateTimeIndexLabels(
        window.emissions['Servers_and_storage_energy']['start_date'], resultsTemporalGranularity,
        chartData["datasets"][0]["data"].length);

    window.chartJSOptions.scales.x.time.unit = resultsTemporalGranularity === "month" ? "month" : "year";
    window.chartJSOptions.scales.x.time.tooltipFormat = resultsTemporalGranularity === "month" ? "MMM yyyy" : "yyyy";

    if (window.charts[chartType+'Chart']) {
        window.charts[chartType+'Chart'].destroy();
        window.charts[chartType+'Chart'] = null;
    }

    let area_ctx = document.getElementById(chartType + "Chart").getContext("2d");

    window.charts[chartType+'Chart'] = new Chart(area_ctx, {
        chart:{height: '400px'},
        type: chartType,
        data: chartData,
        options: window.chartJSOptions
    });
}

function drawBarResultChart(){
    let resultsTemporalGranularity = document.getElementById('results_temporal_granularity').value;
    drawResultChart('bar', resultsTemporalGranularity);
}



function convertHourlyToDailyEmissionsByHardwareType(emissions) {
    let dailyEmissionsDataByHardwareType = {}

    for (const hardwareType of Object.keys(emissions)) {
        let values = emissions[hardwareType]['values']
        let startDate = luxon.DateTime.fromFormat(emissions[hardwareType]['start_date'], "yyyy-MM-dd HH:mm:ss",
            {zone: "utc"});
        let datesCorrespondingToValueTimestamps = [];
        for (let nbHoursSinceFirstValue = 0; nbHoursSinceFirstValue < values.length; nbHoursSinceFirstValue++) {
            datesCorrespondingToValueTimestamps.push(startDate.plus({hours: nbHoursSinceFirstValue}).toISODate());
        }
        dailyEmissionsDataByHardwareType[hardwareType] = datesCorrespondingToValueTimestamps.reduce(
            function (previousDict, dateAtIndex, index) {
                if (!previousDict[dateAtIndex]) {
                    previousDict[dateAtIndex] = 0;
                }
                previousDict[dateAtIndex] += values[index];
                return previousDict;
            },
            /* initial value of previousDict */
            {}
        )
    }
    return dailyEmissionsDataByHardwareType;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        convertHourlyToDailyEmissionsByHardwareType
    };
}
