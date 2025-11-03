let timeSeriesChartJSOptions = {
    locale: "en-EN",
    responsive: true,
    maintainAspectRatio: false,
    scales: {
        x: {
            type: 'time',
            time: {
                tooltipFormat: 'yyyy',
                unit: 'year'
            },
            title: { display: false },
            grid: { display: false }
        },
        y: {
            display: true,
            title: {
                display: true,
                text: 'Number of usage journeys',
            },
            beginAtZero: true
        }
    },
    plugins: {
        tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    let value = context.parsed.y;
                    if (value !== null && value !== undefined) {
                        value = value.toFixed(1);
                    }
                    return `${label}: ${value}`;
                }
            }
        },
        legend: { display: false },
        responsive: true,
        maintainAspectRatio: false,
        zoom: {
            zoom: {
                drag: {enabled: true,},
                pinch: {enabled: true},
                mode: 'x',
            }
        }
    }
};

function openOrCloseTimeseriesChartAndTriggerUpdate() {
    if( window.innerWidth < 1200){return}
    let element = document.getElementById("chartTimeseries");
    let sidePanel = document.getElementById("sidePanelContent");
    let startDate = sidePanel.querySelector('[id$="start_date"]').value;
    let modelingDurationValue = sidePanel.querySelector('[id$="modeling_duration_value"]').value;
    let initialUsageJourneyVolume = sidePanel.querySelector('[id$="initial_volume"]').value;
    let netGrowthRateInPercentage = sidePanel.querySelector('[id$="net_growth_rate_in_percentage"]').value;
    if(
        startDate !==""
        && (modelingDurationValue !== "" && modelingDurationValue > 0)
        && (initialUsageJourneyVolume !== "" && initialUsageJourneyVolume > 0)
        && (netGrowthRateInPercentage !== "")
    ){
        if(element.classList.contains("d-none")){
            element.classList.remove("d-none");
            element.classList.add("d-block");
        }
        createOrUpdateTimeSeriesChart();
    }else{
        if(element.classList.contains("d-block")) {
            element.classList.remove("d-block");
            element.classList.add("d-none");
            if (window.chart) {
                window.chart.destroy();
                window.chart = null;
            }
        }
    }
}

function closeTimeseriesChart() {
    if(window.chart){
        let element = document.getElementById("chartTimeseries");
        element.classList.remove("d-block");
        element.classList.add("d-none");
        window.chart.destroy();
        window.chart = null;
    }
}

function applyMaxLimitOnModelingDurationValue() {
    let sidePanel = document.getElementById("sidePanelContent");
    let inputValue = sidePanel.querySelector('[id$="modeling_duration_value"]');
    let inputUnit = sidePanel.querySelector('[id$="modeling_duration_unit"]').value;
    let currentValue = parseInt(inputValue.value);
    let maxValue = parseInt(inputValue.max);
    let errorElement = document.getElementById('modeling_duration_value_error_message');
    if(currentValue <= 0 || isNaN(currentValue) || !currentValue){
        errorElement.innerHTML = "Modeling duration value must be greater than 0 and can't be empty";
        errorElement.style.display = "block";
        if (inputUnit === 'month'){inputValue.value= 12}else{inputValue.value= 1}
    }else if (currentValue > maxValue) {
        errorElement.innerHTML = `Modeling duration value must be less than or equal to ${maxValue}`;
        errorElement.style.display = "block";
        inputValue.value = maxValue;
    }else{
        errorElement.innerHTML ='';
        errorElement.style.display = "none";
    }
}

