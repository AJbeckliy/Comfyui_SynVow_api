import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { registerMediaLoader } from "./dom.js";

registerMediaLoader(app, api, {
    extensionName: "SynVow.VideoUpload",
    nodeName: "SynVowApiVideoLoader",
    widgetName: "video",
    playerName: "videoPlayer",
    mime: "video",
    createElement() {
        const el = document.createElement("video");
        el.controls = true;
        el.classList.add("comfy-video");
        el.style.width = "100%";
        return el;
    },
});
