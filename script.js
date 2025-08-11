function formatNumber(n) {
  if (n === undefined || n === null || n === "") return "-";
  const num = Number(String(n).replace(/[^\d.-]/g, ""));
  if (Number.isNaN(num)) return n;
  return num.toLocaleString("pt-BR");
}

async function loadRanking(type) {
  const csvFile = `data/top8_${type}.csv`;
  const res = await fetch(csvFile, { cache: "no-store" });
  if (!res.ok) {
    document.getElementById("ranking").innerHTML = `<div class="ranking-item">Não consegui carregar ${csvFile}</div>`;
    return;
  }
  const text = await res.text();
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return;

  // cabeçalho -> índice por nome
  const headers = lines[0].split(",").map(h => h.trim());
  const idx = name => headers.indexOf(name);

  const iTrainee = idx("trainee_name") !== -1 ? idx("trainee_name") : 0;
  const iViews   = idx("views");
  const iLikes   = idx("likes");
  const iComms   = idx("comments");
  const iScore   = idx("score_norm") !== -1 ? idx("score_norm") : idx("score");

  const container = document.getElementById("ranking");
  container.innerHTML = "";

  lines.slice(1).forEach((row, i) => {
    if (!row.trim()) return;
    const cols = row.split(",");
    const trainee = cols[iTrainee] || "";
    const views = iViews !== -1 ? cols[iViews] : "";
    const likes = iLikes !== -1 ? cols[iLikes] : "";
    const comments = iComms !== -1 ? cols[iComms] : "";
    const score = iScore !== -1 ? cols[iScore] : "";

    let metric = "";
    if (type === "views")     metric = `${formatNumber(views)} views`;
    else if (type === "likes")    metric = `${formatNumber(likes)} likes`;
    else if (type === "comments") metric = `${formatNumber(comments)} comentários`;
    else metric = `Score: ${score ? Number(score).toFixed(3) : "-"}`;

    const item = document.createElement("div");
    item.className = "ranking-item";
    item.innerHTML = `<strong>#${i + 1}</strong> ${trainee} <br/> ${metric}`;
    container.appendChild(item);
  });
}

// carrega um ranking por padrão
document.addEventListener("DOMContentLoaded", () => loadRanking("views"));
