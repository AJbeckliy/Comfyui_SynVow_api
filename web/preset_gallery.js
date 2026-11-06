import { app } from "../../scripts/app.js";
function ensureImageInputs(node) {
  for (let i = 1; i <= 8; i++) {
    const name = `image_${i}`;
    if (!node.inputs?.some(input => input.name === name)) node.addInput(name, "IMAGE");
  }
}
app.registerExtension({
  name: "PresetGallery",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "PresetGallery") return;
    const configure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = configure?.apply(this, arguments);
      ensureImageInputs(this);
      return result;
    };
    const orig = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      orig?.apply(this, arguments);
      ensureImageInputs(this);
      const w = this.widgets.find(x => x.name === "preset");
      this.addWidget("button", "🖼 打开预设画廊", null, () => openGallery(w, this));
    };
  },
});
const CSS = `
.pg-bg{position:fixed;inset:0;background:rgba(10,12,18,.72);backdrop-filter:blur(8px);z-index:9999;display:flex;align-items:center;justify-content:center;font-family:system-ui,"PingFang SC","Microsoft YaHei",sans-serif}
.pg-box{width:min(1100px,92vw);height:86vh;background:#1b1e26;border:1px solid #2c313d;border-radius:16px;box-shadow:0 20px 60px #0008;display:flex;flex-direction:column;overflow:hidden}
.pg-head{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid #2c313d}
.pg-title{color:#fff;font-size:16px;font-weight:600;white-space:nowrap}
.pg-q{flex:1;background:#12141a;border:1px solid #2c313d;border-radius:10px;color:#eee;padding:9px 14px;font-size:13px;outline:none}
.pg-q:focus{border-color:#5b8cff}
.pg-x{background:none;border:none;color:#999;font-size:22px;cursor:pointer;line-height:1}.pg-x:hover{color:#fff}
.pg-tabs{display:flex;gap:8px;flex-wrap:wrap;padding:12px 20px}
.pg-tab{background:#252a35;border:none;color:#bbb;padding:6px 14px;border-radius:999px;font-size:12px;cursor:pointer;transition:.15s}
.pg-tab:hover{background:#30364a;color:#fff}.pg-tab.on{background:#5b8cff;color:#fff}
.pg-grid{flex:1;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));grid-auto-rows:max-content;align-content:start;gap:14px;padding:6px 20px 20px}
.pg-card{cursor:pointer;background:#232733;border-radius:12px;overflow:hidden;transition:transform .15s,box-shadow .15s;border:2px solid transparent;display:flex;flex-direction:column;height:max-content}
.pg-card:hover{transform:translateY(-3px);box-shadow:0 8px 20px #0007}
.pg-card.sel{border-color:#5b8cff}
.pg-card img{width:100%;aspect-ratio:1;object-fit:contain;display:block;background:#12141a;flex:none}
.pg-name{color:#ddd;font-size:12.5px;line-height:1.4;padding:7px 8px 9px;text-align:center;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.8em;box-sizing:content-box}
.pg-card{position:relative}
.pg-fav{position:absolute;top:6px;right:6px;width:28px;height:28px;border-radius:50%;border:none;background:rgba(0,0,0,.45);color:#fff;font-size:16px;line-height:28px;text-align:center;cursor:pointer;opacity:0;transition:opacity .15s,transform .15s;padding:0;z-index:2}
.pg-card:hover .pg-fav,.pg-fav.on{opacity:1}
.pg-fav:hover{transform:scale(1.12)}
.pg-fav.on{width:auto;min-width:28px;padding:0 9px;border-radius:14px;color:#ffc53d;background:rgba(0,0,0,.82)}
.pg-fav.on::after{content:"取消收藏";margin-left:4px;font-size:12px;vertical-align:1px}
.pg-placeholder{aspect-ratio:1;display:flex;align-items:center;justify-content:center;background:#12141a;color:#929bb0;font-size:13px}.pg-code{color:#91afff;font-size:11px;text-align:center;overflow-wrap:anywhere;padding:4px 8px}.pg-empty{grid-column:1/-1;color:#888;text-align:center;padding:60px 0;font-size:13px}`;
async function readGalleryJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
async function openGallery(w, node) {
  if (!document.getElementById("pg-css")) { const s = document.createElement("style"); s.id = "pg-css"; s.textContent = CSS; document.head.append(s); }
  let list;
  try {
    list = await readGalleryJSON("/preset_gallery/list");
    if (!Array.isArray(list) || list.some(it => !it || typeof it.label !== "string" || typeof it.code !== "string" || typeof it.thumb !== "string")) throw new Error("预设列表格式异常");
  } catch (error) {
    const overlay = document.createElement("div"); overlay.className = "pg-bg";
    const panel = document.createElement("div"); panel.className = "pg-box";
    panel.style.height = "auto"; panel.style.padding = "24px"; panel.style.color = "#eee";
    const message = document.createElement("p"); message.textContent = `画廊加载失败：${error.message}。请检查 ComfyUI 服务后重试。`;
    const retry = document.createElement("button"); retry.textContent = "重试";
    retry.onclick = () => { overlay.remove(); openGallery(w, node); };
    const close = document.createElement("button"); close.textContent = "关闭"; close.onclick = () => overlay.remove();
    panel.append(message, retry, close); overlay.append(panel); document.body.append(overlay);
    return;
  }
  let favs = new Set();
  let favoritesError = "";
  try {
    const values = await readGalleryJSON("/preset_gallery/favs");
    if (!Array.isArray(values) || values.some(v => typeof v !== "string")) throw new Error("收藏列表格式异常");
    favs = new Set(values);
  } catch (e) { favoritesError = "收藏加载失败，请重新打开画廊重试"; }
  let favoriteBusy = false;
  const el = (t, c, txt) => { const e = document.createElement(t); if (c) e.className = c; if (txt) e.textContent = txt; return e; };
  const bg = el("div", "pg-bg"), box = el("div", "pg-box"), head = el("div", "pg-head");
  const q = el("input", "pg-q"); q.placeholder = "搜索预设（支持中文、英文指令、模糊匹配，空格分隔多个词）…";
  const x = el("button", "pg-x", "×"); x.onclick = () => bg.remove();
  head.append(el("div", "pg-title", "预设画廊"), q, x);
  if (favoritesError) head.append(el("span", "pg-name", favoritesError));
  const tabs = el("div", "pg-tabs"), grid = el("div", "pg-grid");
  let cur = "全部";
  const sub = (k, t) => { let i = 0; for (const ch of k) { if (ch === t[i]) i++; if (i === t.length) return true; } return !t.length; };
  const hit = (k, s) => s.trim().toLowerCase().split(/\s+/).filter(Boolean).every(t => k.includes(t) || sub(k, t.replace(/^\//, "")));
  const empty = el("div", "pg-empty", "还没有收藏，鼠标移到卡片上点右上角的 ☆ 就能收藏");
  const favTab = () => tabs.querySelector('[data-n="已收藏"]');
  const apply = () => {
    let n = 0;
    grid.querySelectorAll(".pg-card").forEach(c => { const ok = (cur === "全部" || (cur === "已收藏" ? favs.has(c.dataset.code) : c.dataset.c === cur)) && hit(c.dataset.k, q.value); c.style.display = ok ? "" : "none"; if (ok) n++; });
    empty.textContent = cur === "已收藏" && !favs.size ? "还没有收藏，鼠标移到卡片上点右上角的 ☆ 就能收藏" : "没有找到匹配的预设";
    empty.style.display = n ? "none" : "";
    const ft = favTab(); if (ft) ft.textContent = `★ 已收藏 ${favs.size}`;
  };
  [...new Set([...["全部", "已收藏", "产品广告", "产品摄影", "人物写真", "风格"], ...list.map(i => i.cat).filter(Boolean)])].filter(n => n === "全部" || n === "已收藏" || list.some(i => i.cat === n)).forEach(n => {
    const b = el("button", "pg-tab" + (n === cur ? " on" : ""), n); b.dataset.n = n;
    b.onclick = () => { cur = n; tabs.childNodes.forEach(t => t.classList.toggle("on", t === b)); apply(); };
    tabs.append(b);
  });
  list.forEach(it => {
    const c = el("div", "pg-card" + (it.label === w.value ? " sel" : ""));
    const img = el("img"); img.loading = "lazy"; img.src = `/preset_gallery/thumb/${encodeURIComponent(it.thumb)}`;
    img.alt = it.label;
    img.onerror = () => img.replaceWith(el("div", "pg-placeholder", "暂无预览图"));
    c.append(img, el("div", "pg-code", it.code || ""), el("div", "pg-name", it.label)); c.title = `${it.code || ""} ${it.label}`;
    c.dataset.k = [it.label, it.code || "", (it.code || "").replace(/^\//, ""), it.alt || ""].join(" ").toLowerCase(); c.dataset.c = it.cat; c.dataset.code = it.code || it.label;
    const star = el("button", "pg-fav" + (favs.has(c.dataset.code) ? " on" : ""), favs.has(c.dataset.code) ? "★" : "☆");
    star.title = favs.has(c.dataset.code) ? "取消收藏" : "收藏";
    star.type = "button";
    star.onclick = async e => {
      e.stopPropagation();
      if (favoriteBusy || favoritesError) return;
      favoriteBusy = true;
      grid.querySelectorAll(".pg-fav").forEach(button => { button.disabled = true; });
      const code = c.dataset.code, on = !favs.has(code);
      on ? favs.add(code) : favs.delete(code);
      star.classList.toggle("on", on); star.textContent = on ? "★" : "☆";
      apply();
      try {
        const values = await readGalleryJSON("/preset_gallery/favs/set", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, fav: on }) });
        if (!Array.isArray(values) || values.some(v => typeof v !== "string")) throw new Error("收藏响应格式异常");
        if (values.includes(code) !== on) throw new Error("服务器未保存收藏变更");
        favs = new Set(values);
        grid.querySelectorAll(".pg-card").forEach(card => {
          const button = card.querySelector(".pg-fav"), selected = favs.has(card.dataset.code);
          button.title = selected ? "取消收藏" : "收藏";
          button.classList.toggle("on", selected); button.textContent = selected ? "★" : "☆";
        });
        apply();
      }
      catch (err) { on ? favs.delete(code) : favs.add(code); star.classList.toggle("on", !on); star.textContent = !on ? "★" : "☆"; apply(); alert("收藏保存失败：" + err.message + "。请确认已重启 ComfyUI 并刷新页面。"); }
      finally { favoriteBusy = false; grid.querySelectorAll(".pg-fav").forEach(button => { button.disabled = false; }); }
    };
    star.disabled = !!favoritesError;
    c.append(star);
    c.onclick = () => { w.value = it.label; w.callback?.(it.label); node.setDirtyCanvas(true, true); bg.remove(); };
    grid.append(c);
  });
  grid.append(empty);
  q.oninput = apply;
  apply();
  bg.onclick = e => { if (e.target === bg) bg.remove(); };
  box.append(head, tabs, grid); bg.append(box); document.body.append(bg); q.focus();
}
