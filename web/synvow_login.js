/**
 * SynVow 登录对话框
 */
import { $el } from "./dom.js";

let loginDialog = null;
let wechatDialog = null;
let wechatPollTimer = null;
let wechatMessageListener = null;
const API_BASE = "/sv_api";
const wechatIcon = `<svg viewBox="0 0 1024 1024"><path d="M690.1 377.4c5.9 0 11.8.2 17.6.5-24.4-128.7-158.3-227.1-319.9-227.1C209 150.8 64 271.4 64 420.2c0 81.1 43.6 154.2 111.9 203.6 5.5 3.9 9.1 10.3 9.1 17.6 0 2.4-.5 4.6-1.1 6.9-5.5 20.3-14.2 52.8-14.6 54.3-.7 2.6-1.7 5.2-1.7 7.9 0 5.9 4.8 10.8 10.8 10.8 2.3 0 4.2-.9 6.2-2l70.9-40.9c5.3-3.1 11-5 17.2-5 3.2 0 6.4.5 9.5 1.4 33.1 9.5 68.8 14.8 105.7 14.8 6 0 11.9-.1 17.8-.4-7.1-21-10.9-43.1-10.9-66 0-135.8 132.2-245.8 295.3-245.8zm-194.3-86.5c23.8 0 43.2 19.3 43.2 43.1s-19.3 43.1-43.2 43.1c-23.8 0-43.2-19.3-43.2-43.1s19.4-43.1 43.2-43.1zm-215.9 86.2c-23.8 0-43.2-19.3-43.2-43.1s19.3-43.1 43.2-43.1 43.2 19.3 43.2 43.1-19.4 43.1-43.2 43.1zm586.8 415.6c56.9-41.2 93.2-102 93.2-169.7 0-124-108.1-224.8-241.4-224.8-133.4 0-241.4 100.8-241.4 224.8S585 847.1 718.3 847.1c30.8 0 60.6-4.4 88.1-12.3 2.6-.8 5.2-1.2 7.9-1.2 5.2 0 9.9 1.6 14.3 4.1l59.1 34c1.7 1 3.3 1.7 5.2 1.7a9 9 0 0 0 6.4-2.6 9 9 0 0 0 2.6-6.4c0-2.2-.9-4.4-1.4-6.6-.3-1.2-7.6-28.3-12.2-45.3-.5-1.9-.9-3.8-.9-5.7.1-5.9 3.1-11.2 7.6-14.5zM600.2 587.2c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9c0 19.8-16.2 35.9-36 35.9zm179.9 0c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9a36.08 36.08 0 0 1-36 35.9z" fill="white"/></svg>`;

