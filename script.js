// ============ Config ============

// pasta das imagens
const IMG_DIR = "images/";

// mapeie nomes -> arquivos (use a parte em inglês do nome)
const imageMap = {
  "LEE LEO": "leeleo.png",
  "CHUEI LI YU": "chueliyu.png",
  "KANG WOO JIN": "kangwoojin.png",
  "LEE SANG WON": "leesangwon.png",
  "YUMEKI": "yumeki.png",
  "ZHOU AN XIN": "zhouanxin.png",
  "KIM GEON WOO": "kimgeonwoo.png",
  "KIM JUN SEO": "kimjunseo.png",
  "CHUNG SANG HYEON": "changsunghyeon.png",
  "HE XIN LONG": "hexinlong.png",
};

// ============ Helpers ============

function formatNumber(n){
  if(n===undefined||n===null||n==="") return "-";
  const num = Number(String(n).replace(/[^\d.-]/g, ""));
  if(Number.isNaN(num)) return n;
  return num.toLocaleString("en-US");
}

// slug “solto”
function slugify(str){
  return String(str)
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .replace(/[^a-zA-Z0-9]+/g,"-")
    .replace(/^-+|-+$/g,"")
    .toLowerCase();
}

// slug bem compacto
function tightSlug(str){
  return String(str)
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g,"");
}

// parte em inglês do nome completo
function getEnglishName(fullName){
  const m = fullName.match(/[A-Za-z].*$/);
  return (m ? m[0] : "").trim();
}

// resolve a URL da imagem (map + fallbacks)
function getImageUrl(fullName){
  const english = getEnglishName(fullName);
  const englishLower = english.toLowerCase();
  const englishTight = tightSlug(english);
  const englishHyphen = slugify(english);
  const fullTight = tightSlug(fullName);

  if (english && imageMap[english]) return IMG_DIR + imageMap[english];

  const candidates = [
    `${IMG_DIR}${englishTight}.png`,
    `${IMG_DIR}${englishHyphen}.png`,
    `${IMG_DIR}${fullTight}.png`,
  ];
  return candidates[0];
}

function parseCSV(text){
  const lines = text.trim().split(/\r?\n/);
  if(lines.length<2) return {headers:[], rows:[]};
  const headers = lines[0].split(",").map(h=>h.trim());
  const rows = lines.slice(1).map(l=>l.split(","));
  return {headers, rows};
}

function idx(headers, name, fallback=0){
  const i = headers.indexOf(name);
  return i===-1 ? fallback : i;
}

// ============ Rendering (two vertical columns) ============

function createCard(rankNumber, trainee, metricLabel, barPercent){
  const card = document.createElement("div");
  card.className = "card";

  const rank = document.createElement("div");
  rank.className = "rank";
  rank.textContent = `#${rankNumber}`;

  const img = document.createElement("img");
  img.className = "thumb";
  img.src = getImageUrl(trainee);
  img.loading = "lazy";
  img.referrerPolicy = "no-referrer";
  img.onerror = () => { img.src = IMG_DIR + "placeholder.png"; };

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `
    <div class="name">${trainee}</div>
    <div class="metric">${metricLabel}</div>
    <div class="bar"><div class="fill" style="width:0%"></div></div>
  `;

  const fill = meta.querySelector(".fill");
  requestAnimationFrame(() => fill.style.width = `${Math.max(4, barPercent)}%`);

  card.append(rank, img, meta);
  return card;
}

