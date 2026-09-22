/**
 * SynVow 个人中心对话框
 */
import { $el, getToken, injectStyle, API_BASE } from "./dom.js";
import { showLoginDialog, clearAuthFile } from "./synvow_login.js";

const SUPPORT_WECHAT_ID = "manhualvren";
const UPGRADE_QR_SRC = "/extensions/Comfyui_SynVow_api/wx.png";
const ROLE_LABELS = {
    user: "普通用户",
    business: "企业用户",
    moderator: "管理员",
    admin: "超级管理员",
    super_admin: "超级管理员(系统)",
};

let profileDialog = null;

export function showProfileDialog() {
    if (profileDialog) {
        profileDialog.remove();
        profileDialog = null;
    }

    injectStyle("sv-profile-style", `
        .sv-profile-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-profile-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:760px; max-width:94vw; position:relative; }
        .sv-profile-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-profile-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-profile-close:hover { color:white; }
        .sv-profile-loading { text-align:center; color:#667788; padding:40px; }
        .sv-profile-row { display:flex; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:16px; }
        .sv-profile-label { color:#8899aa; font-size:14px; }
        .sv-profile-value { color:white; font-size:14px; font-weight:bold; }
        .sv-profile-link { color:#2dd4bf; font-size:13px; cursor:pointer; margin-left:8px; }
        .sv-profile-link:hover { text-decoration:underline; }
        .sv-profile-muted { color:#8899aa; font-weight:normal; }
        .sv-profile-copy { width:14px; height:14px; cursor:pointer; color:#8899aa; flex-shrink:0; }
        .sv-profile-copy:hover { color:#2dd4bf; }
        .sv-profile-ml-auto { margin-left:auto; }
        .sv-profile-ml { margin-left:24px; }
        .sv-currency-unit { font-size:12px; font-weight:normal; margin-left:4px; color:#8899aa; }
        .sv-profile-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; padding:16px; background:#1e3a4a; border-radius:8px; }
        .sv-profile-stat { text-align:center; }
        .sv-profile-stat-label { color:#8899aa; font-size:12px; margin-bottom:4px; }
        .sv-profile-stat-value { color:#2dd4bf; font-size:18px; font-weight:bold; }
        .sv-profile-bind-status { padding:2px 8px; border-radius:4px; font-size:12px; }
        .sv-profile-bind-yes { background:#22c55e20; color:#22c55e; }
        .sv-profile-bind-no { background:#ef444420; color:#ef4444; }
        .sv-profile-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-profile-btn:hover { border-color:#2dd4bf; }
        .sv-profile-btn-danger { border-color:#ef4444; color:#ef4444; }
        .sv-profile-btn-danger:hover { background:#ef444420; }
        .sv-wechat-qr-modal { position:fixed; inset:0; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:10003; }
        .sv-wechat-qr-box { background:#1a2a3a; border-radius:12px; padding:24px; text-align:center; width:280px; }
        .sv-wechat-qr-title { color:#2dd4bf; font-size:16px; font-weight:bold; margin-bottom:16px; }
        .sv-wechat-qr-tip { color:#8899aa; font-size:13px; margin-bottom:16px; }
        .sv-wechat-qr-close { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 16px; color:white; font-size:13px; cursor:pointer; }
        .sv-role-tag { display:inline-flex; align-items:center; padding:3px 12px; border-radius:999px; font-size:13px; font-weight:500; }
        .sv-role-user { background:#f1f5f9; color:#64748b; }
        .sv-role-business { background:#fff6e8; color:#e8a317; }
        .sv-role-moderator { background:#eef4ff; color:#3b82f6; }
        .sv-role-admin { background:#fff1e0; color:#f59e0b; }
        .sv-role-super_admin { background:#f3e8ff; color:#9333ea; }
        .sv-upgrade-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.72); display:flex; justify-content:center; align-items:center; z-index:10004; }
        .sv-upgrade-card { position:relative; width:360px; padding:28px 28px 24px; border-radius:20px; background:#fff; text-align:center; }
        .sv-upgrade-head { display:flex; align-items:flex-start; gap:12px; text-align:left; margin-bottom:20px; padding-right:16px; }
        .sv-upgrade-icon { width:40px; height:40px; flex-shrink:0; }
        .sv-upgrade-title { font-size:18px; font-weight:700; color:#0f172a; line-height:1.3; }
        .sv-upgrade-sub { margin-top:6px; font-size:13px; line-height:1.55; color:#64748b; }
        .sv-upgrade-qr-wrap { width:188px; height:188px; margin:0 auto; padding:10px; border-radius:16px; background:linear-gradient(180deg,#f0fdf4,#fff); border:1px solid #d1fae5; box-sizing:border-box; }
        .sv-upgrade-qr { width:100%; height:100%; object-fit:contain; display:block; border-radius:8px; background:#fff; }
        .sv-upgrade-scan { margin-top:14px; font-size:14px; font-weight:600; color:#07c160; }
        .sv-upgrade-id { display:inline-flex; align-items:center; gap:6px; margin-top:8px; padding:6px 12px; border-radius:999px; background:#f0fdf4; color:#166534; font-size:13px; font-weight:600; }
        .sv-upgrade-id svg { width:16px; height:16px; }
    `);

    const contentDiv = $el("div", {}, [
        $el("div.sv-profile-loading", { textContent: "加载中..." })
    ]);

    profileDialog = $el("div.sv-profile-overlay", {
        onclick: (e) => { if (e.target === profileDialog) hideProfileDialog(); }
    }, [
        $el("div.sv-profile-dialog", {}, [
            $el("button.sv-profile-close", { textContent: "×", onclick: hideProfileDialog }),
            $el("div.sv-profile-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> 个人中心` }),
            contentDiv
        ])
    ]);

    document.body.appendChild(profileDialog);

    // 加载数据
    loadProfile();

    async function loadProfile() {
        const token = getToken();
        if (!token) {
            profileDialog.remove();
            profileDialog = null;
            showLoginDialog();
            return;
        }

        let user = JSON.parse(localStorage.getItem("sv_user") || "{}");
        const headers = { "Authorization": `Bearer ${token}` };

        try {
            const [summaryRes, userRes] = await Promise.all([
                fetch(`${API_BASE}/account/summary`, { headers }).then(r => r.json()).catch(() => null),
                fetch(`${API_BASE}/user/info`, { headers }).then(r => r.json()).catch(() => null),
            ]);
            if (userRes?.code === 200 && userRes.data) {
                user = { ...user, ...userRes.data };
                localStorage.setItem("sv_user", JSON.stringify(user));
            }
            if (summaryRes?.code === 200 && summaryRes.data) {
                const summary = summaryRes.data;
                const userId = user.id || user.user_id || "";
                const displayName = user.nickname || user.phone_number || user.email || "用户";
                const roleKey = ROLE_LABELS[user.role] ? user.role : "user";
                const roleLabel = ROLE_LABELS[roleKey];
                const wechatBound = !!(user.wechat_openid || user.openid);
                const fmt = (v) => parseFloat(v ?? 0).toFixed(2);
                const copySvg = `<svg class="sv-profile-copy" id="sv-copy-id-btn" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;

                contentDiv.innerHTML = `
                    <div class="sv-profile-row">
                        <span class="sv-profile-label">账户昵称：</span>
                        <span class="sv-profile-value">${escapeHtml(displayName)}</span>
                        <span class="sv-profile-link" id="sv-edit-nickname-btn">修改昵称</span>
                        <span class="sv-profile-label sv-profile-ml">角色：</span>
                        <span class="sv-role-tag sv-role-${roleKey}">${escapeHtml(roleLabel)}</span>
                        ${roleKey === "user" ? `<span class="sv-profile-link" id="sv-upgrade-btn">升级了解</span>` : ""}
                        <span class="sv-profile-link sv-profile-btn-danger sv-profile-ml-auto" id="sv-logout-btn">退出登录</span>
                    </div>
                    <div class="sv-profile-row">
                        <span class="sv-profile-label">用户ID：</span>
                        <span class="sv-profile-value sv-profile-muted">${userId || "-"}</span>
                        ${userId ? copySvg : ""}
                        <span class="sv-profile-label sv-profile-ml">密码管理</span>
                        <span class="sv-profile-link" id="sv-set-pwd-btn">设置密码</span>
                        <span class="sv-profile-link" id="sv-change-pwd-btn">修改密码</span>
                    </div>
                    <div class="sv-profile-stats" style="grid-template-columns:repeat(2,1fr);">
                        <div class="sv-profile-stat">
                            <div class="sv-profile-stat-label">当前余额</div>
                            <div class="sv-profile-stat-value">${fmt(summary.current_balance ?? summary.balance)}<span class="sv-currency-unit">星币</span></div>
                        </div>
                        <div class="sv-profile-stat">
                            <div class="sv-profile-stat-label">总充值量</div>
                            <div class="sv-profile-stat-value">${fmt(summary.total_recharge)}<span class="sv-currency-unit">星币</span></div>
                        </div>
                    </div>
                    <div class="sv-profile-row" style="gap:20px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="sv-profile-label">手机号：</span>
                            <span class="sv-profile-value">${escapeHtml(maskPhone(user.phone_number))}</span>
                            ${user.phone_number
                                ? `<span class="sv-profile-bind-status sv-profile-bind-yes">已绑定</span>`
                                : `<span class="sv-profile-bind-status sv-profile-bind-no">未绑定</span><span class="sv-profile-link" id="sv-bind-phone-btn">绑定</span>`
                            }
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="sv-profile-label">微信：</span>
                            ${wechatBound
                                ? `<span class="sv-profile-bind-status sv-profile-bind-yes">已绑定</span>`
                                : `<span class="sv-profile-bind-status sv-profile-bind-no">未绑定</span><span class="sv-profile-link" id="sv-bind-wechat-btn">绑定</span>`
                            }
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="sv-profile-label">邮箱：</span>
                            <span class="sv-profile-value">${escapeHtml(maskEmail(user.email))}</span>
                            ${user.email
                                ? `<span class="sv-profile-bind-status sv-profile-bind-yes">已绑定</span>`
                                : `<span class="sv-profile-bind-status sv-profile-bind-no">未绑定</span><span class="sv-profile-link" id="sv-bind-email-btn">绑定</span>`
                            }
                        </div>
                    </div>
                `;

                document.getElementById('sv-edit-nickname-btn').onclick = () => showEditNicknameDialog(user.nickname || '');
                document.getElementById('sv-change-pwd-btn').onclick = () => {
                    if (!user.phone_number) { alert('请先绑定手机号码再修改密码'); return; }
                    showChangePasswordDialog();
                };
                document.getElementById('sv-set-pwd-btn').onclick = () => {
                    if (!user.phone_number) { alert('请先绑定手机号码再重置'); return; }
                    showSetPasswordDialog(user.phone_number);
                };
                const copyBtn = document.getElementById('sv-copy-id-btn');
                if (copyBtn) copyBtn.onclick = () => copyText(String(userId), 'ID已复制');
                const bindBtn = document.getElementById('sv-bind-phone-btn');
                if (bindBtn) bindBtn.onclick = () => showBindAccountDialog('phone');
                const bindEmailBtn = document.getElementById('sv-bind-email-btn');
                if (bindEmailBtn) bindEmailBtn.onclick = () => showBindAccountDialog('email');
                const bindWechatBtn = document.getElementById('sv-bind-wechat-btn');
                if (bindWechatBtn) bindWechatBtn.onclick = () => startWechatBind(token, user);
                const upgradeBtn = document.getElementById('sv-upgrade-btn');
                if (upgradeBtn) upgradeBtn.onclick = showUpgradeDialog;
                const logoutBtn = document.getElementById('sv-logout-btn');
                if (logoutBtn) logoutBtn.onclick = () => {
                    if (confirm('确定要退出登录吗？')) {
                        localStorage.removeItem('sv_token');
                        localStorage.removeItem('sv_refresh_token');
                        localStorage.removeItem('sv_user');
                        clearAuthFile();
                        hideProfileDialog();
                        window.synvowRefreshAccount?.();
                    }
                };
            } else {
                contentDiv.innerHTML = `<div class="sv-profile-loading">${summaryRes?.message || '获取信息失败'}</div>`;
            }
        } catch (e) {
            contentDiv.innerHTML = '<div class="sv-profile-loading">网络错误，请稍后重试</div>';
        }
    }

}

export function hideProfileDialog() {
    if (profileDialog) profileDialog.style.display = "none";
}

function wechatIconSvg() {
    return `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="24" fill="#07C160"/><path d="M19.5 14C14.25 14 10 17.58 10 22C10 24.17 11.08 26.13 12.83 27.55L12 31L15.83 29.17C17 29.5 18.25 29.67 19.5 29.67C19.67 29.67 19.83 29.67 20 29.63C19.67 28.79 19.5 27.92 19.5 27C19.5 22.58 23.58 19 28.5 19C28.83 19 29.17 19.04 29.5 19.08C28.5 16.08 24.33 14 19.5 14Z" fill="white"/><ellipse cx="15.5" cy="20.5" rx="1.5" ry="1.5" fill="#07C160"/><ellipse cx="23.5" cy="20.5" rx="1.5" ry="1.5" fill="#07C160"/><path d="M28.5 21C24.36 21 21 23.69 21 27C21 30.31 24.36 33 28.5 33C29.5 33 30.42 32.83 31.25 32.54L34.5 34L33.83 31.25C35.17 30.08 36 28.58 36 27C36 23.69 32.64 21 28.5 21Z" fill="white"/><ellipse cx="26" cy="26.5" rx="1.25" ry="1.25" fill="#07C160"/><ellipse cx="31" cy="26.5" rx="1.25" ry="1.25" fill="#07C160"/></svg>`;
}

function showUpgradeDialog() {
    const overlay = document.createElement("div");
    overlay.className = "sv-upgrade-overlay";
    overlay.innerHTML = `
        <div class="sv-upgrade-card">
            <button class="sv-profile-close" type="button" style="color:#94a3b8">×</button>
            <div class="sv-upgrade-head">
                <div class="sv-upgrade-icon">${wechatIconSvg()}</div>
                <div>
                    <div class="sv-upgrade-title">升级了解</div>
                    <div class="sv-upgrade-sub">添加客服微信，了解升级套餐及优惠政策。</div>
                </div>
            </div>
            <div class="sv-upgrade-qr-wrap">
                <img class="sv-upgrade-qr" src="${UPGRADE_QR_SRC}" alt="微信扫一扫">
            </div>
            <div class="sv-upgrade-scan">微信扫一扫</div>
            <div class="sv-upgrade-id">${wechatIconSvg()}<span>${escapeHtml(SUPPORT_WECHAT_ID)}</span></div>
        </div>
    `;
    const close = () => overlay.remove();
    overlay.querySelector(".sv-profile-close").onclick = close;
    overlay.onclick = (e) => { if (e.target === overlay) close(); };
    document.body.appendChild(overlay);
}

async function startWechatBind(token, user) {
    const userId = user.id || user.user_id;
    if (!userId) { alert('无法获取用户信息，请重新登录'); return; }

    // 1. 获取绑定 URL
    let bindUrl, state;
    try {
        const res = await fetch(`${API_BASE}/auth/wechat/bind/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ user_id: Number(userId) })
        });
        const data = await res.json();
        if (data.code !== 200 || !data.data) { alert(data.message || '获取微信授权链接失败'); return; }
        bindUrl = data.data.bind_url || data.data.login_url || data.data.url;
        state = data.data.state;
        if (!state) { try { state = new URL(bindUrl).searchParams.get('state'); } catch(e) {} }
        if (!bindUrl) { alert('返回数据中未找到授权链接'); return; }
    } catch(e) { alert('网络错误，请稍后重试'); return; }

    // 2. 用 iframe 内嵌微信扫码页（与登录流程一致）
    const iframeSrc = (() => {
        try {
            const u = new URL(bindUrl);
            const appid = u.searchParams.get("appid");
            const redirectUri = u.searchParams.get("redirect_uri");
            const st = u.searchParams.get("state");
            return `https://open.weixin.qq.com/connect/qrconnect?appid=${appid}&scope=snsapi_login&redirect_uri=${encodeURIComponent(redirectUri)}&state=${st}&login_type=jssdk&self_redirect=true&style=black`;
        } catch (_) { return bindUrl; }
    })();

    const qrModal = document.createElement('div');
    qrModal.className = 'sv-wechat-qr-modal';
    qrModal.innerHTML = `
        <div class="sv-wechat-qr-box">
            <div class="sv-wechat-qr-title">微信扫码绑定</div>
            <iframe class="sv-wechat-qr-iframe" src="${iframeSrc}" style="width:300px;height:400px;border:none;border-radius:8px;background:#fff;"></iframe>
            <div class="sv-wechat-qr-tip" id="sv-wechat-bind-tip">请使用微信扫码完成绑定</div>
            <button class="sv-wechat-qr-close" id="sv-wechat-qr-close-btn">取消</button>
        </div>
    `;
    document.body.appendChild(qrModal);

    let pollTimer = null;
    const stopPoll = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };
    document.getElementById('sv-wechat-qr-close-btn').onclick = () => { stopPoll(); qrModal.remove(); };

    // 3. 轮询绑定状态
    if (state) {
        pollTimer = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/auth/wechat/bind/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify({ state })
                });
                const data = await res.json();
                if (data.code === 200) {
                    stopPoll();
                    qrModal.remove();
                    const u = JSON.parse(localStorage.getItem('sv_user') || '{}');
                    u.wechat_openid = data.data?.openid || 'bound';
                    localStorage.setItem('sv_user', JSON.stringify(u));
                    alert('微信绑定成功！');
                    hideProfileDialog();
                    showProfileDialog();
                }
            } catch(e) { /* 忽略轮询异常 */ }
        }, 2000);
        setTimeout(() => {
            if (pollTimer) {
                stopPoll();
                const tip = document.getElementById('sv-wechat-bind-tip');
                if (tip) tip.textContent = '二维码已过期，请关闭后重试';
            }
        }, 120000);
    }
}

