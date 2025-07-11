import {defineConfig} from "cypress";


module.exports = defineConfig({
    e2e: {
        baseUrl: "http://localhost:8000/",
          setupNodeEvents(on, config) {
        },
        experimentalStudio: true,
    },
    viewportWidth: 1920,
    viewportHeight: 1200,
});