function renderTwoColumns(type, headers, rows){
  const container = document.getElementById("ranking");
  container.innerHTML = "";

  const leftRows  = rows.slice(0, 4);
  const rightRows = rows.slice(4, 8);

  const iName  = idx(headers,"trainee_name",0);
  const iViews = headers.indexOf("views");
  const iLikes = headers.indexOf("likes");
  const iComms = headers.indexOf("comments");
  const iScore = headers.indexOf("score_norm") !== -1 ? headers.indexOf("score_norm") : headers.indexOf("score");

  let valueIndex, labelFn;
  if(type==="views"){ valueIndex = iViews; labelFn = v=>`${formatNumber(v)} views`; }
  else if(type==="likes"){ valueIndex = iLikes; labelFn = v=>`${formatNumber(v)} likes`; }
  else if(type==="comments"){ valueIndex = iComms; labelFn = v=>`${formatNumber(v)} comments`; }
  else { valueIndex = iScore; labelFn = v=>`Score: ${v?Number(v).toFixed(3):"-"}`; }

  const values = rows.map(r => {
    const raw = r[valueIndex];
    const num = type==="overall" ? Number(raw) : Number(String(raw).replace(/[^\d.-]/g,""));
    return Number.isFinite(num) ? num : 0;
  });
  const maxVal = Math.max(...values, 1);

  const leftCol = document.createElement("div");
  leftCol.className = "col";
  const rightCol = document.createElement("div");
  rightCol.className = "col";

  const renderSide = (rowsChunk, offset, targetCol) => {
    rowsChunk.forEach((r, i) => {
      const trainee = r[iName] || "";
      const raw = r[valueIndex];
      const num = type==="overall" ? Number(raw) : Number(String(raw).replace(/[^\d.-]/g,""));
      const pct = Math.round((Math.max(0, num) / maxVal) * 100);
      const card = createCard(offset + i + 1, trainee, labelFn(raw), pct);
      targetCol.appendChild(card);
    });
  };

  renderSide(leftRows, 0, leftCol);   // #1–#4
  renderSide(rightRows, 4, rightCol); // #5–#8

  container.append(leftCol, rightCol);

  const now = new Date();
  document.getElementById("lastUpdate").textContent =
    `Last update: ${now.toLocaleString("en-US")}`;
}

// ============ Controller ============

let activeTab = "views"; // guarda a aba ativa

async function loadRanking(type){
  activeTab = type;

  // destaque somente nas abas que têm data-type
  document.querySelectorAll('.tab[data-type]').forEach(b=>{
    b.classList.toggle("active", b.dataset.type===type);
  });

  const csvFile = `data/top8_${type}.csv`;
  const res = await fetch(csvFile, { cache:"no-store" });
  const root = document.getElementById("ranking");

  if(!res.ok){
    root.innerHTML = `<div class="col"><div class="card">Could not load <strong>${csvFile}</strong>.</div></div>`;
    return;
  }

  const text = await res.text();
  const {headers, rows} = parseCSV(text);
  renderTwoColumns(type, headers, rows);
}

document.addEventListener("DOMContentLoaded", () => {
  // listeners só em tabs com data-type (evita pegar o botão ALL TRAINEES)
  document.querySelectorAll('.tab[data-type]').forEach(btn=>{
    btn.addEventListener("click", ()=> loadRanking(btn.dataset.type));
  });

  // carrega a aba padrão
  loadRanking(activeTab);
});

/* ================= All Trainees (rank + name) ================= */

let ALL_DATA_CACHE = null;

function logWarn(msg) {
  console.warn("[all-trainees]", msg);
}