function showEditNicknameDialog(currentNickname) {
    const modal = document.createElement('div');
    modal.className = 'sv-profile-overlay';
    modal.style.zIndex = '10002';
    modal.innerHTML = `
        <div class="sv-profile-dialog" style="width:400px;">
            <button class="sv-profile-close" id="sv-nickname-close">×</button>
            <div class="sv-profile-title">修改昵称</div>
            <input type="text" id="sv-nickname-input" class="sv-nickname-input" value="${currentNickname}" placeholder="请输入新昵称" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;margin-bottom:16px;">
            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button class="sv-profile-btn" id="sv-nickname-cancel">取消</button>
                <button class="sv-profile-btn" id="sv-nickname-submit" style="background:#2dd4bf;border-color:#2dd4bf;">确定</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('sv-nickname-close').onclick = closeModal;
    document.getElementById('sv-nickname-cancel').onclick = closeModal;
    modal.onclick = (e) => { if (e.target === modal) closeModal(); };

    document.getElementById('sv-nickname-submit').onclick = async () => {
        const newNickname = document.getElementById('sv-nickname-input').value.trim();
        if (!newNickname) {
            alert('请输入昵称');
            return;
        }

        const token = localStorage.getItem("sv_token");
        try {
            const res = await fetch(`${API_BASE}/user/info`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ nickname: newNickname })
            });
            const data = await res.json();
            if (data.code === 200) {
                // 更新本地存储的用户信息
                const user = JSON.parse(localStorage.getItem("sv_user") || "{}");
                user.nickname = newNickname;
                localStorage.setItem("sv_user", JSON.stringify(user));
                
                alert('昵称修改成功');
                closeModal();
                // 刷新个人中心
                hideProfileDialog();
                showProfileDialog();
            } else {
                alert(data.message || '修改失败');
            }
        } catch (e) {
            alert('网络错误，请稍后重试');
        }
    };
}

function showChangePasswordDialog() {
    const modal = document.createElement('div');
    modal.className = 'sv-profile-overlay';
    modal.style.zIndex = '10002';
    modal.innerHTML = `
        <div class="sv-profile-dialog" style="width:400px;">
            <button class="sv-profile-close" id="sv-pwd-close">×</button>
            <div class="sv-profile-title">修改密码</div>
            <div style="position:relative;margin-bottom:12px;">
                <input type="password" id="sv-old-pwd" placeholder="请输入旧密码" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px 40px 12px 12px;color:white;font-size:14px;box-sizing:border-box;">
                <span class="sv-pwd-eye" data-target="sv-old-pwd" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);cursor:pointer;color:#667788;font-size:16px;">👁</span>
            </div>
            <div style="position:relative;margin-bottom:12px;">
                <input type="password" id="sv-new-pwd" placeholder="请输入新密码（至少6位）" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px 40px 12px 12px;color:white;font-size:14px;box-sizing:border-box;">
                <span class="sv-pwd-eye" data-target="sv-new-pwd" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);cursor:pointer;color:#667788;font-size:16px;">👁</span>
            </div>
            <div style="position:relative;margin-bottom:4px;">
                <input type="password" id="sv-confirm-pwd" placeholder="请再次输入新密码" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px 40px 12px 12px;color:white;font-size:14px;box-sizing:border-box;">
                <span class="sv-pwd-eye" data-target="sv-confirm-pwd" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);cursor:pointer;color:#667788;font-size:16px;">👁</span>
            </div>
            <div id="sv-pwd-hint" style="color:#ef4444;font-size:12px;min-height:18px;margin-bottom:12px;"></div>
            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button class="sv-profile-btn" id="sv-pwd-cancel">取消</button>
                <button class="sv-profile-btn" id="sv-pwd-submit" style="background:#2dd4bf;border-color:#2dd4bf;">确定修改</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('sv-pwd-close').onclick = closeModal;
    document.getElementById('sv-pwd-cancel').onclick = closeModal;
    modal.onclick = (e) => { if (e.target === modal) closeModal(); };

    // 显示/隐藏密码切换
    modal.querySelectorAll('.sv-pwd-eye').forEach(eye => {
        eye.onclick = () => {
            const input = document.getElementById(eye.dataset.target);
            if (input.type === 'password') { input.type = 'text'; eye.style.color = '#2dd4bf'; }
            else { input.type = 'password'; eye.style.color = '#667788'; }
        };
    });

    const hintEl = document.getElementById('sv-pwd-hint');
    const newPwdEl = document.getElementById('sv-new-pwd');
    const confirmPwdEl = document.getElementById('sv-confirm-pwd');
    const checkMatch = () => {
        const n = newPwdEl.value, c = confirmPwdEl.value;
        if (c && n && n !== c) {
            hintEl.textContent = '两次输入的新密码不一致';
            confirmPwdEl.style.borderColor = '#ef4444';
        } else if (n && n.length < 6) {
            hintEl.textContent = '新密码至少6位';
            confirmPwdEl.style.borderColor = '#334455';
        } else {
            hintEl.textContent = '';
            confirmPwdEl.style.borderColor = '#334455';
        }
    };
    newPwdEl.oninput = checkMatch;
    confirmPwdEl.oninput = checkMatch;

    document.getElementById('sv-pwd-submit').onclick = async () => {
        const oldPwd = document.getElementById('sv-old-pwd').value;
        const newPwd = newPwdEl.value;
        const confirmPwd = confirmPwdEl.value;

        if (!oldPwd || !newPwd || !confirmPwd) { alert('请填写完整信息'); return; }
        if (newPwd.length < 6) { alert('新密码至少6位'); return; }
        if (newPwd !== confirmPwd) { alert('两次输入的新密码不一致'); return; }

        const token = localStorage.getItem("sv_token");
        try {
            const res = await fetch(`${API_BASE}/auth/change-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
            });
            const data = await res.json();
            if (data.code === 200) {
                alert('密码修改成功');
                closeModal();
            } else {
                alert(data.message || '修改失败');
            }
        } catch (e) {
            alert('网络错误，请稍后重试');
        }
    };
}

function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function maskPhone(phone) {
    const p = String(phone || "");
    if (!p) return "未绑定";
    return p.length >= 11 ? p.substring(0, 3) + "****" + p.substring(7) : p;
}

function maskEmail(email) {
    const v = String(email || "");
    if (!v) return "未绑定";
    const at = v.indexOf("@");
    if (at <= 0) return v;
    const local = v.slice(0, at);
    const domain = v.slice(at);
    if (local.length <= 2) return `${local[0] || ""}***${domain}`;
    if (local.length <= 4) return `${local.slice(0, 1)}***${local.slice(-1)}${domain}`;
    return `${local.slice(0, 3)}***${local.slice(-2)}${domain}`;
}

function copyText(text, okMsg) {
    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => alert(okMsg)).catch(() => window.prompt("复制用户ID", text));
        return;
    }
    window.prompt("复制用户ID", text);
}

function isValidMobile(phone) { return /^1\d{10}$/.test(phone); }
function isValidEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || "").trim()); }

async function postAuth(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` },
        body: JSON.stringify(body),
    });
    return res.json();
}

