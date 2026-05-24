# -*- coding: utf-8 -*-
"""
X いいね取り込みエンジン（自動待機・再開対応版）
================================================================
  - CLI:        python xlike_import.py
  - アプリから: run_import() を呼ぶ
レート制限に当たったら自動で待機して継続。途中で止めても続きから再開。
"""
import os
import sys
import json
import time
import sqlite3
import subprocess


def _ensure(pkg):
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

_ensure("tweepy")
_ensure("requests")
import tweepy
import requests

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG    = os.path.join(BASE_DIR, "config.json")
DB_PATH   = os.path.join(BASE_DIR, "liked_tweets.db")
MEDIA_DIR = os.path.join(BASE_DIR, "media")


def load_keys():
    if os.path.exists(CONFIG):
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_keys(keys):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(keys, f)


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS tweets(tweet_id TEXT PRIMARY KEY,
        author_username TEXT, author_name TEXT, text TEXT, created_at TEXT,
        liked_rank INTEGER, fetched_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS media(tweet_id TEXT, media_key TEXT,
        type TEXT, source_url TEXT, local_path TEXT, PRIMARY KEY(tweet_id, media_key))""")
    con.execute("CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT)")
    con.commit()
    return con


def get_state(con, key, default=None):
    row = con.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_state(con, key, value):
    con.execute("INSERT INTO state(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    con.commit()


def orig_photo_url(url):
    if "pbs.twimg.com" not in url:
        return url
    base = url.split("?")[0]
    fname = base.split("/")[-1]
    if "." in fname:
        ext = fname.rsplit(".", 1)[1]
        return f"{base.rsplit('.',1)[0]}?format={ext}&name=orig"
    return base + "?name=orig"


def best_video_url(variants):
    if not variants:
        return None
    mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
    if not mp4s:
        return None
    mp4s.sort(key=lambda v: v.get("bit_rate", 0), reverse=True)
    return mp4s[0]["url"]


def download(url, path):
    r = requests.get(url, timeout=90, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def run_import(max_tweets=0, log=print):
    """増分取り込み。レート制限は自動待機。戻り値: {'new','media','total'}"""
    keys = load_keys()
    if not keys:
        raise RuntimeError("APIキーが未設定です。先に設定してください。")
    # wait_on_rate_limit=True : 429になったらリセット時刻まで自動で待って継続
    client = tweepy.Client(
        consumer_key=keys["api_key"], consumer_secret=keys["api_secret"],
        access_token=keys["access_token"], access_token_secret=keys["access_token_secret"],
        wait_on_rate_limit=True)

    os.makedirs(MEDIA_DIR, exist_ok=True)
    con = init_db()
    user_id = client.get_me(user_auth=True).data.id

    full_done = get_state(con, "full_done") == "1"
    mode = "update" if full_done else "full"
    log(f"モード: {'増分(新着のみ)' if mode=='update' else '初回フル取得'}")
    if mode == "full":
        log("※ 制限に当たると自動で待機します（画面が止まって見えても正常です。最大15分ほど待つことがあります）")

    existing = set(r[0] for r in con.execute("SELECT tweet_id FROM tweets"))
    saved_media = set((r[0], r[1]) for r in con.execute("SELECT tweet_id, media_key FROM media"))
    rank = con.execute("SELECT COALESCE(MAX(liked_rank),0) FROM tweets").fetchone()[0]
    new_count = media_count = pages = 0
    newly_added = []

    # フル取得は前回の続き(保存トークン)から。増分は常に最新から。
    pagination_token = None
    if mode == "full":
        saved_tok = get_state(con, "page_token")
        pagination_token = saved_tok if saved_tok else None
        if pagination_token:
            log("前回の続きから再開します。")
    stop = False

    while not stop:
        resp = client.get_liked_tweets(
            user_id, max_results=100, pagination_token=pagination_token,
            expansions=["attachments.media_keys", "author_id"],
            media_fields=["url", "variants", "type", "preview_image_url"],
            user_fields=["username", "name"], tweet_fields=["created_at"], user_auth=True)
        if not resp.data:
            if mode == "full":
                set_state(con, "full_done", "1"); set_state(con, "page_token", "")
            break
        pages += 1
        users = {u.id: u for u in (resp.includes.get("users") or [])}
        media = {m.media_key: m for m in (resp.includes.get("media") or [])}

        for tw in resp.data:
            if str(tw.id) in existing:
                if mode == "update":
                    stop = True
                    break
                continue
            if max_tweets and new_count >= max_tweets:
                stop = True
                break
            au = users.get(tw.author_id)
            rank += 1
            con.execute("INSERT OR IGNORE INTO tweets VALUES(?,?,?,?,?,?,?)",
                (str(tw.id), getattr(au, "username", None), getattr(au, "name", None),
                 tw.text, str(tw.created_at) if tw.created_at else None, rank,
                 time.strftime("%Y-%m-%d %H:%M:%S")))
            existing.add(str(tw.id))
            newly_added.append(str(tw.id))
            new_count += 1
            mkeys = (tw.attachments or {}).get("media_keys", []) if tw.attachments else []
            for i, mk in enumerate(mkeys):
                mobj = media.get(mk)
                if not mobj or (str(tw.id), mk) in saved_media:
                    continue
                if mobj.type == "photo":
                    src, ext = orig_photo_url(mobj.url), "jpg"
                else:
                    src, ext = best_video_url(getattr(mobj, "variants", None)), "mp4"
                if not src:
                    continue
                fname = f"{tw.id}_{i}.{ext}"
                try:
                    download(src, os.path.join(MEDIA_DIR, fname))
                    con.execute("INSERT OR IGNORE INTO media VALUES(?,?,?,?,?)",
                        (str(tw.id), mk, mobj.type, src, fname))
                    saved_media.add((str(tw.id), mk))
                    media_count += 1
                except Exception as de:
                    log(f"  (メディアDL失敗 {tw.id}: {de})")
        con.commit()
        log(f"ページ{pages}: 新規{new_count}件 / メディア{media_count}個（DB合計 約{len(existing)}件）")
        pagination_token = (resp.meta or {}).get("next_token")
        if mode == "full":
            set_state(con, "page_token", pagination_token or "")
        if not pagination_token:
            if mode == "full":
                set_state(con, "full_done", "1"); set_state(con, "page_token", "")
            break
        time.sleep(1.0)

    # 増分で取得した新着は「最新のいいね」なので、番号を振り直して先頭(新しい側)に置く
    if mode == "update" and newly_added:
        k = len(newly_added)
        con.execute("UPDATE tweets SET liked_rank = liked_rank + ?", (k,))
        for idx, tid in enumerate(newly_added):  # newly_added は最新順
            con.execute("UPDATE tweets SET liked_rank=? WHERE tweet_id=?", (idx + 1, tid))
        con.commit()
        log(f"新着 {k} 件を最新として並べ直しました")
    total = con.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
    con.close()
    return {"new": new_count, "media": media_count, "total": total}


def unlike_tweets(tweet_ids, delete_local=False, log=print):
    """指定IDのいいねをX本体から解除。delete_local=True なら手元のDB・画像も削除。
    戻り値: {'done':成功数,'failed':失敗数,'total':対象数}"""
    keys = load_keys()
    if not keys:
        raise RuntimeError("APIキーが未設定です。")
    client = tweepy.Client(
        consumer_key=keys["api_key"], consumer_secret=keys["api_secret"],
        access_token=keys["access_token"], access_token_secret=keys["access_token_secret"],
        wait_on_rate_limit=True)
    con = init_db()
    done = failed = 0
    total = len(tweet_ids)
    for tid in tweet_ids:
        tid = str(tid)
        try:
            client.unlike(tid, user_auth=True)
            done += 1
            if delete_local:
                for r in con.execute("SELECT local_path FROM media WHERE tweet_id=?", (tid,)).fetchall():
                    p = os.path.join(MEDIA_DIR, r[0])
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                con.execute("DELETE FROM media WHERE tweet_id=?", (tid,))
                con.execute("DELETE FROM tweets WHERE tweet_id=?", (tid,))
                con.commit()
            log(f"解除 {done}/{total}")
            time.sleep(1.5)
        except Exception as e:
            failed += 1
            log(f"解除失敗 {tid}: {type(e).__name__} {e}")
    con.close()
    return {"done": done, "failed": failed, "total": total}


def main():
    keys = load_keys()
    if not keys:
        print("初回設定: 4つの鍵を順番に貼り付けてください。\n")
        keys = {"api_key": input("  API Key             > ").strip(),
                "api_secret": input("  API Key Secret      > ").strip(),
                "access_token": input("  Access Token        > ").strip(),
                "access_token_secret": input("  Access Token Secret > ").strip()}
        save_keys(keys)
    raw = input("\n取得上限（テストなら300、全部なら0）> ").strip()
    res = run_import(int(raw) if raw.isdigit() else 0)
    print(f"\n完了: 新規{res['new']}件 / メディア{res['media']}個 / 合計{res['total']}件")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[エラー] {type(e).__name__}: {e}")
    input("\n（Enterで閉じます）")