async function fetchAllTrainees() {
  if (ALL_DATA_CACHE) return ALL_DATA_CACHE;

  const res = await fetch("data/all_trainees.csv", { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load data/all_trainees.csv");
  let text = await res.text();

  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

  let headers, rows;
  try {
    const parsed = parseCSV(text);
    headers = parsed.headers;
    rows   = parsed.rows;
  } catch (e) {
    console.error("CSV parse error:", e);
    throw e;
  }

  const idxName    = headers.indexOf("trainee_name");
  const idxViews   = headers.indexOf("views");
  const idxLikes   = headers.indexOf("likes");
  const idxComms   = headers.indexOf("comments");
  const idxOverall = headers.indexOf("overall_rank");
  const idxVRank   = headers.indexOf("views_rank");
  const idxLRank   = headers.indexOf("likes_rank");
  const idxCRank   = headers.indexOf("comments_rank");

  const data = rows.map(r => ({
    name: (r[idxName] ?? "").trim(),
    views: Number(r[idxViews] ?? 0),
    likes: Number(r[idxLikes] ?? 0),
    comments: Number(r[idxComms] ?? 0),
    overall: Number(r[idxOverall] ?? 0),
    views_rank: Number(r[idxVRank] ?? 0),
    likes_rank: Number(r[idxLRank] ?? 0),
    comments_rank: Number(r[idxCRank] ?? 0),
  }));

  ALL_DATA_CACHE = data;
  return data;
}

function computeRanks(arr, key) {
  if (key === "overall"  && arr.every(x => x.overall))       return arr.map(x => ({ ...x, rank: x.overall }));
  if (key === "views"    && arr.every(x => x.views_rank))    return arr.map(x => ({ ...x, rank: x.views_rank }));
  if (key === "likes"    && arr.every(x => x.likes_rank))    return arr.map(x => ({ ...x, rank: x.likes_rank }));
  if (key === "comments" && arr.every(x => x.comments_rank)) return arr.map(x => ({ ...x, rank: x.comments_rank }));

  const sorted = [...arr].sort((a,b) => (b[key]||0) - (a[key]||0));
  const rankMap = new Map();
  let lastVal = null, lastRank = 0;
  sorted.forEach((item, idx) => {
    const val = item[key] || 0;
    if (val !== lastVal) { lastVal = val; lastRank = idx + 1; }
    rankMap.set(item.name, lastRank);
  });
  return arr.map(x => ({ ...x, rank: rankMap.get(x.name) || 0 }));
}

function renderAllSimple(metric = "overall", query = "") {
  if (!ALL_DATA_CACHE) return;
  const tbody = document.querySelector("#allTable tbody");
  if (!tbody) { logWarn("tbody #allTable not found."); return; }

  const q = (query || "").toLowerCase();

  let list = computeRanks(ALL_DATA_CACHE, metric);
  list = list.filter(x => x.name.toLowerCase().includes(q));
  list.sort((a,b) => a.rank - b.rank);

  const frag = document.createDocumentFragment();
  list.forEach(row => {
    const tr = document.createElement("tr");
    const tdRank = document.createElement("td");
    tdRank.textContent = row.rank || "-";
    const tdName = document.createElement("td");
    tdName.textContent = row.name || "";
    tr.append(tdRank, tdName);
    frag.appendChild(tr);
  });

  tbody.innerHTML = "";
  tbody.appendChild(frag);
}

async function openAllModal() {
  try {
    await fetchAllTrainees();
    const metricSel = document.getElementById("allMetric");
    const searchInp = document.getElementById("allSearch");
    renderAllSimple(metricSel ? metricSel.value : "overall", searchInp ? searchInp.value : "");
    const modal = document.getElementById("allModal");
    modal && modal.classList.remove("hidden");
  } catch (e) {
    console.error(e);
    alert("Failed to load the full ranking.");
  }
}

function closeAllModal() {
  const modal = document.getElementById("allModal");
  modal && modal.classList.add("hidden");
  // não recarrega nada — mantém a aba ativa
}

// listeners da modal + botão All
document.addEventListener("DOMContentLoaded", () => {
  const btnAll     = document.getElementById("btnAll");
  const btnClose   = document.getElementById("closeAll");
  const selMetric  = document.getElementById("allMetric");
  const inpSearch  = document.getElementById("allSearch");
  const modal      = document.getElementById("allModal");

  btnAll   && btnAll.addEventListener("click", openAllModal);
  btnClose && btnClose.addEventListener("click", closeAllModal);

  // fecha clicando fora do conteúdo
  modal && modal.addEventListener("click", (ev) => {
    if (ev.target === modal) closeAllModal();
  });

  selMetric && selMetric.addEventListener("change", (e) => {
    renderAllSimple(e.target.value, inpSearch ? inpSearch.value : "");
  });

  inpSearch && inpSearch.addEventListener("input", (e) => {
    renderAllSimple(selMetric ? selMetric.value : "overall", e.target.value);
  });
});



