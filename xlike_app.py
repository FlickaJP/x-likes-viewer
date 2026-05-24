# -*- coding: utf-8 -*-
"""
X いいね ビューア アプリ 【設定・取得・表示を1ウィンドウに統合】
================================================================
事前に1回:  pip install pywebview
置き場所  :  xlike_import.py / make_viewer.py と同じフォルダ（db・media もここ）
起動      :  フォルダで cmd を開いて  python xlike_app.py

使い方:
  右上 ⚙ … APIキー(4つ)を入力して保存（初回のみ）
  ↻ いいね取得 … 新しいいいねを追加で取り込み→自動で画面更新
"""
import os
import sys

print("[1] 起動しました。準備中...")

try:
    import webview
except Exception as e:
    print("[!] pywebview が読み込めません:", e)
    print("    コマンドプロンプトで:  pip install --upgrade pywebview pythonnet")
    input("\nEnterキーを押すと閉じます。")
    sys.exit()

try:
    import make_viewer
    import xlike_import
except Exception as e:
    print("[!] make_viewer.py / xlike_import.py が読み込めません:", e)
    print("    3つの .py を同じフォルダに置いてください。")
    input("\nEnterキーを押すと閉じます。")
    sys.exit()

# 実行ファイルの場所を基準に、3つの部品が見る場所をそろえる
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

make_viewer.BASE_DIR = BASE
make_viewer.DB_PATH = os.path.join(BASE, "liked_tweets.db")
make_viewer.OUT = os.path.join(BASE, "gallery.html")
xlike_import.BASE_DIR = BASE
xlike_import.CONFIG = os.path.join(BASE, "config.json")
xlike_import.DB_PATH = os.path.join(BASE, "liked_tweets.db")
xlike_import.MEDIA_DIR = os.path.join(BASE, "media")


class Api:
    """画面(JS)から呼ばれる窓口"""

    def get_config(self):
        k = xlike_import.load_keys() or {}
        return {"api_key": k.get("api_key", ""), "api_secret": k.get("api_secret", ""),
                "access_token": k.get("access_token", ""),
                "access_token_secret": k.get("access_token_secret", "")}

    def save_config(self, api_key, api_secret, access_token, access_token_secret):
        xlike_import.save_keys({"api_key": api_key, "api_secret": api_secret,
                                "access_token": access_token,
                                "access_token_secret": access_token_secret})
        return True

    def fetch_likes(self):
        res = xlike_import.run_import(max_tweets=0)  # 増分取得
        make_viewer.main()                            # 取り込み後にHTML再生成
        return res

    def unlike_tweets(self, tweet_ids, delete_local):
        res = xlike_import.unlike_tweets(tweet_ids, delete_local=delete_local)
        make_viewer.main()  # 解除（とローカル削除）を反映してHTML再生成
        return res


def main():
    if not os.path.exists(make_viewer.DB_PATH):
        print("[2] データベースが無いので新規作成します...")
        xlike_import.init_db().close()
    print("[2] ギャラリーを生成しています...")
    make_viewer.main()
    print("[3] ウィンドウを作成しています...")
    webview.create_window(
        "いいねギャラリー", url=make_viewer.OUT, js_api=Api(),
        width=1280, height=820, background_color="#0c0c0f")
    print("[4] ウィンドウを起動します（ここでウィンドウが開きます）...")
    webview.start(http_server=True, private_mode=False)
    print("[5] ウィンドウが閉じられました。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        print("\n==== エラー内容（これをそのまま貼ってください）====")
        traceback.print_exc()
        print("================================================")
    try:
        input("\nEnterキーを押すと閉じます。")
    except Exception:
        pass  # --windowed版(黒い画面なし)では標準入力が無いので、静かに終了