export function showLoginDialog() {
    if (loginDialog) { loginDialog.style.display = "flex"; return; }

    const style = document.createElement('style');
    style.textContent = `
        .sv-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10000; }
        .sv-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:40px; width:400px; position:relative; }
        .sv-title { color:#2dd4bf; font-size:28px; font-weight:bold; margin-bottom:10px; }
        .sv-subtitle { color:#8899aa; font-size:14px; margin-bottom:30px; }
        .sv-input { width:100%; background:transparent; border:1px solid #334455; border-radius:8px; padding:14px 16px; color:white; font-size:14px; margin-bottom:16px; box-sizing:border-box; }
        .sv-input::placeholder { color:#667788; }
        .sv-input:focus { outline:none; border-color:#2dd4bf; }
        .sv-forgot { text-align:right; margin-bottom:20px; }
        .sv-forgot a { color:#8899aa; font-size:13px; text-decoration:none; }
        .sv-forgot a:hover { color:#2dd4bf; }
        .sv-btn { width:100%; background:linear-gradient(90deg,#2dd4bf,#22d3ee); border:none; border-radius:8px; padding:14px; color:white; font-size:16px; font-weight:bold; cursor:pointer; margin-bottom:24px; }
        .sv-btn:hover { filter:brightness(1.1); }
        .sv-wechat { text-align:center; margin-bottom:20px; }
        .sv-wechat-icon { width:48px; height:48px; background:#07c160; border-radius:50%; display:inline-flex; justify-content:center; align-items:center; cursor:pointer; }
        .sv-wechat-icon:hover { filter:brightness(1.1); }
        .sv-wechat-icon svg { width:28px; height:28px; fill:white; }
        .sv-footer { text-align:center; color:#8899aa; font-size:14px; }
        .sv-footer a { color:#2dd4bf; text-decoration:underline; cursor:pointer; }
        .sv-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-close:hover { color:white; }
        .sv-row { display:flex; gap:10px; margin-bottom:16px; }
        .sv-row .sv-input { flex:1; margin-bottom:0; }
        .sv-code-btn { background:#334455; color:white; border:none; border-radius:8px; padding:14px 16px; font-size:13px; cursor:pointer; white-space:nowrap; }
        .sv-code-btn:hover:not(:disabled) { background:#445566; }
        .sv-code-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-input.sv-error { border-color:#ef4444; }
        .sv-error-msg { color:#ef4444; font-size:12px; margin:-12px 0 12px 0; }
        .sv-toast { position:fixed; top:20px; left:50%; transform:translateX(-50%); background:#1a2a3a; border:1px solid #334455; border-radius:8px; padding:12px 24px; color:white; font-size:14px; z-index:10003; animation:svToastIn 0.3s ease; }
        .sv-toast.error { border-color:#ef4444; color:#ef4444; }
        .sv-toast.success { border-color:#2dd4bf; color:#2dd4bf; }
        @keyframes svToastIn { from { opacity:0; transform:translateX(-50%) translateY(-20px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }
        .sv-view { display:none; }
        .sv-view.active { display:block; }
        .sv-pwd-wrap { position:relative; margin-bottom:16px; }
        .sv-pwd-wrap .sv-input { margin-bottom:0; padding-right:44px; }
        .sv-eye-btn { position:absolute; right:12px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; padding:4px; color:#2dd4bf; }
        .sv-eye-btn:hover { color:#22d3ee; }
        .sv-eye-btn svg { width:20px; height:20px; }
        .sv-eye-btn svg path, .sv-eye-btn svg line, .sv-eye-btn svg circle { stroke:#2dd4bf !important; }
        .sv-wechat-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.72); display:flex; justify-content:center; align-items:center; z-index:10004; }
        .sv-wechat-dialog { width:420px; background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:22px; position:relative; }
        .sv-wechat-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:8px; }
        .sv-wechat-subtitle { color:#8ba0b3; font-size:13px; margin-bottom:12px; }
        .sv-wechat-qrcode { width:220px; height:220px; margin:0 auto 12px auto; display:block; border-radius:8px; background:white; padding:8px; box-sizing:border-box; }
        .sv-wechat-actions { display:flex; gap:8px; margin-bottom:10px; }
        .sv-wechat-small-btn { flex:1; border:1px solid #334455; background:#1e3a4a; color:white; border-radius:6px; padding:8px 10px; cursor:pointer; font-size:12px; }
        .sv-wechat-small-btn:hover { border-color:#2dd4bf; }
        .sv-wechat-code-input { width:100%; background:transparent; border:1px solid #334455; border-radius:8px; padding:10px 12px; color:white; font-size:13px; box-sizing:border-box; margin-bottom:10px; }
        .sv-wechat-code-input:focus { outline:none; border-color:#2dd4bf; }
        .sv-wechat-login-btn { width:100%; border:none; border-radius:8px; padding:11px; color:white; background:linear-gradient(90deg,#2dd4bf,#22d3ee); font-weight:bold; cursor:pointer; }
        .sv-wechat-login-btn:hover { filter:brightness(1.1); }
        .sv-wechat-close { position:absolute; top:10px; right:12px; border:none; background:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-wechat-close:hover { color:white; }
        .sv-wechat-tip { color:#8ba0b3; font-size:12px; line-height:1.5; margin:0 0 8px 0; }
        .sv-wechat-status { color:#a7f3d0; font-size:12px; margin:6px 0 10px 0; min-height:18px; }
        .sv-wechat-frame-wrap { width:100%; height:360px; border:1px solid #334455; border-radius:8px; overflow:hidden; background:white; margin:0 auto 12px auto; }
        .sv-wechat-frame { width:100%; height:100%; border:none; }
    `;
    document.head.appendChild(style);

    const views = {};
    const switchView = (name) => Object.keys(views).forEach(k => views[k].classList.toggle('active', k === name));

    const eyeOpen = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
    const eyeClosed = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
    
    const createPwdInput = (id, placeholder) => {
        const input = $el("input.sv-input", { type: "password", placeholder, id });
        const btn = $el("button.sv-eye-btn", { type: "button", innerHTML: eyeClosed, onclick: () => {
            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            btn.innerHTML = isHidden ? eyeOpen : eyeClosed;
        }});
        return $el("div.sv-pwd-wrap", {}, [input, btn]);
    };

    const createWechat = () => $el("div.sv-wechat", {}, [$el("div.sv-wechat-icon", { innerHTML: wechatIcon, onclick: handleWechatLogin })]);

    views.login = $el("div.sv-view.active", {}, [
        $el("div.sv-title", { textContent: "欢迎回来!" }),
        $el("div.sv-subtitle", { textContent: "登录您的账户，继续使用 AI 服务" }),
        $el("input.sv-input", { type: "text", placeholder: "手机号/用户名", id: "sv-username" }),
        createPwdInput("sv-password", "密码"),
        $el("div.sv-forgot", {}, [$el("a", { href: "#", textContent: "忘记密码?", onclick: (e) => { e.preventDefault(); switchView('forgot'); } })]),
        $el("button.sv-btn", { textContent: "登录", onclick: handleLogin }),
        createWechat(),
        $el("div.sv-footer", {}, ["还没有账户? ", $el("a", { textContent: "立即注册", onclick: () => switchView('register') })])
    ]);

    const forgotPhoneInput = $el("input.sv-input", { type: "text", placeholder: "请输入注册手机号", id: "sv-forgot-phone", oninput: validateForgotForm });
    const forgotPhoneErr = $el("div.sv-error-msg", { id: "sv-forgot-phone-err" });
    const forgotPwdWrap = createPwdInput("sv-forgot-newpwd", "设置新密码（至少6位）");
    const forgotCpwdWrap = createPwdInput("sv-forgot-confirmpwd", "重复新密码");
    const forgotPwdErr = $el("div.sv-error-msg", { id: "sv-forgot-pwd-err" });
    forgotPwdWrap.querySelector('input').oninput = validateForgotForm;
    forgotCpwdWrap.querySelector('input').oninput = validateForgotForm;
    const forgotCodeBtn = $el("button.sv-code-btn", { id: "sv-forgot-code-btn", textContent: "获取验证码", disabled: true, onclick: () => handleGetCode('forgot') });

    views.forgot = $el("div.sv-view", {}, [
        $el("div.sv-title", { textContent: "忘记密码" }),
        $el("div.sv-subtitle", { textContent: "通过手机号验证重置您的密码" }),
        forgotPhoneInput,
        forgotPhoneErr,
        forgotPwdWrap,
        forgotCpwdWrap,
        forgotPwdErr,
        $el("div.sv-row", {}, [
            $el("input.sv-input", { type: "text", placeholder: "短信验证码", id: "sv-forgot-code" }),
            forgotCodeBtn
        ]),
        $el("button.sv-btn", { textContent: "修改并登录", onclick: handleResetPassword }),
        $el("div.sv-footer", {}, ["想起密码了？ ", $el("a", { textContent: "返回登录", onclick: () => switchView('login') })])
    ]);

    const regPhoneInput = $el("input.sv-input", { type: "text", placeholder: "手机号", id: "sv-reg-phone", oninput: validateRegForm });
    const regPhoneErr = $el("div.sv-error-msg", { id: "sv-reg-phone-err" });
    const regPwdWrap = createPwdInput("sv-reg-password", "密码");
    const regCpwdWrap = createPwdInput("sv-reg-confirmpwd", "确认密码");
    const regPwdErr = $el("div.sv-error-msg", { id: "sv-reg-pwd-err" });
    regPwdWrap.querySelector('input').oninput = validateRegForm;
    regCpwdWrap.querySelector('input').oninput = validateRegForm;
    const regCodeBtn = $el("button.sv-code-btn", { id: "sv-reg-code-btn", textContent: "发送验证码", disabled: true, onclick: () => handleGetCode('register') });

    views.register = $el("div.sv-view", {}, [
        $el("div.sv-title", { textContent: "欢迎加入!" }),
        $el("div.sv-subtitle", { textContent: "只需一点点时间，就能与我们继续一起创造精彩" }),
        regPhoneInput,
        regPhoneErr,
        regPwdWrap,
        regCpwdWrap,
        regPwdErr,
        $el("div.sv-row", {}, [
            $el("input.sv-input", { type: "text", placeholder: "短信验证码", id: "sv-reg-code" }),
            regCodeBtn
        ]),
        $el("button.sv-btn", { textContent: "注册并登录", onclick: handleRegister }),
        createWechat(),
        $el("div.sv-footer", {}, ["已有账户？ ", $el("a", { textContent: "立即登录", onclick: () => switchView('login') })])
    ]);

    loginDialog = $el("div.sv-overlay", {
        onclick: (e) => { if (e.target === loginDialog) { loginDialog.style.display = "none"; switchView('login'); } }
    }, [
        $el("div.sv-dialog", {}, [
            $el("button.sv-close", { textContent: "×", onclick: () => { loginDialog.style.display = "none"; switchView('login'); } }),
            views.login, views.forgot, views.register
        ])
    ]);

    document.body.appendChild(loginDialog);
}