function openProfileModal(innerHtml) {
    const modal = document.createElement("div");
    modal.className = "sv-profile-overlay";
    modal.style.zIndex = "10002";
    modal.innerHTML = innerHtml;
    document.body.appendChild(modal);
    let timer = null;
    const close = () => { if (timer) clearInterval(timer); modal.remove(); };
    modal.querySelector(".sv-profile-close")?.addEventListener("click", close);
    modal.onclick = (e) => { if (e.target === modal) close(); };
    return {
        modal,
        close,
        startCountdown(btn) {
            let n = 60;
            btn.disabled = true;
            btn.textContent = `${n}s`;
            timer = setInterval(() => {
                if (--n <= 0) {
                    clearInterval(timer);
                    timer = null;
                    btn.disabled = false;
                    btn.textContent = "发送验证码";
                } else {
                    btn.textContent = `${n}s`;
                }
            }, 1000);
        },
    };
}

function showBindAccountDialog(kind) {
    const isEmail = kind === "email";
    const { modal, close, startCountdown } = openProfileModal(`
        <div class="sv-profile-dialog" style="width:400px;">
            <button class="sv-profile-close">×</button>
            <div class="sv-profile-title">${isEmail ? "绑定邮箱" : "绑定手机号"}</div>
            <input type="text" id="sv-bind-account" placeholder="${isEmail ? "请输入邮箱" : "请输入手机号"}" ${isEmail ? "" : 'maxlength="11"'} style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;margin-bottom:12px;">
            <div style="display:flex;gap:8px;margin-bottom:16px;">
                <input type="text" id="sv-bind-code" placeholder="验证码" style="flex:1;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;">
                <button class="sv-profile-btn" id="sv-bind-send" style="white-space:nowrap;">发送验证码</button>
            </div>
            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button class="sv-profile-btn" id="sv-bind-cancel">取消</button>
                <button class="sv-profile-btn" id="sv-bind-submit" style="background:#2dd4bf;border-color:#2dd4bf;">确定绑定</button>
            </div>
        </div>
    `);
    modal.querySelector("#sv-bind-cancel").onclick = close;

    modal.querySelector("#sv-bind-send").onclick = async () => {
        const account = modal.querySelector("#sv-bind-account").value.trim();
        if (isEmail ? !isValidEmail(account) : !isValidMobile(account)) {
            alert(isEmail ? "请输入正确的邮箱" : "请输入正确的手机号");
            return;
        }
        try {
            const data = await postAuth(
                isEmail ? "/auth/send-email-code" : "/auth/send-code",
                isEmail ? { email: account } : { phone_number: account },
            );
            if (data.code === 200) {
                alert("验证码已发送");
                startCountdown(modal.querySelector("#sv-bind-send"));
            } else {
                alert(data.message || "发送失败");
            }
        } catch (e) {
            alert("网络错误，请稍后重试");
        }
    };

    modal.querySelector("#sv-bind-submit").onclick = async () => {
        const account = modal.querySelector("#sv-bind-account").value.trim();
        const code = modal.querySelector("#sv-bind-code").value.trim();
        if (isEmail ? !isValidEmail(account) : !isValidMobile(account)) {
            alert(isEmail ? "请输入正确的邮箱" : "请输入正确的手机号");
            return;
        }
        if (!code) { alert("请输入验证码"); return; }
        try {
            const data = await postAuth(
                isEmail ? "/user/bind-email" : "/user/bind-phone",
                isEmail ? { email: account, code } : { phone_number: account, code },
            );
            if (data.code === 200) {
                const user = JSON.parse(localStorage.getItem("sv_user") || "{}");
                if (isEmail) user.email = account;
                else user.phone_number = account;
                localStorage.setItem("sv_user", JSON.stringify(user));
                alert(isEmail ? "邮箱绑定成功" : "手机号绑定成功");
                close();
                hideProfileDialog();
                showProfileDialog();
            } else {
                alert(data.message || "绑定失败");
            }
        } catch (e) {
            alert("网络错误，请稍后重试");
        }
    };
}

