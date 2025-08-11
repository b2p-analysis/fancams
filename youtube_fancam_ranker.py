
import argparse
import os
import sys
import datetime as dt
from zoneinfo import ZoneInfo
from typing import List, Tuple

import pandas as pd
from dateutil import parser as dateparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def build_youtube(api_key: str):
    return build("youtube", "v3", developerKey=api_key)

def get_channel_id(youtube, handle: str) -> Tuple[str, dict]:
    handle = handle.lstrip("@")
    resp = youtube.channels().list(part="id,contentDetails,snippet", forHandle=handle).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"Nenhum canal encontrado para handle '@{handle}'. Verifique se está correto.")
    channel = items[0]
    return channel["id"], channel

def iso_window_for_local_date(date_str: str, tz_name: str) -> Tuple[str, str]:
    tz = ZoneInfo(tz_name)
    d = dt.date.fromisoformat(date_str)
    start_local = dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)
    start_utc = start_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return start_utc, end_utc

def list_video_ids_by_date(youtube, channel_id: str, start_iso_utc: str, end_iso_utc: str) -> List[str]:
    ids = []
    page_token = None
    while True:
        req = youtube.search().list(
            part="id",
            channelId=channel_id,
            type="video",
            maxResults=50,
            order="date",
            publishedAfter=start_iso_utc,
            publishedBefore=end_iso_utc,
            pageToken=page_token,
        )
        resp = req.execute()
        for it in resp.get("items", []):
            if it["id"]["kind"] == "youtube#video":
                ids.append(it["id"]["videoId"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids

def extract_trainee_name(title: str) -> str:
    """
    Extrai o nome do trainee a partir do título no formato:
    [BOYS ll PLANET/4회 직캠] NOME TRAINEE ♬Música ...
    """
    try:
        # Remove prefixo antes de ]
        if "]" in title:
            title = title.split("]", 1)[1].strip()
        # Nome vem antes do símbolo ♬
        if "♬" in title:
            name_part = title.split("♬", 1)[0].strip()
        else:
            name_part = title.strip()
        return name_part
    except Exception:
        return title

def fetch_video_details(youtube, video_ids: List[str]) -> pd.DataFrame:
    rows = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        resp = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(chunk)
        ).execute()
        for item in resp.get("items", []):
            stats = item.get("statistics", {})
            snip = item.get("snippet", {})
            title = snip.get("title", "")
            rows.append({
                "videoId": item["id"],
                "title": title,
                "trainee_name": extract_trainee_name(title),
                "publishedAt": snip.get("publishedAt"),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })
    return pd.DataFrame(rows)

def add_ranks_and_scores(df: pd.DataFrame, weights: Tuple[float, float, float]) -> pd.DataFrame:
    if df.empty:
        return df
    for col in ["views", "likes", "comments"]:
        df[f"{col}_rank"] = df[col].rank(method="min", ascending=False).astype(int)
    # Min-max normalization
    for col in ["views", "likes", "comments"]:
        minv, maxv = df[col].min(), df[col].max()
        if maxv > minv:
            df[f"{col}_norm"] = (df[col] - minv) / (maxv - minv)
        else:
            df[f"{col}_norm"] = 0.0
    wv, wl, wc = weights
    total_w = max(wv + wl + wc, 1e-9)
    df["score"] = wv * df["views_norm"] + wl * df["likes_norm"] + wc * df["comments_norm"]
    df["score_norm"] = df["score"] / total_w
    df["overall_rank"] = df["score_norm"].rank(method="min", ascending=False).astype(int)
    return df

def save_outputs(df_raw: pd.DataFrame, df_grouped: pd.DataFrame, out_dir: str, date_str: str, append_history: bool):
    os.makedirs(out_dir, exist_ok=True)
    # Raw
    df_raw.to_csv(os.path.join(out_dir, f"{date_str}_raw.csv"), index=False)
    # Grouped
    df_grouped.to_csv(os.path.join(out_dir, f"{date_str}_grouped.csv"), index=False)
    # Top 8s
    df_grouped.sort_values("views", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_views.csv"), index=False)
    df_grouped.sort_values("likes", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_likes.csv"), index=False)
    df_grouped.sort_values("comments", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_comments.csv"), index=False)
    df_grouped.sort_values(["overall_rank", "score_norm"], ascending=[True, False]).head(8).to_csv(os.path.join(out_dir, "top8_overall.csv"), index=False)
    if append_history:
        hist_path = os.path.join(out_dir, "history.csv")
        snapshot = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        df_hist = df_grouped.copy()
        df_hist.insert(0, "snapshot_time_utc", snapshot)
        if os.path.exists(hist_path):
            df_hist.to_csv(hist_path, mode="a", header=False, index=False)
        else:
            df_hist.to_csv(hist_path, index=False)
    print(f"\nArquivos salvos em: {os.path.abspath(out_dir)}")
import argparse
import os
import sys
import datetime as dt
from zoneinfo import ZoneInfo
from typing import List, Tuple

import pandas as pd
from dateutil import parser as dateparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ---------------- YouTube helpers ----------------

def build_youtube(api_key: str):
    return build("youtube", "v3", developerKey=api_key)

def get_channel_id(youtube, handle: str) -> Tuple[str, dict]:
    handle = handle.lstrip("@")
    resp = youtube.channels().list(part="id,contentDetails,snippet", forHandle=handle).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"Nenhum canal encontrado para handle '@{handle}'. Verifique se está correto.")
    channel = items[0]
    return channel["id"], channel


# ---------------- Date window helpers ----------------

def iso_window_for_local_range(start_date_str: str, end_date_str: str | None, tz_name: str) -> Tuple[str, str]:
    """
    Converte um intervalo local [start_date, end_date] para janelas UTC:
    - start_date às 00:00:00 (inclusive)
    - end_date + 1 dia às 00:00:00 (exclusivo). Se end_date for None, usa hoje.
    """
    tz = ZoneInfo(tz_name)
    start_d = dt.date.fromisoformat(start_date_str)

    if end_date_str:
        end_d = dt.date.fromisoformat(end_date_str)
    else:
        end_d = dt.datetime.now(tz=tz).date()

    start_local = dt.datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=tz)
    end_local = dt.datetime(end_d.year, end_d.month, end_d.day, 0, 0, 0, tzinfo=tz) + dt.timedelta(days=1)

    start_utc = start_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return start_utc, end_utc


# ---------------- Search / fetch ----------------

def list_video_ids_in_range(youtube, channel_id: str, start_iso_utc: str, end_iso_utc: str) -> List[str]:
    """
    Busca IDs de vídeos publicados no canal entre start/end (UTC), paginando tudo.
    """
    ids: List[str] = []
    page_token = None
    while True:
        req = youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            type="video",
            maxResults=50,
            order="date",
            publishedAfter=start_iso_utc,
            publishedBefore=end_iso_utc,
            pageToken=page_token,
        )
        resp = req.execute()
        for it in resp.get("items", []):
            if it["id"]["kind"] == "youtube#video":
                ids.append(it["id"]["videoId"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids

def fetch_video_details(youtube, video_ids: List[str]) -> pd.DataFrame:
    rows = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        resp = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(chunk)
        ).execute()
        for item in resp.get("items", []):
            stats = item.get("statistics", {})
            snip = item.get("snippet", {})
            title = snip.get("title", "")
            rows.append({
                "videoId": item["id"],
                "title": title,
                "publishedAt": snip.get("publishedAt"),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })
    return pd.DataFrame(rows)


# ---------------- Title parsing & filter ----------------

FANCAM_KEYWORDS_DEFAULT = [
    "직캠",          # fancam (coreano)
    "fancam",       # inglês
    "팬캠",          # outra variação em coreano
    "個人直拍",       # chinês tradicional (opcional)
    "直拍",          # chinês simplificado
]

def looks_like_fancam(title: str, include: list[str] | None) -> bool:
    """
    Retorna True se o título aparenta ser fancam.
    - Usa palavras-chave (case-insensitive) em qualquer idioma.
    - Você pode passar --include "palavra1|palavra2" para forçar um regex personalizado.
    """
    t = title.lower()
    if include:
        for kw in include:
            if kw.lower() in t:
                return True
        return False
    # default heurística
    for kw in FANCAM_KEYWORDS_DEFAULT:
        if kw.lower() in t:
            return True
    return False

def extract_trainee_name(title: str) -> str:
    """
    Extrai o nome do trainee a partir do título.
    Exemplo de formato:
    [BOYS ll PLANET/4회 직캠] NOME TRAINEE ♬Música - ...
    Regra simples:
      - corta tudo até ']' (inclusive)
      - corta no '♬' se existir
    """
    try:
        if "]" in title:
            title = title.split("]", 1)[1].strip()
        if "♬" in title:
            name_part = title.split("♬", 1)[0].strip()
        else:
            name_part = title.strip()
        return name_part
    except Exception:
        return title


# ---------------- Ranking helpers ----------------

def add_ranks_and_scores(df: pd.DataFrame, weights: Tuple[float, float, float]) -> pd.DataFrame:
    if df.empty:
        return df
    for col in ["views", "likes", "comments"]:
        df[f"{col}_rank"] = df[col].rank(method="min", ascending=False).astype(int)

    # min-max normalization
    for col in ["views", "likes", "comments"]:
        minv, maxv = df[col].min(), df[col].max()
        if maxv > minv:
            df[f"{col}_norm"] = (df[col] - minv) / (maxv - minv)
        else:
            df[f"{col}_norm"] = 0.0

    wv, wl, wc = weights
    total_w = max(wv + wl + wc, 1e-9)
    df["score"] = wv * df["views_norm"] + wl * df["likes_norm"] + wc * df["comments_norm"]
    df["score_norm"] = df["score"] / total_w
    df["overall_rank"] = df["score_norm"].rank(method="min", ascending=False).astype(int)
    return df


# ---------------- Save helpers ----------------

def save_outputs(df_raw: pd.DataFrame, df_grouped: pd.DataFrame, out_dir: str, tag: str, append_history: bool):
    os.makedirs(out_dir, exist_ok=True)

    df_raw.to_csv(os.path.join(out_dir, f"{tag}_raw.csv"), index=False)
    df_grouped.to_csv(os.path.join(out_dir, f"{tag}_grouped.csv"), index=False)

    df_grouped.sort_values("views", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_views.csv"), index=False)
    df_grouped.sort_values("likes", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_likes.csv"), index=False)
    df_grouped.sort_values("comments", ascending=False).head(8).to_csv(os.path.join(out_dir, "top8_comments.csv"), index=False)
    df_grouped.sort_values(["overall_rank", "score_norm"], ascending=[True, False]).head(8).to_csv(os.path.join(out_dir, "top8_overall.csv"), index=False)

    if append_history:
        hist_path = os.path.join(out_dir, "history.csv")
        snapshot = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        df_hist = df_grouped.copy()
        df_hist.insert(0, "snapshot_time_utc", snapshot)
        if os.path.exists(hist_path):
            df_hist.to_csv(hist_path, mode="a", header=False, index=False)
        else:
            df_hist.to_csv(hist_path, index=False)


# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser(description="Coleta fancams por intervalo e gera ranking por trainee.")
    ap.add_argument("--api-key", required=True, help="YouTube Data API v3 key")
    ap.add_argument("--handle", default="@BOYSPLANET.OFFICIAL", help="Handle do canal")
    ap.add_argument("--start-date", required=True, help="Data inicial local (YYYY-MM-DD)")
    ap.add_argument("--end-date", default=None, help="Data final local (YYYY-MM-DD). Se omitida, usa hoje.")
    ap.add_argument("--tz", default="America/Sao_Paulo", help="Timezone local para a janela de datas")
    ap.add_argument("--weights", nargs=3, type=float, default=[1.0, 1.0, 1.0], help="Pesos para views likes comentários")
    ap.add_argument("--out", default="data", help="Pasta de saída")
    ap.add_argument("--append-history", action="store_true", help="Adicionar histórico")
    ap.add_argument("--include", default=None, help="Palavras-chave (separadas por '|') para forçar filtro por título (ex.: '직캠|fancam')")
    args = ap.parse_args()

    try:
        yt = build_youtube(args.api_key)
        channel_id, channel = get_channel_id(yt, args.handle)

        start_iso, end_iso = iso_window_for_local_range(args.start_date, args.end_date, args.tz)
        print(f"Canal: {channel.get('snippet', {}).get('title')} (ID: {channel_id})")
        print(f"Janela UTC: {start_iso} → {end_iso} (equivalente a {args.start_date}..{args.end_date or 'hoje'} em {args.tz})")

        video_ids = list_video_ids_in_range(yt, channel_id, start_iso, end_iso)
        if not video_ids:
            print("Nenhum vídeo encontrado no intervalo.")
            sys.exit(0)

        df_raw_all = fetch_video_details(yt, video_ids)
        if df_raw_all.empty:
            print("Vídeos encontrados, mas sem detalhes.")
            sys.exit(0)

        # filtro de fancam por título
        include_list = args.include.split("|") if args.include else None
        mask = df_raw_all["title"].apply(lambda t: looks_like_fancam(t or "", include_list))
        df_raw = df_raw_all[mask].copy()

        if df_raw.empty:
            print("Nenhum vídeo parece ser fancam pelo filtro de título. Ajuste --include (ex.: '직캠|fancam').")
            sys.exit(0)

        # extrai trainee
        df_raw["trainee_name"] = df_raw["title"].apply(extract_trainee_name)

        # agrupa por trainee
        df_grouped = df_raw.groupby("trainee_name").agg({
            "views": "sum",
            "likes": "sum",
            "comments": "sum",
            "url": "first"
        }).reset_index()

        # ranks e score
        df_grouped = add_ranks_and_scores(df_grouped, tuple(args.weights))
        df_grouped = df_grouped.sort_values(["overall_rank", "score_norm"], ascending=[True, False])

        # tag de saída baseada no intervalo
        tag = f"{args.start_date}_to_{args.end_date or dt.date.today().isoformat()}"
        save_outputs(df_raw, df_grouped, args.out, tag, args.append_history)

        print("\nTOP 8 (Geral):")
        print(df_grouped.head(8)[["overall_rank", "trainee_name", "views", "likes", "comments", "url"]].to_string(index=False))

    except HttpError as e:
        print("\n[YouTube API Error]", e)
        sys.exit(1)
    except Exception as e:
        print("\n[Erro]", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