function createOrUpdateTimeSeriesChart(){
    let sidePanel = document.getElementById("sidePanelContent");
    let startDate = luxon.DateTime.fromISO(sidePanel.querySelector('[id$="start_date"]').value);
    let modelingDurationValue = parseInt(sidePanel.querySelector('[id$="modeling_duration_value"]').value);
    let modelingDurationUnit = sidePanel.querySelector('[id$="modeling_duration_unit"]').value;
    let initialUsageJourneyVolume = parseInt(sidePanel.querySelector('[id$="initial_volume"]').value);
    let initialUsageJourneyVolumeTimespan = sidePanel.querySelector('[id$="initial_volume_timespan"]').value;
    let netGrowthRateInPercentage = parseInt(sidePanel.querySelector('[id$="net_growth_rate_in_percentage"]').value);
    let netGrowthRateTimespan = sidePanel.querySelector('[id$="net_growth_rate_timespan"]').value;

    let dailyUsageJourneyVolume = computeUsageJourneyVolume(
        startDate, modelingDurationValue, modelingDurationUnit, netGrowthRateInPercentage, netGrowthRateTimespan,
        initialUsageJourneyVolume, initialUsageJourneyVolumeTimespan);

    let displayGranularity = document.getElementById('display_granularity').value;
    let usageJourneyVolume = sumDailyValuesByDisplayGranularity(
        Object.keys(dailyUsageJourneyVolume), Object.values(dailyUsageJourneyVolume), displayGranularity);

    if (window.chart) {
        window.chart.destroy();
        window.chart = null;
    }

    timeSeriesChartJSOptions.scales.x.time.unit = displayGranularity === "month" ? "month" : "year";
    timeSeriesChartJSOptions.scales.x.time.tooltipFormat = displayGranularity === "month" ? "MMM yyyy" : "yyyy";

    const ctx = document.getElementById("timeSeriesChart").getContext('2d');
    window.chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: Object.keys(usageJourneyVolume),
            datasets: [{
                label: 'Nb of usage journeys',
                borderColor: '#017E7E',
                backgroundColor: '#017E7E',
                data: Object.values(usageJourneyVolume),
                fill: false,
                tension: 0.5
            }]
        },
        options: timeSeriesChartJSOptions
    });
}

function computeUsageJourneyVolume(
    startDate, modelingDurationValue, modelingDurationUnit, netGrowthRateInPercentage, netGrowthRateTimespan,
    initialUsageJourneyVolume, initialUsageJourneyVolumeTimespan) {
    let dailyUsageJourneyVolume = {};

    let luxonStartDate = luxon.DateTime.fromISO(startDate);
    let luxonModelingDuration = luxon.Duration.fromObject({ [modelingDurationUnit]: modelingDurationValue });
    let luxonNetGrowthRateTimespan = luxon.Duration.fromObject({ [netGrowthRateTimespan]: 1 });
    let luxonInitialUsageJourneyVolumeTimespan = luxon.Duration.fromObject({ [initialUsageJourneyVolumeTimespan]: 1 });

    let modelingDurationInDays = luxonModelingDuration.shiftTo('days')['days'];
    let growthRateTimespanInDays = luxonNetGrowthRateTimespan.shiftTo('days')['days'];
    let initialUsageJourneyVolumeTimespanInDays = luxonInitialUsageJourneyVolumeTimespan.shiftTo('days')['days'];

    let dailyGrowthRate = (1 + netGrowthRateInPercentage/100) ** (1/growthRateTimespanInDays);
    let exponentialGrowthSumOverInitialUsageJourneyVolumeTimespan;
    if (dailyGrowthRate === 1) {
        exponentialGrowthSumOverInitialUsageJourneyVolumeTimespan = initialUsageJourneyVolumeTimespanInDays;
    } else {
        exponentialGrowthSumOverInitialUsageJourneyVolumeTimespan =
        (dailyGrowthRate ** initialUsageJourneyVolumeTimespanInDays - 1) / (dailyGrowthRate - 1);
    }
    let firstDailyUsageJourneyVolume = initialUsageJourneyVolume / exponentialGrowthSumOverInitialUsageJourneyVolumeTimespan;

    let dateLooper = luxonStartDate;
    let dailyUsageJourneyVolumeLooper = firstDailyUsageJourneyVolume;
    for(let day_nb = 0; day_nb < modelingDurationInDays; day_nb++){
        dailyUsageJourneyVolume[dateLooper.toISO()] = dailyUsageJourneyVolumeLooper;
        dailyUsageJourneyVolumeLooper *= dailyGrowthRate;
        dateLooper = luxonStartDate.plus({ ["day"]: (day_nb+1)});
    }
    return dailyUsageJourneyVolume;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        computeUsageJourneyVolume
    };
}
