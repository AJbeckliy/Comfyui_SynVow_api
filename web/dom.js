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
