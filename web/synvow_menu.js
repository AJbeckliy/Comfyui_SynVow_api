/**
 * SynVow 菜单按钮扩展 - 独立悬浮框
 * 布局: ⠿ | SV主按钮 | 👤用户按钮 | ⚙设置按钮
 */
import { app } from "../../../scripts/app.js";
import { $el } from "./dom.js";
import { showLoginDialog, clearAuthFile } from "./synvow_login.js";
import { showRechargeDialog } from "./synvow_recharge.js";
import { showRechargeRecordsDialog } from "./synvow_recharge_records.js";
import { showConsumptionRecordsDialog } from "./synvow_consumption_records.js";
import { showProfileDialog } from "./synvow_profile.js";
import { showModelPriceDialog } from "./synvow_model_price.js";

function loadPos() {
    try { return JSON.parse(localStorage.getItem("sv_float_pos") || "null"); } catch { return null; }
}
function savePos(x, y) {
    localStorage.setItem("sv_float_pos", JSON.stringify({ x, y }));
}

app.registerExtension({
    name: "SynVow.MenuButton",

    async setup() {
        if (document.getElementById("synvow-float")) return;

        const style = document.createElement("style");
        style.textContent = `
            #synvow-float {
                position: fixed; z-index: 99999;
                display: flex; align-items: center;
                background: #2a2a2a; border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.55);
                padding: 6px 10px; gap: 8px;
                user-select: none;
            }
            .sv-drag-handle {
                display: grid; grid-template-columns: repeat(3, 3px); gap: 2.5px;
                padding: 3px 5px; cursor: grab; opacity: 0.3; flex-shrink: 0;
                transition: opacity 0.2s;
            }
            .sv-drag-handle:active { cursor: grabbing; }
            .sv-drag-handle:hover { opacity: 0.6; }
            .sv-drag-handle span { width:2.5px; height:2.5px; border-radius:50%; background:#fff; display:block; }
            .sv-main-btn {
                background: #4a9eff; color: white; border: none;
                padding: 7px 13px; font-size: 12px; font-weight: bold; cursor: pointer;
                display: flex; align-items: flex-end; gap: 5px;
                border-radius: 6px; position: relative; overflow: hidden;
            }
            .sv-main-btn::after {
                content:''; position:absolute; top:-100%; left:-100%; width:200%; height:200%;
                background:linear-gradient(135deg,transparent 40%,rgba(255,255,255,0.4) 50%,transparent 60%);
                animation: sv-shine 5s infinite;
            }
            @keyframes sv-shine { 0%{top:-100%;left:-100%} 50%,100%{top:100%;left:100%} }
            .sv-main-btn:hover { filter: brightness(1.15); }
            .sv-main-label { font-size: 12px; }
            .sv-main-balance { font-size: 14px; }
            /* 登录状态按钮 */
            .sv-user-btn {
                background: #3a3a3a; color: white; border: none;
                padding: 7px 13px; font-size: 13px; cursor: pointer;
                border-radius: 6px; display: flex; align-items: center; gap: 6px;
            }
            .sv-user-btn:hover { background: #484848; }
            .sv-user-icon { font-size: 14px; line-height: 1; }
            /* 设置按钮 */
            .sv-settings-btn {
                background: #3a3a3a; color: #ccc; border: none;
                padding: 7px 10px; font-size: 16px; cursor: pointer;
                border-radius: 6px; line-height: 1; position: relative;
            }
            .sv-settings-btn:hover { background: #484848; color: white; }
            /* 下拉通用 */
            .sv-dropdown {
                position: absolute; top: calc(100% + 6px);
                background: #333; border-radius: 6px; min-width: 140px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.45); z-index: 100000; display: none;
            }
            .sv-dropdown.show { display: block; }
            .sv-dropdown-item {
                padding: 9px 14px; cursor: pointer; color: white; font-size: 13px;
                display: flex; align-items: center; gap: 8px;
            }
            .sv-dropdown-item:hover { background: #444; }
            .sv-dropdown-item:first-child { border-radius: 6px 6px 0 0; }
            .sv-dropdown-item:last-child  { border-radius: 0 0 6px 6px; }
            .sv-divider { height:1px; background:#444; margin:2px 0; }
            .sv-balance-row { padding:7px 14px; color:#888; font-size:12px; pointer-events:none; }
        `;
        document.head.appendChild(style);

        const svIcon = `<img src="/extensions/Comfyui_SynVow_api/xb_icon.svg" style="width:18px;height:18px;pointer-events:none">`;

        // 九点拖拽标识
        const dragHandle = $el("div.sv-drag-handle", {}, Array.from({ length: 9 }, () => $el("span")));

        // 主按钮：图标 + 余额 + 下拉（充值星币）
        const mainBtn = $el("button.sv-main-btn", { id: "sv-main-btn" });
        mainBtn.innerHTML = svIcon;
        mainBtn.appendChild($el("span.sv-main-balance", { id: "sv-main-balance" }));

        const mainMenu = $el("div.sv-dropdown", { id: "sv-main-menu" }, [
            $el("div.sv-dropdown-item", { innerHTML: `<img src="/extensions/Comfyui_SynVow_api/xb_icon.svg" style="width:16px;height:16px"> 充值星币`, onclick: () => { hideMenus(); showRechargeDialog(); } }),
            $el("div.sv-dropdown-item", { textContent: "🔄 刷新余额", onclick: () => { hideMenus(); window.dispatchEvent(new CustomEvent("synvow_refresh_balance")); } }),
        ]);
        mainMenu.style.left = "0";
        const mainBtnWrap = $el("div", { style: "position:relative" }, [mainBtn, mainMenu]);

        // 登录状态按钮 + 下拉
        const userIcon = $el("span.sv-user-icon", { innerHTML: `<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle"><circle cx="12" cy="8" r="4" fill="#4a9eff"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7" fill="#2dd4bf"/></svg>` });
        const userLabel = document.createTextNode(
            (() => { 
                const t = localStorage.getItem("sv_token");
                if (!t || t === "undefined" || t === "") return "未登录";
                try { return JSON.parse(localStorage.getItem("sv_user") || "null")?.nickname || "已登录"; } catch { return "已登录"; } 
            })()
        );
        const userBtn = $el("button.sv-user-btn", { id: "sv-user-btn" }, [userIcon]);
        userBtn.appendChild(userLabel);

        const userMenu = $el("div.sv-dropdown", { id: "sv-user-menu" }, [
            $el("div.sv-dropdown-item", { textContent: "退出登录", style: { color: "#ff6b6b" }, onclick: () => {
                hideMenus();
                if (confirm("确定要退出登录吗？")) {
                    localStorage.removeItem("sv_token");
                    localStorage.removeItem("sv_refresh_token");
                    localStorage.removeItem("sv_user");
                    userLabel.nodeValue = "未登录";
                    userIcon.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle"><circle cx="12" cy="8" r="4" fill="#666"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7" fill="#888"/></svg>`;
                    clearAuthFile();
                }
            }})
        ]);
        userMenu.style.right = "0";

        // 设置按钮 + 下拉（个人中心、充值中心等）
        const settingsBtn = $el("button.sv-settings-btn", { id: "sv-settings-btn", textContent: "⚙" });

        const settingsMenu = $el("div.sv-dropdown", { id: "sv-settings-menu" }, [
            $el("div.sv-dropdown-item", { textContent: "个人中心",  onclick: () => { hideMenus(); showProfileDialog(); } }),
            $el("div.sv-dropdown-item", { textContent: "充值星币",  onclick: () => { hideMenus(); showRechargeDialog(); } }),
            $el("div.sv-dropdown-item", { textContent: "充值记录",  onclick: () => { hideMenus(); showRechargeRecordsDialog(); } }),
            $el("div.sv-dropdown-item", { textContent: "消费记录",  onclick: () => { hideMenus(); showConsumptionRecordsDialog(); } }),
            $el("div.sv-dropdown-item", { textContent: "模型价格",  onclick: () => { hideMenus(); showModelPriceDialog(); } }),
            $el("div.sv-divider"),
        ]);
        settingsMenu.style.right = "0";

        const userBtnWrap = $el("div", { style: "position:relative" }, [userBtn, userMenu]);
        const settingsBtnWrap = $el("div", { style: "position:relative" }, [settingsBtn, settingsMenu]);

        const float = $el("div", { id: "synvow-float" }, [
            dragHandle, mainBtnWrap, userBtnWrap, settingsBtnWrap
        ]);
        document.body.appendChild(float);

        // --- 定位 ---
        const pos = loadPos();
        if (pos) {
            float.style.left = pos.x + "px";
            float.style.top  = pos.y + "px";
        } else {
            requestAnimationFrame(() => {
                float.style.left = (window.innerWidth - float.offsetWidth - 16) + "px";
                float.style.top  = "16px";
            });
        }

        // --- 拖拽 ---
        let dragging = false, ox = 0, oy = 0, moved = false;
        dragHandle.addEventListener("mousedown", (e) => {
            dragging = true; moved = false;
            ox = e.clientX - float.getBoundingClientRect().left;
            oy = e.clientY - float.getBoundingClientRect().top;
            e.preventDefault();
        });
        document.addEventListener("mousemove", (e) => {
            if (!dragging) return;
            moved = true;
            let nx = Math.max(0, Math.min(e.clientX - ox, window.innerWidth  - float.offsetWidth));
            let ny = Math.max(0, Math.min(e.clientY - oy, window.innerHeight - float.offsetHeight));
            float.style.left = nx + "px";
            float.style.top  = ny + "px";
        });
        document.addEventListener("mouseup", () => {
            if (dragging) { dragging = false; if (moved) savePos(parseInt(float.style.left), parseInt(float.style.top)); }
        });

        // --- 菜单交互 ---
        function hideMenus() {
            mainMenu.classList.remove("show");
            userMenu.classList.remove("show");
            settingsMenu.classList.remove("show");
        }

        // 主按钮：点击弹充值下拉
        mainBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            mainMenu.classList.toggle("show");
            userMenu.classList.remove("show");
            settingsMenu.classList.remove("show");
        });

        // 设置按钮
        settingsBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            settingsMenu.classList.toggle("show");
            userMenu.classList.remove("show");
        });

        // 用户按钮：已登录弹退出下拉，未登录直接弹登录框
        userBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const token = localStorage.getItem("sv_token");
            if (token && token !== "undefined" && token !== "") {
                userMenu.classList.toggle("show");
                settingsMenu.classList.remove("show");
            } else {
                hideMenus();
                showLoginDialog();
            }
        });

        document.addEventListener("click", hideMenus);

        // --- 监听登录成功事件，更新用户按钮 ---
        window.addEventListener("synvow_login_success", (e) => {
            const nickname = e.detail?.nickname || "已登录";
            userLabel.nodeValue = nickname;
            userIcon.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:middle"><circle cx="12" cy="8" r="4" fill="#4a9eff"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7" fill="#2dd4bf"/></svg>`;
            // 触发余额刷新
            window.dispatchEvent(new CustomEvent("synvow_refresh_balance"));
        });

        window.addEventListener("synvow_refresh_balance", async () => {
            const token = localStorage.getItem("sv_token");
            if (!token || token === "undefined" || token === "") return;
            try {
                const res = await fetch("/sv_api/account/balance", { headers: { "Authorization": "Bearer " + token } });
                const data = await res.json();
                const mainBalanceEl = document.getElementById("sv-main-balance");
                if (data.code === 200) {
                    const balanceVal = parseFloat(data.data.balance || 0).toFixed(2);
                    if (mainBalanceEl) mainBalanceEl.textContent = " " + balanceVal;
                    try {
                        const user = JSON.parse(localStorage.getItem("sv_user") || "null");
                        if (user?.nickname) userLabel.nodeValue = user.nickname;
                    } catch(_e) {}
                } else if (data.code === 401) {
                    localStorage.removeItem("sv_token");
                    localStorage.removeItem("sv_refresh_token");
                    localStorage.removeItem("sv_user");
                    clearAuthFile();
                    userLabel.nodeValue = "未登录";
                    if (mainBalanceEl) mainBalanceEl.textContent = "";
                }
            } catch(_e) {}
        });

        // --- 加载余额 ---
        if (localStorage.getItem("sv_token") && localStorage.getItem("sv_token") !== "undefined" && localStorage.getItem("sv_token") !== "") {
            setTimeout(async () => {
                const _token = localStorage.getItem("sv_token");
                try {
                    let _res  = await fetch("/sv_api/account/balance", { headers: { "Authorization": "Bearer " + _token } });
                    let _data = await _res.json();
                    if (_data.code === 401) {
                        const _rt = localStorage.getItem("sv_refresh_token");
                        if (_token || _rt) {
                            try {
                                const _rr = await fetch("/sv_api/auth/refresh", {
                                    method: "POST", headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ token: _token || "", refresh_token: _rt || "" })
                                });
                                const _rd = await _rr.json();
                                if (_rd.code === 200 && _rd.data?.access_token) {
                                    localStorage.setItem("sv_token", _rd.data.access_token);
                                    if (_rd.data.refresh_token) localStorage.setItem("sv_refresh_token", _rd.data.refresh_token);
                                    _res  = await fetch("/sv_api/account/balance", { headers: { "Authorization": "Bearer " + _rd.data.access_token } });
                                    _data = await _res.json();
                                }
                            } catch(_e) {}
                        }
                    }
                    const _mainEl = document.getElementById("sv-main-balance");
                    if (_data.code === 200) {
                        const _balVal = parseFloat(_data.data.balance || 0).toFixed(2);
                        if (_mainEl) _mainEl.textContent = " " + _balVal;
                        try {
                            const _user = JSON.parse(localStorage.getItem("sv_user") || "null");
                            if (_user?.nickname) userLabel.nodeValue = _user.nickname;
                        } catch(_e) {}
                    } else if (_data.code === 401) {
                        // token 彻底失效，清除所有认证信息
                        localStorage.removeItem("sv_token");
                        localStorage.removeItem("sv_refresh_token");
                        localStorage.removeItem("sv_user");
                        clearAuthFile();
                        userLabel.nodeValue = "未登录";
                        if (_mainEl) _mainEl.textContent = "";
                    }
                } catch(_e) {
                    const _el = document.getElementById("sv-balance");
                    if (_el) _el.textContent = "连接失败";
                }
            }, 500);
        }
    }
});