function showSetPasswordDialog(phone) {
    const { modal, close, startCountdown } = openProfileModal(`
        <div class="sv-profile-dialog" style="width:400px;">
            <button class="sv-profile-close">×</button>
            <div class="sv-profile-title">设置密码</div>
            <input type="text" value="${escapeHtml(maskPhone(phone))}" readonly style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:#8899aa;font-size:14px;box-sizing:border-box;margin-bottom:12px;">
            <input type="password" id="sv-setpwd-new" placeholder="请输入新密码（至少6位）" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;margin-bottom:12px;">
            <input type="password" id="sv-setpwd-confirm" placeholder="请再次输入新密码" style="width:100%;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;margin-bottom:12px;">
            <div style="display:flex;gap:8px;margin-bottom:8px;">
                <input type="text" id="sv-setpwd-code" placeholder="验证码" style="flex:1;background:#1e3a4a;border:1px solid #334455;border-radius:8px;padding:12px;color:white;font-size:14px;box-sizing:border-box;">
                <button class="sv-profile-btn" id="sv-setpwd-send" style="white-space:nowrap;">发送验证码</button>
            </div>
            <div id="sv-setpwd-hint" style="color:#ef4444;font-size:12px;min-height:18px;margin-bottom:12px;"></div>
            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button class="sv-profile-btn" id="sv-setpwd-cancel">取消</button>
                <button class="sv-profile-btn" id="sv-setpwd-submit" style="background:#2dd4bf;border-color:#2dd4bf;">确定设置</button>
            </div>
        </div>
    `);
    modal.querySelector("#sv-setpwd-cancel").onclick = close;
    const hintEl = modal.querySelector("#sv-setpwd-hint");
    const newEl = modal.querySelector("#sv-setpwd-new");
    const confirmEl = modal.querySelector("#sv-setpwd-confirm");
    const checkMatch = () => {
        hintEl.textContent = (confirmEl.value && newEl.value && newEl.value !== confirmEl.value)
            ? "两次输入的新密码不一致" : "";
    };
    newEl.oninput = checkMatch;
    confirmEl.oninput = checkMatch;

    modal.querySelector("#sv-setpwd-send").onclick = async () => {
        try {
            const data = await postAuth("/auth/send-code", { phone_number: phone });
            if (data.code === 200) {
                alert("验证码已发送");
                startCountdown(modal.querySelector("#sv-setpwd-send"));
            } else {
                alert(data.message || "发送失败");
            }
        } catch (e) {
            alert("网络错误，请稍后重试");
        }
    };

    modal.querySelector("#sv-setpwd-submit").onclick = async () => {
        const code = modal.querySelector("#sv-setpwd-code").value.trim();
        const newPwd = newEl.value;
        if (!code) { alert("请输入验证码"); return; }
        if (newPwd.length < 6) { alert("新密码至少6位"); return; }
        if (newPwd !== confirmEl.value) { alert("两次输入的新密码不一致"); return; }
        try {
            const data = await postAuth("/auth/reset-password", {
                phone_number: phone, code, new_password: newPwd,
            });
            if (data.code === 200) {
                alert("密码设置成功");
                close();
            } else {
                alert(data.message || "修改失败");
            }
        } catch (e) {
            alert("网络错误，请稍后重试");
        }
    };
}
