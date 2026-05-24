# exe化の手順メモ（Windows用）

アプリ（python xlike_app.py）が完成して動作確認できたら、以下で .exe にまとめます。
exeにするとPython本体と必要な部品が同梱され、使う人はインストール不要で起動できます。

## 0. 準備（一度だけ）
コマンドプロンプトで:
    pip install pyinstaller

## 1. まずは動作確認用ビルド（黒い画面つき = --console）
F:\X\ で cmd を開いて:
    pyinstaller --onefile --console --name XLikeViewer xlike_app.py

- 完了すると dist\XLikeViewer.exe ができます。
- この exe を F:\X\ に置いて（db・media・config.json と同じ場所）、実行して動作確認。
- 黒い画面つきなので、エラーや進捗が見えてデバッグしやすいです。
- ※ make_viewer.py と xlike_import.py は import 経由で自動的に取り込まれます
  （同じフォルダに置いた状態でビルドすればOK）。

## 2. 問題なければ完成版ビルド（黒い画面なし = --windowed）
    pyinstaller --onefile --windowed --name XLikeViewer xlike_app.py

- アプリらしく黒い画面が出なくなります。
- ※注意: --windowed にすると取り込み中の進捗（ページ◯◯）が見えなくなります。
  進捗をアプリ画面内に表示する改良を入れてからこちらにするのがおすすめです。

## 3. アイコンを付けたい場合（任意）
app.ico を用意して:
    pyinstaller --onefile --windowed --icon=app.ico --name XLikeViewer xlike_app.py

## つまずいたときのメモ
- ビルドは初回ほど時間がかかります。気長に待ってください。
- --windowed で起動しない/すぐ閉じる場合は、まず --console 版で
  エラーメッセージを確認してください。
- pywebview の隠れた部品が足りずにこけることがあります。その場合は
  エラー文を控えて相談してください（--hidden-import などで対処できます）。
- できあがった exe は、ウイルス対策ソフトに誤検知されることがあります（無害です）。
  公開する場合は README に一言添えると親切です。

## 公開フォルダの中身（GitHubに置くもの）
    xlike_app.py
    make_viewer.py
    xlike_import.py
    requirements.txt
    .gitignore
    README.md        ← 機能が固まってから作成
    LICENSE          ← MIT など
    config.example.json  ← キーの見本（中身は空欄）

※ config.json / liked_tweets.db / media / dist / build は
  .gitignore で除外されるので公開されません。