function getVal(id) { return document.getElementById(id)?.value; }

function isValidMobile(phone) { return /^1\d{10}$/.test(phone); }

function showToast(msg, type = '') {
    const toast = document.createElement('div');
    toast.className = 'sv-toast' + (type ? ` ${type}` : '');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function validateForm(phoneId, pwdId, cpwdId, phoneErrId, pwdErrId, codeBtnId) {
    const phone = getVal(phoneId) || '';
    const pwd = getVal(pwdId) || '';
    const cpwd = getVal(cpwdId) || '';
    
    const phoneErr = document.getElementById(phoneErrId);
    const pwdErr = document.getElementById(pwdErrId);
    const phoneInput = document.getElementById(phoneId);
    const codeBtn = document.getElementById(codeBtnId);
    
    let valid = true;
    
    if (phone && !isValidMobile(phone)) {
        if (phoneErr) phoneErr.textContent = '请输入正确的11位手机号';
        phoneInput?.classList.add('sv-error');
        valid = false;
    } else {
        if (phoneErr) phoneErr.textContent = '';
        phoneInput?.classList.remove('sv-error');
        if (!phone) valid = false;
    }
    
    if (pwd && cpwd && pwd !== cpwd) {
        if (pwdErr) pwdErr.textContent = '两次密码不一致';
        valid = false;
    } else if (pwd && pwd.length < 6) {
        if (pwdErr) pwdErr.textContent = '密码至少6位';
        valid = false;
    } else {
        if (pwdErr) pwdErr.textContent = '';
        if (!pwd || !cpwd) valid = false;
    }
    
    if (codeBtn && !codeBtn.dataset.counting) {
        codeBtn.disabled = !valid;
    }
}

function validateRegForm() {
    validateForm('sv-reg-phone', 'sv-reg-password', 'sv-reg-confirmpwd', 'sv-reg-phone-err', 'sv-reg-pwd-err', 'sv-reg-code-btn');
}

function validateForgotForm() {
    validateForm('sv-forgot-phone', 'sv-forgot-newpwd', 'sv-forgot-confirmpwd', 'sv-forgot-phone-err', 'sv-forgot-pwd-err', 'sv-forgot-code-btn');
}

async function postJson(path, body) {
    console.log(`[SynVow] 请求: https://service.synvow.com/api/v1${path}`);
    console.log(`[SynVow] 请求参数:`, JSON.stringify(body, null, 2));
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    const data = await res.json();
    console.log(`[SynVow] 响应 ${path}:`, JSON.stringify(data, null, 2));
    return data;
}

function saveAuth(data) {
    // 兼容两种响应格式：
    // 格式1（登录）: { token: "...", user: {...} }
    // 格式2（注册）: { token: "...", id: ..., phone_number: ... }（用户信息直接在顶层）
    const token = data.token;
    const refreshToken = data.refresh_token;
    const user = data.user || data;  // 如果没有 user 字段，整个 data 就是用户信息
    
    if (token) {
        localStorage.setItem("sv_token", token);
    }
    if (refreshToken) {
        localStorage.setItem("sv_refresh_token", refreshToken);
    }
    localStorage.setItem("sv_user", JSON.stringify(user));
    if (token) {
        saveAuthToFile(token, refreshToken);
        // 通知菜单更新用户按钮状态
        const nickname = user?.nickname || user?.username || "已登录";
        window.dispatchEvent(new CustomEvent("synvow_login_success", { detail: { nickname } }));
    }
}

async function saveAuthToFile(token, refreshToken) {
    try {
        await fetch('/sv_api/auth/save-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, refresh_token: refreshToken || "" })
        });
    } catch (e) {
        console.error('[SynVow] saveAuthToFile failed:', e);
    }
}

