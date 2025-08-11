// ============ Config ============

// pasta das imagens
const IMG_DIR = "images/";

// Mapeie aqui se quiser garantir nomes específicos.
// Use APENAS a parte em inglês do nome (fica mais estável).
// O restante é resolvido automaticamente por fallback.
const imageMap = {
  "LEE LEO": "leeleo.png",
  "CHUEI LI YU": "chueliyu.png",
  "KANG WOO JIN": "kangwoojin.png",

  "LEE SANG WON": "leesangwon.png",
  "YUMEKI": "yumeki.png",
  "ZHOU AN XIN": "zhouanxin.png",
  "KIM GEON WOO": "kimgeonwoo.png",
  "KIM JUN SEO": "kimjunseo.png",
  "CHUNG SANG HYEON": "changsunghyeon.png" // se seu arquivo for changsunghyeon.png, ajuste aqui
  // Ex.: "CHUNG SANG HYEON": "changsunghyeon.png",
};

// ============ Helpers ============

function formatNumber(n){
  if(n===undefined||n===null||n==="") return "-";
  const num = Number(String(n).replace(/[^\d.-]/g, ""));
  if(Number.isNaN(num)) return n;
  return num.toLocaleString("en-US");
}

// Faz um "slug" seguro
function slugify(str){
  return String(str)
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .replace(/[^a-zA-Z0-9]+/g,"-")
    .replace(/^-+|-+$/g,"")
    .toLowerCase();
}

// Remove tudo que não é [a-z0-9]
function tightSlug(str){
  return String(str)
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g,"");
}

// Extrai a parte em inglês de "이름 NAME SURNAME"
function getEnglishName(fullName){
  const m = fullName.match(/[A-Za-z].*$/);
  return (m ? m[0] : "").trim();
}

// Estratégia robusta para encontrar a imagem
function getImageUrl(fullName){
  const english = getEnglishName(fullName);        // ex.: "LEE LEO"
  const englishLower = english.toLowerCase();      // "lee leo"
  const englishTight = tightSlug(english);         // "leeleo"
  const englishHyphen = slugify(english);          // "lee-leo"

  const fullTight = tightSlug(fullName);           // tudo junto do nome inteiro

  // 1) Mapeamento direto por inglês
  if (english && imageMap[english]) return IMG_DIR + imageMap[english];

  // 2) Fallbacks automáticos em ordem:
  //    a) inglês sem espaços/hífens -> leeleo.png
  //    b) inglês com hífens -> lee-leo.png
  //    c) tight do nome completo -> (último recurso)
  const candidates = [
    `${IMG_DIR}${englishTight}.png`,
    `${IMG_DIR}${englishHyphen}.png`,
    `${IMG_DIR}${fullTight}.png`,
  ];

  // retornamos o primeiro candidato; se não existir, onerror cai em placeholder
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

  const iName = idx(headers,"trainee_name",0);
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

async function loadRanking(type){
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active", b.dataset.type===type));

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
  document.querySelectorAll(".tab").forEach(btn=>{
    btn.addEventListener("click", ()=> loadRanking(btn.dataset.type));
  });
  loadRanking("views"); // default
});




