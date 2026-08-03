/**
 * SynVow 登录对话框
 */
import { $el, API_BASE, postJson } from "./dom.js";

let loginDialog = null;
let wechatDialog = null;
let wechatPollTimer = null;
let wechatMessageListener = null;
let loginKind = "phone";
let registerKind = "phone";
const wechatIcon = `<svg viewBox="0 0 1024 1024"><path d="M690.1 377.4c5.9 0 11.8.2 17.6.5-24.4-128.7-158.3-227.1-319.9-227.1C209 150.8 64 271.4 64 420.2c0 81.1 43.6 154.2 111.9 203.6 5.5 3.9 9.1 10.3 9.1 17.6 0 2.4-.5 4.6-1.1 6.9-5.5 20.3-14.2 52.8-14.6 54.3-.7 2.6-1.7 5.2-1.7 7.9 0 5.9 4.8 10.8 10.8 10.8 2.3 0 4.2-.9 6.2-2l70.9-40.9c5.3-3.1 11-5 17.2-5 3.2 0 6.4.5 9.5 1.4 33.1 9.5 68.8 14.8 105.7 14.8 6 0 11.9-.1 17.8-.4-7.1-21-10.9-43.1-10.9-66 0-135.8 132.2-245.8 295.3-245.8zm-194.3-86.5c23.8 0 43.2 19.3 43.2 43.1s-19.3 43.1-43.2 43.1c-23.8 0-43.2-19.3-43.2-43.1s19.4-43.1 43.2-43.1zm-215.9 86.2c-23.8 0-43.2-19.3-43.2-43.1s19.3-43.1 43.2-43.1 43.2 19.3 43.2 43.1-19.4 43.1-43.2 43.1zm586.8 415.6c56.9-41.2 93.2-102 93.2-169.7 0-124-108.1-224.8-241.4-224.8-133.4 0-241.4 100.8-241.4 224.8S585 847.1 718.3 847.1c30.8 0 60.6-4.4 88.1-12.3 2.6-.8 5.2-1.2 7.9-1.2 5.2 0 9.9 1.6 14.3 4.1l59.1 34c1.7 1 3.3 1.7 5.2 1.7a9 9 0 0 0 6.4-2.6 9 9 0 0 0 2.6-6.4c0-2.2-.9-4.4-1.4-6.6-.3-1.2-7.6-28.3-12.2-45.3-.5-1.9-.9-3.8-.9-5.7.1-5.9 3.1-11.2 7.6-14.5zM600.2 587.2c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9c0 19.8-16.2 35.9-36 35.9zm179.9 0c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9a36.08 36.08 0 0 1-36 35.9z" fill="white"/></svg>`;

