/**
 * SynVow 充值中心对话框
 */
import { $el } from "./dom.js";

let rechargeDialog = null;
let pollTimer = null;
let selectedAmount = null;
let selectedPayment = "wechat";

const AMOUNTS = [5, 10, 20, 50, 100, 200];

export function showRechargeDialog() {
    if (rechargeDialog) { 
        rechargeDialog.remove();
        rechargeDialog = null;
    }

    const style = document.createElement('style');
    style.textContent = `
        .sv-recharge-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-recharge-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:480px; position:relative; }
        .sv-recharge-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-recharge-title svg { width:18px; height:18px; }
        .sv-amount-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:20px; }
        .sv-amount-btn { background:#1e3a4a; border:2px solid #334455; border-radius:8px; padding:16px; color:white; font-size:18px; font-weight:bold; cursor:pointer; transition:all 0.2s; }
            .sv-amount-btn .sv-currency { font-size:12px; font-weight:normal; margin-right:2px; }
        .sv-amount-btn:hover { border-color:#2dd4bf; background:#1e4a5a; }
        .sv-amount-btn.selected { border-color:#2dd4bf; background:linear-gradient(135deg,#1e4a5a,#0d3a4a); box-shadow:0 0 10px rgba(45,212,191,0.3); }
        .sv-custom-input { width:100%; background:#1e3a4a; border:1px solid #334455; border-radius:8px; padding:14px 16px; color:white; font-size:14px; margin-bottom:8px; box-sizing:border-box; }
        .sv-custom-input::placeholder { color:#667788; }
        .sv-custom-input:focus { outline:none; border-color:#2dd4bf; }
        .sv-custom-hint { color:#667788; font-size:12px; margin-bottom:20px; }
        .sv-payment-row { display:flex; gap:12px; margin-bottom:20px; }
        .sv-payment-btn { flex:1; background:#1e3a4a; border:2px solid #334455; border-radius:8px; padding:12px; color:white; font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px; transition:all 0.2s; }
        .sv-payment-btn:hover { border-color:#556677; }
        .sv-payment-btn.selected { border-color:#2dd4bf; }
        .sv-payment-btn svg { width:20px; height:20px; }
        .sv-submit-btn { width:100%; background:linear-gradient(90deg,#2dd4bf,#22d3ee); border:none; border-radius:8px; padding:14px; color:white; font-size:16px; font-weight:bold; cursor:pointer; margin-bottom:16px; }
        .sv-submit-btn:hover { filter:brightness(1.1); }
        .sv-submit-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-recharge-footer { text-align:center; color:#667788; font-size:12px; }
        .sv-recharge-footer a { color:#2dd4bf; text-decoration:underline; cursor:pointer; }
        .sv-recharge-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-recharge-close:hover { color:white; }
        .sv-wechat-icon { color:#07c160; }
        .sv-alipay-icon { color:#1677ff; }
        .sv-qrcode-container { text-align:center; padding:20px; }
        .sv-qrcode-container img { width:200px; height:200px; background:white; padding:10px; border-radius:8px; }
        .sv-qrcode-tip { color:#667788; font-size:14px; margin-top:12px; }
        .sv-qrcode-order { color:#556677; font-size:12px; margin-top:8px; }
    `;
    document.head.appendChild(style);

    const lightningIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>`;
    const wechatIcon = `<svg viewBox="0 0 1024 1024" fill="currentColor"><path d="M690.1 377.4c5.9 0 11.8.2 17.6.5-24.4-128.7-158.3-227.1-319.9-227.1C209 150.8 64 271.4 64 420.2c0 81.1 43.6 154.2 111.9 203.6 5.5 3.9 9.1 10.3 9.1 17.6 0 2.4-.5 4.6-1.1 6.9-5.5 20.3-14.2 52.8-14.6 54.3-.7 2.6-1.7 5.2-1.7 7.9 0 5.9 4.8 10.8 10.8 10.8 2.3 0 4.2-.9 6.2-2l70.9-40.9c5.3-3.1 11-5 17.2-5 3.2 0 6.4.5 9.5 1.4 33.1 9.5 68.8 14.8 105.7 14.8 6 0 11.9-.1 17.8-.4-7.1-21-10.9-43.1-10.9-66 0-135.8 132.2-245.8 295.3-245.8zm-194.3-86.5c23.8 0 43.2 19.3 43.2 43.1s-19.3 43.1-43.2 43.1c-23.8 0-43.2-19.3-43.2-43.1s19.4-43.1 43.2-43.1zm-215.9 86.2c-23.8 0-43.2-19.3-43.2-43.1s19.3-43.1 43.2-43.1 43.2 19.3 43.2 43.1-19.4 43.1-43.2 43.1zm586.8 415.6c56.9-41.2 93.2-102 93.2-169.7 0-124-108.1-224.8-241.4-224.8-133.4 0-241.4 100.8-241.4 224.8S585 847.1 718.3 847.1c30.8 0 60.6-4.4 88.1-12.3 2.6-.8 5.2-1.2 7.9-1.2 5.2 0 9.9 1.6 14.3 4.1l59.1 34c1.7 1 3.3 1.7 5.2 1.7a9 9 0 0 0 6.4-2.6 9 9 0 0 0 2.6-6.4c0-2.2-.9-4.4-1.4-6.6-.3-1.2-7.6-28.3-12.2-45.3-.5-1.9-.9-3.8-.9-5.7.1-5.9 3.1-11.2 7.6-14.5zM600.2 587.2c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9c0 19.8-16.2 35.9-36 35.9zm179.9 0c-19.9 0-36-16.1-36-35.9 0-19.8 16.1-35.9 36-35.9s36 16.1 36 35.9a36.08 36.08 0 0 1-36 35.9z"/></svg>`;
    const alipayIcon = `<svg viewBox="0 0 1024 1024" fill="currentColor"><path d="M789.6 460.8c-19.2-6.4-41.6-12.8-64-19.2 12.8-32 22.4-67.2 28.8-102.4H608v-48h176v-32H608v-80h-64c-6.4 0-12.8 6.4-12.8 12.8v67.2H352v32h179.2v48H371.2v32h246.4c-6.4 25.6-12.8 51.2-22.4 73.6-70.4-19.2-144-35.2-208-35.2-108.8 0-176 54.4-176 134.4 0 83.2 73.6 134.4 182.4 134.4 89.6 0 172.8-38.4 243.2-108.8 54.4 32 99.2 67.2 131.2 99.2l44.8-44.8c-35.2-35.2-86.4-73.6-147.2-108.8 19.2-28.8 35.2-60.8 48-96 32 9.6 60.8 19.2 86.4 28.8l19.2-57.6zM393.6 620.8c-73.6 0-118.4-28.8-118.4-80s44.8-80 112-80c51.2 0 115.2 12.8 179.2 32-57.6 80-118.4 128-172.8 128z"/></svg>`;

    const amountBtns = AMOUNTS.map(amount => {
        const btn = $el("button.sv-amount-btn", { innerHTML: `<span class="sv-currency">¥</span>${amount}`, onclick: () => selectAmount(amount, btn) });
        return btn;
    });

    const customInput = $el("input.sv-custom-input", { type: "number", placeholder: "自定义金额", min: "1", oninput: (e) => {
        amountBtns.forEach(b => b.classList.remove("selected"));
        const val = parseInt(e.target.value);
        selectedAmount = val > 0 ? val : null;
        if (val <= 0 && e.target.value) e.target.value = "";
    }});

    const wechatBtn = $el("button.sv-payment-btn.selected", { innerHTML: `<span class="sv-wechat-icon">${wechatIcon}</span> 微信支付`, onclick: () => selectPayment("wechat", wechatBtn, alipayBtn) });
    const alipayBtn = $el("button.sv-payment-btn", { innerHTML: `<span class="sv-alipay-icon">${alipayIcon}</span> 支付宝支付`, onclick: () => selectPayment("alipay", alipayBtn, wechatBtn) });

    function selectAmount(amount, btn) {
        amountBtns.forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        selectedAmount = amount;
        customInput.value = "";
    }

    function selectPayment(type, activeBtn, otherBtn) {
        selectedPayment = type;
        activeBtn.classList.add("selected");
        otherBtn.classList.remove("selected");
    }

    const submitBtn = $el("button.sv-submit-btn", { textContent: "立即支付", onclick: handleSubmit });

    rechargeDialog = $el("div.sv-recharge-overlay", {
        onclick: (e) => { if (e.target === rechargeDialog) hideRechargeDialog(); }
    }, [
        $el("div.sv-recharge-dialog", {}, [
            $el("button.sv-recharge-close", { textContent: "×", onclick: hideRechargeDialog }),
            $el("div.sv-recharge-title", { innerHTML: `${lightningIcon} 快速充值` }),
            $el("div.sv-amount-grid", {}, amountBtns),
            customInput,
            $el("div.sv-custom-hint", { textContent: "自定义金额，仅支持整数充值。" }),
            $el("div.sv-payment-row", {}, [wechatBtn, alipayBtn]),
            submitBtn,
            $el("div.sv-recharge-footer", {}, ["支付成功即充值到账，视为同意《服务条款》及退款政策。"])
        ])
    ]);

    document.body.appendChild(rechargeDialog);
}

async function handleSubmit() {
    if (!selectedAmount || selectedAmount <= 0) {
        alert("请选择或输入充值金额");
        return;
    }
    
    const token = localStorage.getItem("sv_token");
    if (!token) {
        alert("请先登录");
        return;
    }

    const accountReady = await ensureAccountReady(token);
    if (!accountReady.ok) {
        alert(accountReady.message || "账户状态异常，暂时无法充值");
        return;
    }
    
    try {
        const actualPayType = selectedPayment === "wechat" ? "wxpay" : "alipay";
        const requestBody = {
            amount: Number(selectedAmount),
            paymentType: "zpayz",
            payType: actualPayType
        };
        console.log("[SynVow Recharge] 请求: https://service.synvow.com/api/v1/account/recharge");
        console.log("[SynVow Recharge] Token:", token ? token.substring(0, 30) + '...' : '无');
        console.log("[SynVow Recharge] 请求参数:", JSON.stringify(requestBody, null, 2));
        const res = await fetch("/sv_api/account/recharge", {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(requestBody)
        });
        const text = await res.text();
        console.log("[SynVow Recharge] 响应原文:", text);
        let data;
        try {
            data = JSON.parse(text);
            console.log("[SynVow Recharge] 响应数据:", JSON.stringify(data, null, 2));
        } catch (e) {
            alert("服务器响应错误");
            return;
        }
        
        if (data.code === 200 && data.data) {
            const orderNo = data.data.orderNo || data.data.order_no || data.data.order_id || '';
            const paymentData = data.data.paymentData || data.data.payment_data || {};
            const payUrl = data.data.paymentUrl || paymentData.payUrl || data.data.payment_url || data.data.pay_url;
            const qrCode = paymentData.qrcode || data.data.qr_code || data.data.qrcode;
            const qrImg = paymentData.img;

            if (qrImg) {
                showQrCode(qrImg, orderNo);
            } else if (payUrl) {
                showQrCode(payUrl, orderNo);
            } else if (qrCode) {
                showQrCode(qrCode, orderNo);
            } else {
                alert("创建订单失败，无支付信息");
            }
        } else {
            alert(data.message || "创建订单失败");
        }
    } catch (e) {
        alert("网络错误，请稍后重试");
    }
}

async function ensureAccountReady(token) {
    const headers = { "Authorization": `Bearer ${token}` };
    const isAccountMissing = (data) => {
        const code = Number(data?.code || 0);
        const msg = String(data?.message || "").toLowerCase();
        if (msg.includes("账户不存在")) return true;
        if (msg.includes("record not found")) return true;
        if (msg.includes("not found") && msg.includes("账户")) return true;
        if (code === 404) return true;
        return false;
    };

    try {
        // First pass: direct account lookup
        let res = await fetch("/sv_api/account/info", { headers });
        let data = await res.json();
        if (data.code === 200) {
            return { ok: true };
        }
        if (!isAccountMissing(data)) {
            return { ok: false, message: data.message || "获取账户信息失败" };
        }

        // Retry path: some backends create/link account on this endpoint.
        await fetch("/sv_api/user/with-account", { headers });

        res = await fetch("/sv_api/account/info", { headers });
        data = await res.json();
        if (data.code === 200) {
            return { ok: true };
        }

        if (isAccountMissing(data)) {
            return {
                ok: false,
                message: "当前账号未开通资金账户，请联系管理员初始化账户后再充值"
            };
        }

        return { ok: false, message: data.message || "账户状态异常，无法充值" };
    } catch (e) {
        return { ok: false, message: "网络错误，无法校验账户状态" };
    }
}

function showQrCode(imgSrc, orderNo) {
    const dialog = rechargeDialog.querySelector(".sv-recharge-dialog");
    dialog.innerHTML = `
        <button class="sv-recharge-close" id="sv-qr-close">×</button>
        <div class="sv-recharge-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> 扫码支付</div>
        <div class="sv-qrcode-container">
            <img src="${imgSrc}" alt="支付二维码">
            <div class="sv-qrcode-tip">请使用${selectedPayment === 'wechat' ? '微信' : '支付宝'}扫码支付</div>
            ${orderNo ? `<div class="sv-qrcode-order">订单号：${orderNo}</div>` : ''}
            </div>
    `;
    document.getElementById('sv-qr-close').onclick = () => { stopPoll(); hideRechargeDialog(); };
    startPoll();
}

let lastBalance = null;

function getBalanceText() {
    return document.getElementById('sv-main-balance')?.textContent?.trim() || '';
}

function startPoll() {
    stopPoll();
    lastBalance = getBalanceText();
    pollTimer = setInterval(async () => {
        window.dispatchEvent(new CustomEvent("synvow_refresh_balance"));
        // 等待余额元素更新后再对比（余额请求约需 500ms）
        setTimeout(() => {
            const newBalance = getBalanceText();
            if (newBalance && newBalance !== lastBalance && !newBalance.includes('加载') && !newBalance.includes('失败')) {
                stopPoll();
                alert('支付成功，余额已更新！');
                hideRechargeDialog();
            }
        }, 1500);
    }, 3000);
}

function stopPoll() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

export function hideRechargeDialog() {
    stopPoll();
    if (rechargeDialog) rechargeDialog.style.display = "none";
}
