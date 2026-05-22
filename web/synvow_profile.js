/**
 * SynVow 个人中心对话框
 */
import { $el, getToken, injectStyle, API_BASE } from "./dom.js";
import { showLoginDialog, showBindPhoneDialog, clearAuthFile } from "./synvow_login.js";

let profileDialog = null;

export function showProfileDialog() {
    if (profileDialog) {
        profileDialog.remove();
        profileDialog = null;
    }

    injectStyle("sv-profile-style", `
        .sv-profile-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-profile-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:700px; position:relative; }
        .sv-profile-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-profile-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-profile-close:hover { color:white; }
        .sv-profile-loading { text-align:center; color:#667788; padding:40px; }
        .sv-profile-row { display:flex; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:16px; }
        .sv-profile-label { color:#8899aa; font-size:14px; }
        .sv-profile-value { color:white; font-size:14px; font-weight:bold; }
        .sv-profile-link { color:#2dd4bf; font-size:13px; cursor:pointer; margin-left:8px; }
        .sv-profile-link:hover { text-decoration:underline; }
        .sv-profile-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; padding:16px; background:#1e3a4a; border-radius:8px; }
        .sv-profile-stat { text-align:center; }
        .sv-profile-stat-label { color:#8899aa; font-size:12px; margin-bottom:4px; }
        .sv-profile-stat-value { color:#2dd4bf; font-size:18px; font-weight:bold; }
        .sv-profile-bind-status { padding:2px 8px; border-radius:4px; font-size:12px; }
        .sv-profile-bind-yes { background:#22c55e20; color:#22c55e; }
        .sv-profile-bind-no { background:#ef444420; color:#ef4444; }
        .sv-profile-actions { display:flex; gap:12px; margin-top:8px; }
        .sv-profile-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-profile-btn:hover { border-color:#2dd4bf; }
        .sv-profile-btn-danger { border-color:#ef4444; color:#ef4444; }
        .sv-profile-btn-danger:hover { background:#ef444420; }
        .sv-wechat-qr-modal { position:fixed; inset:0; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:10003; }
        .sv-wechat-qr-box { background:#1a2a3a; border-radius:12px; padding:24px; text-align:center; width:280px; }
        .sv-wechat-qr-title { color:#2dd4bf; font-size:16px; font-weight:bold; margin-bottom:16px; }
        .sv-wechat-qr-img { width:200px; height:200px; background:white; padding:8px; border-radius:8px; margin-bottom:12px; }
        .sv-wechat-qr-tip { color:#8899aa; font-size:13px; margin-bottom:16px; }
        .sv-wechat-qr-close { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 16px; color:white; font-size:13px; cursor:pointer; }
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

        const user = JSON.parse(localStorage.getItem("sv_user") || "{}");

        try {
            const res = await fetch(`${API_BASE}/account/summary`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.code === 200 && data.data) {
                const summary = data.data;
                const phoneNumber = user.phone_number || "未绑定";
                const maskedPhone = phoneNumber.length >= 11 ? 
                    phoneNumber.substring(0, 3) + "****" + phoneNumber.substring(7) : phoneNumber;

                contentDiv.innerHTML = `
                    <div class="sv-profile-row">
                        <span class="sv-profile-label">账户昵称：</span>
                        <span class="sv-profile-value">${user.nickname || user.phone_number || "用户"}</span>
                        <span class="sv-profile-link" id="sv-edit-nickname-btn">修改昵称</span>
                        <span class="sv-profile-label" style="margin-left:24px;">密码管理</span>
                        <span class="sv-profile-link" id="sv-change-pwd-btn">修改密码</span>
                        <span class="sv-profile-link sv-profile-btn-danger" style="margin-left:auto;" id="sv-logout-btn">退出登录</span>
                    </div>
                    <div class="sv-profile-stats" style="grid-template-columns:repeat(3,1fr);">
                        <div class="sv-profile-stat">
                            <div class="sv-profile-stat-label">当前余额</div>
                            <div class="sv-profile-stat-value">¥${parseFloat(summary.balance ?? 0).toFixed(2)}</div>
                        </div>
                        <div class="sv-profile-stat">
                            <div class="sv-profile-stat-label">总消耗量</div>
                            <div class="sv-profile-stat-value">¥${parseFloat(summary.total_consumption ?? 0).toFixed(2)}</div>
                        </div>
                        <div class="sv-profile-stat">
                            <div class="sv-profile-stat-label">总充值量</div>
                            <div class="sv-profile-stat-value">¥${parseFloat(summary.total_recharge ?? 0).toFixed(2)}</div>
                        </div>
                    </div>
                    <div class="sv-profile-row" style="gap:32px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="sv-profile-label">手机号：</span>
                            <span class="sv-profile-value">${user.phone_number ? maskedPhone : "未绑定"}</span>
                            ${user.phone_number
                                ? `<span class="sv-profile-bind-status sv-profile-bind-yes">已绑定</span>`
                                : `<span class="sv-profile-bind-status sv-profile-bind-no">未绑定</span><span class="sv-profile-link" id="sv-bind-phone-btn">立即绑定</span>`
                            }
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="sv-profile-label">微信：</span>
                            ${(user.wechat_openid || user.openid)
                                ? `<span class="sv-profile-bind-status sv-profile-bind-yes">已绑定</span>`
                                : `<span class="sv-profile-bind-status sv-profile-bind-no">未绑定</span><span class="sv-profile-link" id="sv-bind-wechat-btn">立即绑定</span>`
                            }
                        </div>
                    </div>
                `;

                // 绑定修改昵称事件
                document.getElementById('sv-edit-nickname-btn').onclick = () => showEditNicknameDialog(user.nickname || '');
                // 绑定修改密码按钮
                document.getElementById('sv-change-pwd-btn').onclick = () => showChangePasswordDialog();
                // 绑定手机号按钮
                const bindBtn = document.getElementById('sv-bind-phone-btn');
                if (bindBtn) bindBtn.onclick = () => showBindPhoneDialog();
                // 绑定微信按钮
                const bindWechatBtn = document.getElementById('sv-bind-wechat-btn');
                if (bindWechatBtn) bindWechatBtn.onclick = () => startWechatBind(token, user);
                // 绑定退出登录按钮
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
                contentDiv.innerHTML = `<div class="sv-profile-loading">${data.message || '获取信息失败'}</div>`;
            }
        } catch (e) {
            contentDiv.innerHTML = '<div class="sv-profile-loading">网络错误，请稍后重试</div>';
        }
    }

}

export function hideProfileDialog() {
    if (profileDialog) profileDialog.style.display = "none";
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
                alert('密码修改成功，请重新登录');
                closeModal();
                localStorage.removeItem('sv_token');
                localStorage.removeItem('sv_refresh_token');
                localStorage.removeItem('sv_user');
                clearAuthFile();
                hideProfileDialog();
                window.synvowRefreshAccount?.();
                showLoginDialog();
            } else {
                alert(data.message || '修改失败');
            }
        } catch (e) {
            alert('网络错误，请稍后重试');
        }
    };
}