export function showLoginDialog() {
    if (loginDialog) {
        if (!loginDialog.querySelector(".sv-mode-tabs")) {
            loginDialog.remove();
            loginDialog = null;
            loginKind = "phone";
            registerKind = "phone";
        } else {
            loginDialog.style.display = "flex";
            return;
        }
    }

    if (!document.getElementById("sv-login-style")) {
        const style = document.createElement('style');
        style.id = "sv-login-style";
        style.textContent = `
        .sv-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10000; }
        .sv-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:40px; width:400px; position:relative; }
        .sv-title { color:#2dd4bf; font-size:28px; font-weight:bold; margin-bottom:10px; }
        .sv-subtitle { color:#8899aa; font-size:14px; margin-bottom:14px; }
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
        .sv-wechat-actions { display:flex; gap:8px; margin-bottom:10px; }
        .sv-wechat-small-btn { flex:1; border:1px solid #334455; background:#1e3a4a; color:white; border-radius:6px; padding:8px 10px; cursor:pointer; font-size:12px; }
        .sv-wechat-small-btn:hover { border-color:#2dd4bf; }
        .sv-wechat-close { position:absolute; top:10px; right:12px; border:none; background:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-wechat-close:hover { color:white; }
        .sv-wechat-status { color:#a7f3d0; font-size:12px; margin:6px 0 10px 0; min-height:18px; }
        .sv-mode-tabs { display:flex; gap:20px; margin-bottom:14px; }
        .sv-mode-tab { border:none; padding:0 0 8px; background:none; font-size:14px; color:#8899aa; cursor:pointer; border-bottom:2px solid transparent; }
        .sv-mode-tab:hover { color:#dbe7f0; }
        .sv-mode-tab.active { color:#2dd4bf; border-bottom-color:#2dd4bf; }
    `;
        document.head.appendChild(style);
    }

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

    const loginAccountInput = $el("input.sv-input", { type: "text", placeholder: "手机号", id: "sv-username" });
    const loginPhoneTab = $el("button.sv-mode-tab.active", {
        type: "button", textContent: "手机登录",
        onclick: () => setLoginKind("phone", loginPhoneTab, loginEmailTab, loginAccountInput),
    });
    const loginEmailTab = $el("button.sv-mode-tab", {
        type: "button", textContent: "邮箱登录",
        onclick: () => setLoginKind("email", loginPhoneTab, loginEmailTab, loginAccountInput),
    });

    views.login = $el("div.sv-view.active", {}, [
        $el("div.sv-title", { textContent: "欢迎回来!" }),
        $el("div.sv-subtitle", { textContent: "登录您的账户，继续使用 AI 服务" }),
        $el("div.sv-mode-tabs", {}, [loginPhoneTab, loginEmailTab]),
        loginAccountInput,
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

    const regAccountInput = $el("input.sv-input", { type: "text", placeholder: "手机号", id: "sv-reg-account", oninput: validateRegForm });
    const regAccountErr = $el("div.sv-error-msg", { id: "sv-reg-account-err" });
    const regPwdWrap = createPwdInput("sv-reg-password", "密码");
    const regCpwdWrap = createPwdInput("sv-reg-confirmpwd", "确认密码");
    const regPwdErr = $el("div.sv-error-msg", { id: "sv-reg-pwd-err" });
    regPwdWrap.querySelector('input').oninput = validateRegForm;
    regCpwdWrap.querySelector('input').oninput = validateRegForm;
    const regCodeInput = $el("input.sv-input", { type: "text", placeholder: "短信验证码", id: "sv-reg-code" });
    const regCodeBtn = $el("button.sv-code-btn", { id: "sv-reg-code-btn", textContent: "发送验证码", disabled: true, onclick: () => handleGetCode('register') });
    const regPhoneTab = $el("button.sv-mode-tab.active", {
        type: "button", textContent: "手机注册",
        onclick: () => setRegisterKind("phone", regPhoneTab, regEmailTab, regAccountInput, regCodeInput),
    });
    const regEmailTab = $el("button.sv-mode-tab", {
        type: "button", textContent: "邮箱注册",
        onclick: () => setRegisterKind("email", regPhoneTab, regEmailTab, regAccountInput, regCodeInput),
    });

    views.register = $el("div.sv-view", {}, [
        $el("div.sv-title", { textContent: "欢迎加入!" }),
        $el("div.sv-subtitle", { textContent: "只需一点点时间，就能与我们继续一起创造精彩" }),
        $el("div.sv-mode-tabs", {}, [regPhoneTab, regEmailTab]),
        regAccountInput,
        regAccountErr,
        regPwdWrap,
        regCpwdWrap,
        regPwdErr,
        $el("div.sv-row", {}, [regCodeInput, regCodeBtn]),
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
function isValidEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || "").trim()); }

function authAccountBody(account, kind) {
    return kind === "email" ? { email: account } : { phone_number: account };
}

function setLoginKind(kind, phoneTab, emailTab, accountInput) {
    loginKind = kind;
    phoneTab.classList.toggle("active", kind === "phone");
    emailTab.classList.toggle("active", kind === "email");
    accountInput.placeholder = kind === "email" ? "邮箱号" : "手机号";
    accountInput.value = "";
}

function setRegisterKind(kind, phoneTab, emailTab, accountInput, codeInput) {
    registerKind = kind;
    phoneTab.classList.toggle("active", kind === "phone");
    emailTab.classList.toggle("active", kind === "email");
    accountInput.placeholder = kind === "email" ? "邮箱号" : "手机号";
    accountInput.value = "";
    codeInput.placeholder = kind === "email" ? "邮箱验证码" : "短信验证码";
    codeInput.value = "";
    validateRegForm();
}

function showToast(msg, type = '') {
    const toast = document.createElement('div');
    toast.className = 'sv-toast' + (type ? ` ${type}` : '');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function validateForm(accountId, pwdId, cpwdId, accountErrId, pwdErrId, codeBtnId, kind) {
    const account = getVal(accountId) || '';
    const pwd = getVal(pwdId) || '';
    const cpwd = getVal(cpwdId) || '';
    const accountErr = document.getElementById(accountErrId);
    const pwdErr = document.getElementById(pwdErrId);
    const accountInput = document.getElementById(accountId);
    const codeBtn = document.getElementById(codeBtnId);
    const isEmail = kind === "email";
    let valid = true;

    if (account && !(isEmail ? isValidEmail(account) : isValidMobile(account))) {
        if (accountErr) accountErr.textContent = isEmail ? "请输入正确的邮箱" : "请输入正确的11位手机号";
        accountInput?.classList.add("sv-error");
        valid = false;
    } else {
        if (accountErr) accountErr.textContent = "";
        accountInput?.classList.remove("sv-error");
        if (!account) valid = false;
    }

    if (pwd && cpwd && pwd !== cpwd) {
        if (pwdErr) pwdErr.textContent = "两次密码不一致";
        valid = false;
    } else if (pwd && pwd.length < 6) {
        if (pwdErr) pwdErr.textContent = "密码至少6位";
        valid = false;
    } else {
        if (pwdErr) pwdErr.textContent = "";
        if (!pwd || !cpwd) valid = false;
    }

    if (codeBtn && !codeBtn.dataset.counting) {
        codeBtn.disabled = !valid;
    }
}

function validateRegForm() {
    validateForm(
        "sv-reg-account", "sv-reg-password", "sv-reg-confirmpwd",
        "sv-reg-account-err", "sv-reg-pwd-err", "sv-reg-code-btn",
        registerKind,
    );
}

function validateForgotForm() {
    validateForm(
        "sv-forgot-phone", "sv-forgot-newpwd", "sv-forgot-confirmpwd",
        "sv-forgot-phone-err", "sv-forgot-pwd-err", "sv-forgot-code-btn",
        "phone",
    );
}

function saveAuth(data) {
    const token = data.token || data.access_token;
    const refreshToken = data.refresh_token || data.refreshToken;
    const user = data.user || data.user_info || data.profile || data;
    if (token) localStorage.setItem("sv_token", token);
    if (refreshToken) localStorage.setItem("sv_refresh_token", refreshToken);
    localStorage.setItem("sv_user", JSON.stringify(user));
    if (token) {
        saveAuthToFile(token, refreshToken);
        window.synvowRefreshAccount?.();
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

async function handleLogin() {
    const account = (getVal("sv-username") || "").trim();
    const password = getVal("sv-password");
    const isEmail = loginKind === "email";
    if (!account || !password) {
        showToast(isEmail ? "请输入邮箱和密码" : "请输入手机号和密码", "error");
        return;
    }
    if (isEmail ? !isValidEmail(account) : !isValidMobile(account)) {
        showToast(isEmail ? "请输入正确的邮箱" : "请输入正确的手机号", "error");
        return;
    }
    try {
        const data = await postJson("/auth/login", {
            ...authAccountBody(account, loginKind),
            password,
            login_source: "comfyui",
        });
        if (data.code === 200) {
            saveAuth(data.data);
            hideLoginDialog();
        } else {
            showToast(data.message || "登录失败", "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
    }
}

export { clearAuthFile };

let codeCountdown = 0;
let codeTimer = null;

async function handleGetCode(type) {
    const isReg = type === "register";
    const kind = isReg ? registerKind : "phone";
    const account = (getVal(isReg ? "sv-reg-account" : "sv-forgot-phone") || "").trim();
    const isEmail = kind === "email";
    if (!account) {
        showToast(isEmail ? "请输入邮箱" : "请输入手机号", "error");
        return;
    }
    if (isEmail ? !isValidEmail(account) : !isValidMobile(account)) {
        showToast(isEmail ? "请输入正确的邮箱" : "请输入正确的手机号", "error");
        return;
    }
    if (codeCountdown > 0) return;

    const btn = document.getElementById(isReg ? "sv-reg-code-btn" : "sv-forgot-code-btn");
    const path = isEmail ? "/auth/send-email-code" : "/auth/send-code";

    try {
        const data = await postJson(path, authAccountBody(account, kind));
        if (data.code === 200) {
            showToast("验证码已发送", "success");
            codeCountdown = 60;
            btn.textContent = `${codeCountdown}s`;
            btn.disabled = true;
            btn.dataset.counting = "true";
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
            showToast(data.message || "发送失败", "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
    }
}

async function handleRegister() {
    const account = (getVal("sv-reg-account") || "").trim();
    const [pwd, cpwd, code] = ["sv-reg-password", "sv-reg-confirmpwd", "sv-reg-code"].map(getVal);
    const isEmail = registerKind === "email";
    if (!account || !pwd || !cpwd || !code) { showToast("请填写完整信息", "error"); return; }
    if (isEmail ? !isValidEmail(account) : !isValidMobile(account)) {
        showToast(isEmail ? "请输入正确的邮箱" : "请输入正确的手机号", "error");
        return;
    }
    if (pwd.length < 6) { showToast("密码至少6位", "error"); return; }
    if (pwd !== cpwd) { showToast("两次密码不一致", "error"); return; }

    try {
        const data = await postJson("/auth/register", {
            ...authAccountBody(account, registerKind),
            password: pwd,
            code,
        });

        if (data.code === 200) {
            if (data.data && data.data.token) {
                saveAuth(data.data);
            } else {
                const loginData = await postJson("/auth/login", {
                    ...authAccountBody(account, registerKind),
                    password: pwd,
                    login_source: "comfyui",
                });
                if (loginData.code === 200 && loginData.data && loginData.data.token) {
                    saveAuth(loginData.data);
                } else {
                    showToast("注册成功，请手动登录", "success");
                    hideLoginDialog();
                    return;
                }
            }
            showToast("注册成功", "success");
            hideLoginDialog();
        } else {
            showToast(data.message || "注册失败", "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
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
            const nodes = loginDialog?.querySelectorAll('.sv-view');
            if (nodes?.length) { nodes.forEach(v => v.classList.remove('active')); nodes[0].classList.add('active'); }
        } else {
            showToast(data.message || "重置失败", 'error');
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", 'error');
    }
}

export function hideLoginDialog() { if (loginDialog) loginDialog.style.display = "none"; }

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

async function finishWechatLoginWithToken(token, refreshToken = "") {
    localStorage.setItem("sv_token", token);
    if (refreshToken) localStorage.setItem("sv_refresh_token", refreshToken);
    saveAuthToFile(token, refreshToken);
    await hydrateUserProfile(token);
    const user = JSON.parse(localStorage.getItem("sv_user") || "{}");
    hideWechatDialog();
    if (!user.phone_number) {
        showBindPhoneDialog();
    } else {
        hideLoginDialog();
        showToast("微信登录成功", "success");
        window.synvowRefreshAccount?.();
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
                window.synvowRefreshAccount?.();
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
            const token = data?.data?.token || data?.data?.access_token;
            if (data?.code === 200 && token) {
                clearInterval(wechatPollTimer);
                wechatPollTimer = null;
                statusNode.textContent = "授权成功，正在登录...";
                await finishWechatLoginWithToken(token, data.data?.refresh_token || data.data?.refreshToken || "");
                return;
            } else {
                statusNode.textContent = `等待扫码授权... ${remaining}s`;
            }
        } catch (_) {
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

    if (wechatMessageListener) window.removeEventListener('message', wechatMessageListener);
    wechatMessageListener = (e) => {
        const token = e.data?.token || e.data?.access_token;
        if (e.data?.type === 'sv_wechat_token' && token) {
            window.removeEventListener('message', wechatMessageListener);
            wechatMessageListener = null;
            if (wechatPollTimer) { clearInterval(wechatPollTimer); wechatPollTimer = null; }
            statusNode.textContent = "授权成功，正在登录...";
            finishWechatLoginWithToken(token, e.data?.refresh_token || e.data?.refreshToken || "");
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
