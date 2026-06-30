import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { registerMediaLoader } from "./dom.js";

registerMediaLoader(app, api, {
    extensionName: "SynVow.AudioUpload",
    nodeName: "SynVowApiAudioLoader",
    widgetName: "audio",
    playerName: "audioPlayer",
    mime: "audio",
    createElement() {
        const el = document.createElement("audio");
        el.controls = true;
        el.classList.add("comfy-audio");
        el.setAttribute("name", "media");
        return el;
    },
    onPlayerSrc(el, src) {
        el.classList.toggle("empty-audio-widget", !src);
    },
});
