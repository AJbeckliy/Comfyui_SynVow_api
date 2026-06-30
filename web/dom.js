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

/** 带 JWT 的 GET 请求，返回解析后的 JSON。 */
export async function authedGet(path, token) {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
    });
    return res.json();
}

/** 统一时间格式化（zh-CN 本地时间）。 */
export function fmtTime(value) {
    return new Date(value).toLocaleString("zh-CN");
}

/** 生成统一的分页 CSS（上一页/下一页按钮 + 页码信息），仅 class 前缀不同。 */
export function paginationCss(prefix) {
    return `
        .${prefix}-pagination { display:flex; justify-content:center; align-items:center; gap:12px; }
        .${prefix}-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .${prefix}-page-btn:hover { border-color:#2dd4bf; }
        .${prefix}-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .${prefix}-page-info { color:#8899aa; font-size:13px; }
    `;
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

function splitFilePath(path) {
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

/**
 * 注册音频/视频加载节点的通用上传/拖拽/预览逻辑（audio 与 video 仅元素类型等参数不同）。
 * cfg: { nodeName, widgetName, playerName, mime, createElement(): HTMLMediaElement, onPlayerSrc?(el, src) }
 */
export function registerMediaLoader(app, api, cfg) {
    const updatePlayer = (playerWidget, src) => {
        const el = playerWidget?.element;
        if (!el) return;
        el.src = src;
        cfg.onPlayerSrc?.(el, src);
    };

    app.registerExtension({
        name: cfg.extensionName,
        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== cfg.nodeName) return;
            const origCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                origCreated?.apply(this, arguments);

                const mediaWidget = this.widgets?.find(w => w.name === cfg.widgetName);
                if (!mediaWidget) return;

                const mediaEl = cfg.createElement();
                const playerWidget = this.addDOMWidget(cfg.playerName, cfg.playerName, mediaEl, { serialize: false });
                playerWidget.serialize = false;

                bindCropPreview(this, mediaEl);

                const syncPlayer = () => updatePlayer(playerWidget, mediaValueToURL(api, app, mediaWidget.value));

                const origCallback = mediaWidget.callback;
                mediaWidget.callback = function (...args) {
                    origCallback?.apply(this, args);
                    syncPlayer();
                };

                const origConfigure = this.onConfigure;
                this.onConfigure = function (...args) {
                    origConfigure?.apply(this, args);
                    syncPlayer();
                };

                syncPlayer();

                this.addWidget("button", "选择文件上传", "", () => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.accept = `${cfg.mime}/*`;
                    input.onchange = async () => {
                        const file = input.files?.[0];
                        if (file) await uploadMediaFile(api, app, mediaWidget, file, src => updatePlayer(playerWidget, src));
                    };
                    input.click();
                }, { serialize: false });

                this.onDragOver = (e) => [...(e.dataTransfer?.items ?? [])].some(
                    i => i.kind === "file" && i.type.startsWith(`${cfg.mime}/`)
                );
                this.onDragDrop = async (e) => {
                    const files = [...(e.dataTransfer?.files ?? [])].filter(f => f.type.startsWith(`${cfg.mime}/`));
                    for (const f of files) await uploadMediaFile(api, app, mediaWidget, f, src => updatePlayer(playerWidget, src));
                    return files.length > 0;
                };
            };
        },
    });
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
