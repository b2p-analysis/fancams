
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

def main():
    ap = argparse.ArgumentParser(description="Coleta fancams e gera ranking por trainee.")
    ap.add_argument("--api-key", required=True, help="YouTube Data API v3 key")
    ap.add_argument("--handle", default="@BOYSPLANET.OFFICIAL", help="Handle do canal")
    ap.add_argument("--date", required=True, help="Data local YYYY-MM-DD")
    ap.add_argument("--tz", default="America/Sao_Paulo", help="Timezone local")
    ap.add_argument("--weights", nargs=3, type=float, default=[1.0, 1.0, 1.0], help="Pesos para views likes comentários")
    ap.add_argument("--out", default="data", help="Pasta de saída")
    ap.add_argument("--append-history", action="store_true", help="Adicionar histórico")
    args = ap.parse_args()

    try:
        yt = build_youtube(args.api_key)
        channel_id, channel = get_channel_id(yt, args.handle)
        start_iso, end_iso = iso_window_for_local_date(args.date, args.tz)
        print(f"Canal: {channel.get('snippet', {}).get('title')} (ID: {channel_id})")
        print(f"Janela UTC: {start_iso} → {end_iso}")

        video_ids = list_video_ids_by_date(yt, channel_id, start_iso, end_iso)
        if not video_ids:
            print("Nenhum vídeo encontrado nessa data.")
            sys.exit(0)

        df_raw = fetch_video_details(yt, video_ids)
        if df_raw.empty:
            print("Vídeos encontrados, mas não há dados.")
            sys.exit(0)

        # Agrupa por trainee
        df_grouped = df_raw.groupby("trainee_name").agg({
            "views": "sum",
            "likes": "sum",
            "comments": "sum",
            "url": "first"
        }).reset_index()

        # Ranks e scores
        df_grouped = add_ranks_and_scores(df_grouped, tuple(args.weights))

        # Ordena
        df_grouped = df_grouped.sort_values(["overall_rank", "score_norm"], ascending=[True, False])

        save_outputs(df_raw, df_grouped, args.out, args.date, args.append_history)

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
