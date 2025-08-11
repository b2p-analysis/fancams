async function loadRanking(type) {
  const csvFile = `data/top8_${type}.csv`;
  const response = await fetch(csvFile);
  const data = await response.text();

  const rows = data.split("\n").slice(1); // Remove o cabeçalho
  const container = document.getElementById("ranking");
  container.innerHTML = "";

  rows.forEach((row, index) => {
    if (!row.trim()) return;
    const cols = row.split(",");
    const trainee = cols[0];
    const views = cols[1];
    const likes = cols[2];
    const comments = cols[3];

    let metric = "";
    if (type === "views") metric = `${views} views`;
    if (type === "likes") metric = `${likes} likes`;
    if (type === "comments") metric = `${comments} comentários`;
    if (type === "overall") metric = `Score: ${cols[4]}`;

    const item = document.createElement("div");
    item.classList.add("ranking-item");
    item.innerHTML = `<strong>#${index + 1}</strong> ${trainee} - ${metric}`;
    container.appendChild(item);
  });
}