async function clearAuthFile() {
    try {
        await fetch('/sv_api/auth/clear-token', { method: 'POST' });
    } catch (e) {
        console.error('[SynVow] clearAuthFile failed:', e);
    }
}

function setLoginViewActive() {
    const nodes = loginDialog?.querySelectorAll('.sv-view');
    if (!nodes || !nodes.length) return;
    nodes.forEach(v => v.classList.remove('active'));
    nodes[0].classList.add('active');
}

async function handleLogin() {
    const phone = getVal("sv-username");
    const password = getVal("sv-password");
    if (!phone || !password) { showToast("请输入手机号和密码", 'error'); return; }
    
    try {
        const data = await postJson("/auth/login", { phone_number: phone, password });
        console.log('[SynVow] 登录响应:', data);
        if (data.code === 200) {
            console.log('[SynVow] 登录成功, token:', data.data?.token);
            console.log('[SynVow] 用户信息:', data.data?.user);
            saveAuth(data.data);
            hideLoginDialog();
            await updateBalanceStatus();
        } else {
            showToast(data.message || "登录失败", 'error');
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", 'error');
    }
}

async function tryRefreshToken() {
    const token = localStorage.getItem("sv_token");
    const refreshToken = localStorage.getItem("sv_refresh_token");
    if (!token && !refreshToken) return false;

    try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token || "", refresh_token: refreshToken || "" })
        });
        const data = await res.json();
        if (data.code === 200 && data.data) {
            const newAccess = data.data.access_token;
            const newRefresh = data.data.refresh_token;
            if (newAccess) {
                localStorage.setItem("sv_token", newAccess);
                if (newRefresh) localStorage.setItem("sv_refresh_token", newRefresh);
                console.log("[SynVow] Token 自动刷新成功");
                return true;
            }
        }
    } catch (e) {
        console.error("[SynVow] Token 刷新失败:", e);
    }
    return false;
}

