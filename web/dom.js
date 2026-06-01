/**
 * Minimal DOM helper to avoid depending on deprecated ComfyUI ui.js APIs.
 */
export function $el(selector, attrs = {}, children = []) {
    const { tagName, id, classNames } = parseSelector(selector || "div");
    const el = document.createElement(tagName);

    if (id) {
        el.id = id;
    }
    if (classNames.length) {
        el.className = classNames.join(" ");
    }

    applyAttrs(el, attrs);
    appendChildren(el, children);
    return el;
}

function parseSelector(selector) {
    const firstDot = selector.indexOf(".");
    const firstHash = selector.indexOf("#");
    const splitAt = [firstDot, firstHash].filter(i => i >= 0).sort((a, b) => a - b)[0];

    const tagName = splitAt === undefined ? selector : selector.slice(0, splitAt);
    const rest = splitAt === undefined ? "" : selector.slice(splitAt);

    let id = "";
    const classNames = [];
    let token = "";
    let mode = "";

    for (const ch of rest) {
        if (ch === "." || ch === "#") {
            if (token) {
                if (mode === "#") id = token;
                if (mode === ".") classNames.push(token);
            }
            mode = ch;
            token = "";
        } else {
            token += ch;
        }
    }
    if (token) {
        if (mode === "#") id = token;
        if (mode === ".") classNames.push(token);
    }

    return {
        tagName: tagName || "div",
        id,
        classNames
    };
}

function applyAttrs(el, attrs) {
    for (const [key, value] of Object.entries(attrs || {})) {
        if (value === undefined || value === null) continue;

        if (key === "dataset" && typeof value === "object") {
            for (const [dk, dv] of Object.entries(value)) {
                el.dataset[dk] = String(dv);
            }
            continue;
        }

        if (key === "style" && typeof value === "object") {
            for (const [sk, sv] of Object.entries(value)) {
                el.style[sk] = sv;
            }
            continue;
        }

        if (key in el) {
            el[key] = value;
            continue;
        }

        el.setAttribute(key, String(value));
    }
}

function appendChildren(el, children) {
    const list = Array.isArray(children) ? children : [children];
    for (const child of list) {
        if (child === null || child === undefined || child === false) continue;
        if (child instanceof Node) {
            el.appendChild(child);
        } else {
            el.appendChild(document.createTextNode(String(child)));
        }
    }
}

export const API_BASE = "/sv_api";

export function getToken() {
    const t = localStorage.getItem("sv_token");
    return (t && t !== "undefined" && t !== "") ? t : null;
}

export function injectStyle(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.head.appendChild(s);
}

export async function postJson(path, body, token) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body)
    });
    return res.json();
}

export function splitFilePath(path) {
    const idx = path.lastIndexOf("/");
    return idx === -1 ? ["", path] : [path.substring(0, idx), path.substring(idx + 1)];
}

/**
 * 上传媒体文件到 ComfyUI input 目录，更新 combo widget，并回调播放器。
 * 复用于音频与视频加载节点。
 */
export async function uploadMediaFile(api, app, comboWidget, file, onResolved) {
    const body = new FormData();
    body.append("image", file);
    const resp = await api.fetchApi("/upload/image", { method: "POST", body });
    if (resp.status !== 200) {
        console.error("Upload failed:", resp.status, resp.statusText);
        return false;
    }
    const data = await resp.json();
    let name = data.name;
    if (data.subfolder) name = data.subfolder + "/" + name;
    if (!comboWidget.options.values.includes(name)) {
        comboWidget.options.values.push(name);
    }
    comboWidget.value = name;
    comboWidget.callback?.(name);
    const [subfolder, filename] = splitFilePath(name);
    const url = api.apiURL(`/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${subfolder}&${app.getRandParam().substring(1)}`);
    onResolved?.(url);
    return true;
}

/** 根据 combo 当前值构造 input 目录媒体的访问 URL（无值时返回空串）。 */
export function mediaValueToURL(api, app, value) {
    if (!value) return "";
    const [subfolder, filename] = splitFilePath(value);
    return api.apiURL(`/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${subfolder}&${app.getRandParam().substring(1)}`);
}

/**
 * 将媒体播放器限制在 [起始秒, 起始秒+裁剪秒数] 区间内播放，实时预览裁剪范围。
 * 裁剪秒数<=0 时不限制（播放整段）。返回解绑函数。
 */
export function bindCropPreview(node, mediaEl) {
    const startW = node.widgets?.find(w => w.name === "起始秒");
    const durW = node.widgets?.find(w => w.name === "裁剪秒数");
    if (!mediaEl || (!startW && !durW)) return () => {};

    const getStart = () => Math.max(0, Number(startW?.value) || 0);
    const getDur = () => Math.max(0, Number(durW?.value) || 0);

    const clampToStart = () => {
        const start = getStart();
        if (Number.isFinite(mediaEl.duration) && start < mediaEl.duration) {
            mediaEl.currentTime = start;
        }
    };

    const onTimeUpdate = () => {
        const start = getStart();
        const dur = getDur();
        if (dur <= 0) return;
        const end = start + dur;
        if (mediaEl.currentTime < start) mediaEl.currentTime = start;
        if (mediaEl.currentTime >= end) {
            mediaEl.pause();
            mediaEl.currentTime = start;
        }
    };

    mediaEl.addEventListener("loadedmetadata", clampToStart);
    mediaEl.addEventListener("play", () => {
        if (getDur() > 0 && mediaEl.currentTime >= getStart() + getDur()) clampToStart();
    });
    mediaEl.addEventListener("timeupdate", onTimeUpdate);

    const wrapCallback = (w) => {
        if (!w) return;
        const orig = w.callback;
        w.callback = function (...args) {
            orig?.apply(this, args);
            clampToStart();
        };
    };
    wrapCallback(startW);
    wrapCallback(durW);

    return () => {
        mediaEl.removeEventListener("loadedmetadata", clampToStart);
        mediaEl.removeEventListener("timeupdate", onTimeUpdate);
    };
}
