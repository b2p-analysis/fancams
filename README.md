# BOYS II PLANET — Fancam Ranker (YouTube Data API)

Script em Python para coletar **views, likes e comentários** dos vídeos publicados no **dia 04 de agosto** (ou qualquer data) em um canal do YouTube e gerar TOP 8 por métrica e um ranking **geral** (ponderado).

## ⚙️ Pré‑requisitos
1. Python 3.9+
2. Crie uma **API Key** no Google Cloud:
   - Console: https://console.cloud.google.com/
   - Crie um projeto → **Enable APIs & Services** → ative **YouTube Data API v3**.
   - Em **APIs & Services → Credentials**, crie uma **API key** (e restrinja por IP se quiser).

## 📦 Instalação
```bash
pip install -r requirements.txt
```

## ▶️ Como rodar
Substitua `YOUR_API_KEY` pela sua chave:

```bash
python youtube_fancam_ranker.py --api-key YOUR_API_KEY   --handle @BOYSPLANET.OFFICIAL   --date 2025-08-04   --tz America/Sao_Paulo   --out data
```

### Opções úteis
- `--weights 1 1 1` → pesos (views likes comentários) para o ranking **geral**.
- `--title-filter fancam` → filtra só vídeos cujo título contenha o termo (ex.: "fancam" ou "직캠").
- `--append-history` → salva um **histórico** com timestamp para acompanhar evolução.

## 📁 Saídas (na pasta `data/`)
- `YYYY-MM-DD_raw.csv` → dados completos
- `top8_views.csv`, `top8_likes.csv`, `top8_comments.csv`, `top8_overall.csv`
- `history.csv` (se usar `--append-history`)

## ⏱️ Agendamento (opcional)
- **Windows**: Task Scheduler → crie uma tarefa para rodar o comando acima 1x/dia.
- **Mac/Linux**: `crontab -e` → `0 9 * * * /usr/bin/python3 /caminho/youtube_fancam_ranker.py ...`

## 📌 Observações
- O filtro de data usa **sua timezone** para montar a janela UTC correta do dia.
- A API tem limites de cota; este script consome pouco (uma busca + 1-2 chamadas `videos.list`).
- `commentCount` inclui comentários **e** respostas.
