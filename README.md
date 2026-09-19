# Weather Notify

Weather Notify は、Windows PC 上で現在地や指定地点の天気を確認し、気温・湿度の条件を満たしたタイミングで通知するデスクトップアプリです。

個人利用から発展させたポートフォリオ作品で、**「外気温が下がったら窓を開けたい」「エアコンを切る判断をしたい」**といった日常の判断を、天気データと通知で補助することを目的にしています。

> このプロジェクトは Weathernews / ウェザーニュース社とは無関係です。Weathernews のデータは使用していません。

## 主な機能

- 現在地または検索した地点の天気表示
  - 気温
  - 湿度
  - 降水確率
  - 天気
  - 風速
- 18時間先までの時間別予報を横スクロール表示
- 複数地点の監視
- 気温の「○℃以上 / ○℃以下」通知
- 任意の湿度条件をAND条件として追加
- 条件外 → 条件内になった瞬間だけ通知
- 通知連打を防ぐヒステリシス
  - 気温: 1℃
  - 湿度: 5ポイント
- Windows通知に地点・気温・湿度・降水確率・天気・風速を表示
- 「睡眠中の窓開け判定」
  - 1〜12時間先の予報をまとめて評価
  - 気温・湿度・雨・降水確率・風速から、気象条件として窓を開けやすいかを表示
- Windows位置情報から現在地を取得
- 住所検索 / 逆ジオコーディング
- 天気に合わせて変化するリアル背景 + 軽量アニメーション
- タスクトレイ常駐
- 5分ごとの自動更新 + 手動更新
- Setup.exe によるWindowsインストール

  <img width="1916" height="1026" alt="image" src="https://github.com/user-attachments/assets/6095f596-ca19-4162-86fc-e409dc25452d" />


## 技術的なポイント

この作品では、単純なAPI表示だけでなく、Windowsアプリとして継続利用できる構成を意識しています。

- **Python / PySide6** によるデスクトップGUI
- **Requests** を利用した気象API・ジオコーディングAPI通信
- **QThreadPool / QRunnable** によるUIを止めない非同期更新
- **QTimer** による5分周期の監視
- **状態機械 + ヒステリシス** による通知連打防止
- **JSON永続化** による監視設定・条件状態の保持
- **Windows位置情報** と緯度経度ベースの天気取得
- **QPainter** を使った雨・雪・霧・雷などの背景アニメーション
- **PyInstaller** による単体EXE化
- **Inno Setup** による配布用Setup.exe作成

### 通知判定の例

`30℃以上` の監視では、30℃以上になった瞬間に通知し、その後29℃以下になるまで条件内として扱います。

```text
29.8℃  条件外
30.1℃  条件内 → 通知
30.5℃  条件内 → 通知しない
29.4℃  条件内
29.0℃  条件外へ戻る
30.0℃  条件内 → 再通知
```

湿度条件を有効にした場合は、気温条件と湿度条件の両方を満たしたときに通知します。

## インストールして使う

GitHub Releases から最新版の `WeatherNotify_Setup_vX.X.X.exe` を取得して実行します。

配布用Setupには実行に必要なPython環境を含めているため、**利用者側でPythonをインストールする必要はありません**。

初回インストールでは監視設定は空の状態から始まります。更新インストールでは、同じWindowsユーザーの既存設定を引き継ぎます。

## 開発用実行

Windows版Python 3.11以上を用意し、`run.bat` を実行します。

初回に `.venv` を作成し、必要なPythonパッケージをインストールします。

手動の場合:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## ビルド

### EXE

```text
build_exe.bat
```

生成先:

```text
dist\WeatherNotify.exe
```

### 配布用Setup

Inno Setupをインストールした開発PCで:

```text
build_setup.bat
```

生成先:

```text
dist_setup\WeatherNotify_Setup_v0.1.21.exe
```

## データ保存

設定はWindowsユーザーごとに次の場所へ保存します。

```text
%USERPROFILE%\.weather_notify\settings.json
```

アプリ本体とは別に保存するため、アプリを更新しても設定を引き継げます。

## データ提供元 / クレジット

- Weather data: **Open-Meteo** — weather data under CC BY 4.0
  - https://open-meteo.com/
  - https://open-meteo.com/en/terms
- Address search / reverse geocoding: **Nominatim / OpenStreetMap**
  - © OpenStreetMap contributors
  - OpenStreetMap data is available under the Open Database License (ODbL)
  - https://www.openstreetmap.org/copyright
- GUI framework: **Qt for Python / PySide6**
  - Qt is available under LGPLv3/GPLv3 or commercial licensing depending on use
  - https://doc.qt.io/qtforpython-6/
- HTTP library: **Requests** — Apache License 2.0
  - https://requests.readthedocs.io/
- Packaging: **PyInstaller**
  - https://pyinstaller.org/
- Installer: **Inno Setup**
  - https://jrsoftware.org/isinfo.php

詳細は [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) を参照してください。

## プライバシー

Weather Notifyには独自のユーザーアカウント、広告、アクセス解析、開発者サーバーはありません。

ただし機能のため、外部サービスへ次の情報を送信します。

- 天気取得: 選択した地点の緯度・経度をOpen-Meteoへ送信
- 住所検索: 入力した検索文字列をNominatimへ送信
- 現在地の住所化: Windowsが取得した緯度・経度をNominatimへ送信

監視条件やアプリ設定はPC内に保存します。

詳細は [`PRIVACY.md`](PRIVACY.md) を参照してください。

## 注意事項

- 天気情報や予報は参考情報です。正確性・完全性・継続提供は保証されません。
- 「睡眠中の窓開け判定」は気象条件のみを基準にした補助機能です。防犯、騒音、花粉、大気汚染、虫の侵入などは判定していません。
- 災害・生命・財産に関わる判断には、公的機関や信頼できる公式情報を確認してください。

## ソースコードの扱い

このリポジトリはポートフォリオ・レビュー目的で公開しています。プロジェクト固有のソースコードについて、現時点ではオープンソースライセンスを付与していません。第三者ライブラリ・データ・サービスには、それぞれのライセンスと利用条件が適用されます。

## Version

Current: **v0.1.21**

変更履歴は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。