async function updateBalanceStatus() {
    const token = localStorage.getItem("sv_token");
    if (!token) return;
    
    const statusBtn = document.getElementById("synvow-status");
    try {
        let res = await fetch(`${API_BASE}/account/balance`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        let data = await res.json();

        // token 过期，尝试自动刷新
        if (data.code === 401) {
            const refreshed = await tryRefreshToken();
            if (refreshed) {
                const newToken = localStorage.getItem("sv_token");
                res = await fetch(`${API_BASE}/account/balance`, {
                    headers: { "Authorization": `Bearer ${newToken}` }
                });
                data = await res.json();
            }
        }

        if (statusBtn && data.code === 200) {
            statusBtn.textContent = `余额 ${parseFloat(data.data.balance || 0).toFixed(2)}`;
        } else if (statusBtn && data.code === 401) {
            statusBtn.textContent = "登录过期";
            localStorage.removeItem("sv_token");
            localStorage.removeItem("sv_refresh_token");
            localStorage.removeItem("sv_user");
        } else if (statusBtn) {
            statusBtn.textContent = "状态异常";
        }
    } catch (e) {
        if (statusBtn) statusBtn.textContent = "连接失败";
    }
}

export { updateBalanceStatus, clearAuthFile };

let codeCountdown = 0;
let codeTimer = null;

async function handleGetCode(type) {
    const isReg = type === 'register';
    const phone = getVal(isReg ? 'sv-reg-phone' : 'sv-forgot-phone');
    if (!phone) { showToast("请输入手机号", 'error'); return; }
    if (!isValidMobile(phone)) { showToast("请输入正确的手机号", 'error'); return; }
    if (codeCountdown > 0) return;
    
    const btn = document.getElementById(isReg ? 'sv-reg-code-btn' : 'sv-forgot-code-btn');
    
    try {
        const data = await postJson("/auth/send-code", { phone_number: phone });
        if (data.code === 200) {
            showToast("验证码已发送", 'success');
            codeCountdown = 60;
            btn.textContent = `${codeCountdown}s`;
            btn.disabled = true;
            btn.dataset.counting = 'true';
            codeTimer = setInterval(() => {
                if (--codeCountdown <= 0) {
                    clearInterval(codeTimer);
                    btn.textContent = isReg ? "发送验证码" : "获取验证码";
                    delete btn.dataset.counting;
                    isReg ? validateRegForm() : validateForgotForm();
                } else {
                    btn.textContent = `${codeCountdown}s`;
                }
            }, 1000);
        } else {
            showToast(data.message || "发送失败", 'error');
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", 'error');
    }
}

async function handleRegister() {
    const [phone, pwd, cpwd, code] = ['sv-reg-phone', 'sv-reg-password', 'sv-reg-confirmpwd', 'sv-reg-code'].map(getVal);
    if (!phone || !pwd || !cpwd || !code) { showToast("请填写完整信息", 'error'); return; }
    if (!isValidMobile(phone)) { showToast("请输入正确的手机号", 'error'); return; }
    if (pwd.length < 6) { showToast("密码至少6位", 'error'); return; }
    if (pwd !== cpwd) { showToast("两次密码不一致", 'error'); return; }
    
    try {
        const data = await postJson("/auth/register", { phone_number: phone, password: pwd, code: code });
        
        if (data.code === 200) {
            // 注册成功后，如果响应里有 token 直接用，否则自动登录获取 token
            if (data.data && data.data.token) {
                saveAuth(data.data);
            } else {
                // 注册接口没返回 token，自动调用登录接口
                const loginData = await postJson("/auth/login", { phone_number: phone, password: pwd });
                if (loginData.code === 200 && loginData.data && loginData.data.token) {
                    saveAuth(loginData.data);
                } else {
                    showToast("注册成功，请手动登录", 'success');
                    hideLoginDialog();
                    return;
                }
            }
            showToast("注册成功", 'success');
            hideLoginDialog();
            await updateBalanceStatus();
        } else {
            showToast(data.message || "注册失败", 'error');
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", 'error');
    }
}

async function handleResetPassword() {
    const [phone, code, pwd, cpwd] = ['sv-forgot-phone', 'sv-forgot-code', 'sv-forgot-newpwd', 'sv-forgot-confirmpwd'].map(getVal);
    if (!phone || !code || !pwd || !cpwd) { showToast("请填写完整信息", 'error'); return; }
    if (!isValidMobile(phone)) { showToast("请输入正确的手机号", 'error'); return; }
    if (pwd.length < 6) { showToast("密码至少6位", 'error'); return; }
    if (pwd !== cpwd) { showToast("两次密码不一致", 'error'); return; }
    
    try {
        const data = await postJson("/auth/reset-password", { phone_number: phone, code: code, new_password: pwd });
        
        if (data.code === 200) {
            showToast("密码重置成功，请使用新密码登录", 'success');
            setLoginViewActive();
        } else {
            showToast(data.message || "重置失败", 'error');
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", 'error');
    }
}

export function hideLoginDialog() { if (loginDialog) loginDialog.style.display = "none"; }

function extractWechatCode(input) {
    const raw = (input || "").trim();
    if (!raw) return "";
    if (/^[A-Za-z0-9_-]{8,}$/.test(raw)) return raw;
    try {
        const u = new URL(raw);
        return u.searchParams.get("code") || "";
    } catch (_) {
        const matched = raw.match(/[?&]code=([^&#]+)/i);
        return matched ? decodeURIComponent(matched[1]) : "";
    }
}

function buildQrImageUrl(url) {
    return `https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=${encodeURIComponent(url)}`;
}

function isWechatQrConnectUrl(url) {
    return typeof url === "string" && url.includes("open.weixin.qq.com/connect/qrconnect");
}

function hideWechatDialog() {
    if (wechatPollTimer) {
        clearInterval(wechatPollTimer);
        wechatPollTimer = null;
    }
    if (wechatMessageListener) {
        window.removeEventListener('message', wechatMessageListener);
        wechatMessageListener = null;
    }
    if (wechatDialog) wechatDialog.style.display = "none";
}

async function hydrateUserProfile(token) {
    try {
        const res = await fetch(`${API_BASE}/user/info`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data?.code === 200 && data?.data) {
            localStorage.setItem("sv_user", JSON.stringify(data.data));
            return;
        }
    } catch (_) {}
    localStorage.setItem("sv_user", JSON.stringify({}));
}

async function finishWechatLoginWithToken(token) {
    localStorage.setItem("sv_token", token);
    saveAuthToFile(token);
    await hydrateUserProfile(token);
    const user = JSON.parse(localStorage.getItem("sv_user") || "{}");
    hideWechatDialog();
    if (!user.phone_number) {
        showBindPhoneDialog();
    } else {
        hideLoginDialog();
        showToast("微信登录成功", "success");
        await updateBalanceStatus();
    }
}

let bindPhoneDialog = null;

export function showBindPhoneDialog() {
    if (bindPhoneDialog) { bindPhoneDialog.remove(); bindPhoneDialog = null; }

    let bindCountdown = 0;
    let bindTimer = null;

    const phoneInput = $el("input.sv-input", { type: "text", placeholder: "请输入手机号", id: "sv-bind-phone" });
    const codeInput = $el("input.sv-input", { type: "text", placeholder: "短信验证码", id: "sv-bind-code" });
    const codeBtn = $el("button.sv-code-btn", { id: "sv-bind-code-btn", textContent: "发送验证码",
        onclick: async () => {
            const phone = phoneInput.value.trim();
            if (!isValidMobile(phone)) { showToast("请输入正确的手机号", "error"); return; }
            if (bindCountdown > 0) return;
            try {
                const data = await postJson("/auth/send-code", { phone_number: phone });
                if (data.code === 200) {
                    showToast("验证码已发送", "success");
                    bindCountdown = 60;
                    codeBtn.disabled = true;
                    codeBtn.dataset.counting = "true";
                    codeBtn.textContent = `${bindCountdown}s`;
                    bindTimer = setInterval(() => {
                        if (--bindCountdown <= 0) {
                            clearInterval(bindTimer);
                            codeBtn.textContent = "发送验证码";
                            delete codeBtn.dataset.counting;
                            codeBtn.disabled = false;
                        } else {
                            codeBtn.textContent = `${bindCountdown}s`;
                        }
                    }, 1000);
                } else {
                    showToast(data.message || "发送失败", "error");
                }
            } catch (e) {
                showToast("网络错误，请稍后重试", "error");
            }
        }
    });

    const handleBind = async () => {
        const phone = phoneInput.value.trim();
        const code = codeInput.value.trim();
        if (!isValidMobile(phone)) { showToast("请输入正确的手机号", "error"); return; }
        if (!code) { showToast("请输入验证码", "error"); return; }
        const token = localStorage.getItem("sv_token");
        try {
            const res = await fetch(`${API_BASE}/user/bind-phone`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ phone_number: phone, code })
            });
            const data = await res.json();
            if (data.code === 200) {
                const user = JSON.parse(localStorage.getItem("sv_user") || "{}");
                user.phone_number = phone;
                localStorage.setItem("sv_user", JSON.stringify(user));
                if (bindTimer) clearInterval(bindTimer);
                bindPhoneDialog.remove();
                bindPhoneDialog = null;
                hideLoginDialog();
                showToast("手机号绑定成功", "success");
                await updateBalanceStatus();
            } else {
                showToast(data.message || "绑定失败", "error");
            }
        } catch (e) {
            showToast("网络错误，请稍后重试", "error");
        }
    };

    bindPhoneDialog = $el("div.sv-overlay", {
        style: "z-index:10005;"
    }, [
        $el("div.sv-dialog", {}, [
            $el("button.sv-close", { textContent: "×", onclick: () => { if (bindTimer) clearInterval(bindTimer); bindPhoneDialog.remove(); bindPhoneDialog = null; } }),
            $el("div.sv-title", { textContent: "绑定手机号" }),
            $el("div.sv-subtitle", { textContent: "微信账号尚未绑定手机号，请绑定后继续使用" }),
            phoneInput,
            $el("div.sv-row", {}, [codeInput, codeBtn]),
            $el("button.sv-btn", { textContent: "绑定并登录", onclick: handleBind })
        ])
    ]);

    document.body.appendChild(bindPhoneDialog);
}

async function handleWechatCodeLogin(loginInputId) {
    const raw = getVal(loginInputId) || "";
    const code = extractWechatCode(raw);
    if (!code) {
        showToast("请粘贴授权 code 或回调链接", "error");
        return;
    }

    try {
        const data = await postJson("/auth/wechat/login", { code });
        if (data.code === 200 && data.data?.token) {
            await finishWechatLoginWithToken(data.data.token);
        } else {
            showToast(data.message || "微信登录失败", "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
    }
}

function startWechatStatePolling(state, statusNode) {
    if (wechatPollTimer) {
        clearInterval(wechatPollTimer);
        wechatPollTimer = null;
    }

    let remaining = 120;
    statusNode.textContent = "等待扫码并授权...";

    wechatPollTimer = setInterval(async () => {
        remaining -= 3;
        if (remaining <= 0) {
            clearInterval(wechatPollTimer);
            wechatPollTimer = null;
            statusNode.textContent = "二维码已过期，请刷新重试。";
            return;
        }

        try {
            const data = await postJson("/auth/qrcode/token", { state });
            if (data?.code === 200 && data?.data?.token) {
                clearInterval(wechatPollTimer);
                wechatPollTimer = null;
                statusNode.textContent = "授权成功，正在登录...";
                await finishWechatLoginWithToken(data.data.token);
                return;
            } else {
                statusNode.textContent = `等待扫码授权... ${remaining}s`;
            }
        } catch (_) {
            // ignore transient polling errors
        }
    }, 3000);
}

function showWechatAuthDialog(loginUrl, state) {
    if (wechatDialog) {
        wechatDialog.remove();
        wechatDialog = null;
    }

    let currentState = state;
    const statusNode = $el("div.sv-wechat-status", { textContent: "" });

    // 从 login_url 解析参数，重新拼接 iframe 内嵌二维码地址
    function buildIframeSrc(url) {
        try {
            const u = new URL(url);
            const appid = u.searchParams.get("appid");
            const redirectUri = u.searchParams.get("redirect_uri");
            const st = u.searchParams.get("state");
            return `https://open.weixin.qq.com/connect/qrconnect?appid=${appid}&scope=snsapi_login&redirect_uri=${encodeURIComponent(redirectUri)}&state=${st}&login_type=jssdk&self_redirect=true&style=black`;
        } catch (_) {
            return url;
        }
    }

    const qrFrame = $el("iframe.sv-wechat-qrframe", {
        src: buildIframeSrc(loginUrl),
        style: {
            width: "300px",
            height: "400px",
            border: "none",
            borderRadius: "8px",
            background: "#fff"
        }
    });

    const refreshBtn = $el("button.sv-wechat-small-btn", {
        textContent: "刷新二维码",
        onclick: async () => {
            refreshBtn.disabled = true;
            refreshBtn.textContent = "刷新中...";
            try {
                const newState = `canvas_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
                const data = await postJson("/auth/wechat/login-url", { state: newState });
                const newUrl = data?.data?.login_url || data?.data?.url || data?.data?.loginUrl;
                if (data.code === 200 && newUrl) {
                    currentState = data?.data?.state || newState;
                    qrFrame.src = buildIframeSrc(newUrl);
                    if (wechatPollTimer) { clearInterval(wechatPollTimer); wechatPollTimer = null; }
                    startWechatStatePolling(currentState, statusNode);
                } else {
                    showToast(data.message || "刷新失败", "error");
                }
            } catch (e) {
                showToast("网络错误", "error");
            }
            refreshBtn.disabled = false;
            refreshBtn.textContent = "刷新二维码";
        }
    });

    wechatDialog = $el("div.sv-wechat-overlay", {
        onclick: (e) => { if (e.target === wechatDialog) hideWechatDialog(); }
    }, [
        $el("div.sv-wechat-dialog", {}, [
            $el("button.sv-wechat-close", { textContent: "×", onclick: hideWechatDialog }),
            $el("div.sv-wechat-title", { textContent: "微信扫码登录" }),
            $el("div.sv-wechat-subtitle", { textContent: "使用微信扫描下方二维码，在手机上点击「允许」完成登录" }),
            qrFrame,
            $el("div.sv-wechat-actions", {}, [refreshBtn]),
            statusNode
        ])
    ]);

    document.body.appendChild(wechatDialog);

    // 监听 callback.html 通过 postMessage 发回的 token
    if (wechatMessageListener) window.removeEventListener('message', wechatMessageListener);
    wechatMessageListener = (e) => {
        if (e.data?.type === 'sv_wechat_token' && e.data?.token) {
            window.removeEventListener('message', wechatMessageListener);
            wechatMessageListener = null;
            if (wechatPollTimer) { clearInterval(wechatPollTimer); wechatPollTimer = null; }
            statusNode.textContent = "授权成功，正在登录...";
            finishWechatLoginWithToken(e.data.token);
        }
    };
    window.addEventListener('message', wechatMessageListener);

    if (currentState) {
        startWechatStatePolling(currentState, statusNode);
    } else {
        statusNode.textContent = "未返回 state，请刷新重试。";
    }
}

async function handleWechatLogin() {
    try {
        const state = `canvas_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
        const data = await postJson("/auth/wechat/login-url", { state });
        const loginUrl = data?.data?.login_url || data?.data?.url || data?.data?.loginUrl;
        if (data.code === 200 && loginUrl) {
            showWechatAuthDialog(loginUrl, data?.data?.state || state);
        } else {
            const msg = (data.message && !data.message.includes("<html")) ? data.message : "服务暂时不可用，请稍后重试";
            showToast(msg, "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
    }
}
