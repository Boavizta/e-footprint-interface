const UNIT_FAMILIES = [
    ["mg", "g", "kg", "t"],
];

function normalizeUnit(unit) {
    if (unit === "tonne") {
        return "t";
    }
    return unit;
}

function getUnitFamily(unit) {
    const normalizedUnit = normalizeUnit(unit);
    return UNIT_FAMILIES.find((family) => family.includes(normalizedUnit)) || null;
}

function convertValue(value, fromUnit, toUnit) {
    const normalizedFrom = normalizeUnit(fromUnit);
    const normalizedTo = normalizeUnit(toUnit);
    const conversionToKg = { mg: 1e-6, g: 1e-3, kg: 1, t: 1e3 };

    if (!(normalizedFrom in conversionToKg) || !(normalizedTo in conversionToKg)) {
        throw new Error(`Unsupported unit conversion from ${fromUnit} to ${toUnit}`);
    }

    return value * conversionToKg[normalizedFrom] / conversionToKg[normalizedTo];
}

function bestDisplayUnit(value, unit) {
    const family = getUnitFamily(unit);
    if (!family) {
        return normalizeUnit(unit);
    }

    const representative = Math.abs(Number(value));
    if (representative === 0) {
        return family[0];
    }

    for (let idx = family.length - 1; idx >= 0; idx -= 1) {
        const candidateUnit = family[idx];
        if (Math.abs(convertValue(representative, unit, candidateUnit)) >= 1) {
            return candidateUnit;
        }
    }

    return family[0];
}

function roundToSigFigs(value, sigFigs = 3) {
    if (value === 0) {
        return 0;
    }
    const digits = sigFigs - Math.floor(Math.log10(Math.abs(value))) - 1;
    const scale = 10 ** digits;
    return Math.round(value * scale) / scale;
}

function formatDisplayNumber(value) {
    if (Object.is(value, -0)) {
        return "0";
    }
    return value.toString();
}

function humanReadableUnit(unit) {
    return normalizeUnit(unit);
}

function formatQuantityForDisplay(value, unit, sigFigs = 3) {
    const displayUnit = bestDisplayUnit(value, unit);
    const convertedValue = convertValue(value, unit, displayUnit);
    const roundedValue = roundToSigFigs(convertedValue, sigFigs);

    return {
        value: roundedValue,
        unit: humanReadableUnit(displayUnit),
        formattedValue: formatDisplayNumber(roundedValue),
    };
}

function formatEmissionsQuantity(value, unit, sigFigs = 3) {
    const formattedQuantity = formatQuantityForDisplay(value, unit, sigFigs);
    return `${formattedQuantity.formattedValue} ${formattedQuantity.unit} CO2-eq`;
}

module.exports = {
    bestDisplayUnit,
    formatDisplayNumber,
    formatEmissionsQuantity,
    formatQuantityForDisplay,
    humanReadableUnit,
    roundToSigFigs,
};
