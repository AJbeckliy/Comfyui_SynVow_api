import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "SynVow.RunIndex",
    async setup(app) {
        const originalQueuePrompt = app.queuePrompt;
        app.queuePrompt = async function(...args) {
            try {
                await api.fetchApi("/synvow/reset_run_index", { method: "POST" });
            } catch (e) {
                console.error("SynVow RunIndex reset failed:", e);
            }
            return originalQueuePrompt.apply(this, args);
        };
    }
});
