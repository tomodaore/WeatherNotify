# Weather Notify Privacy Notes

最終更新: 2026-09-19

Weather Notify は、個人利用・ポートフォリオ用途のWindowsデスクトップアプリです。

## 開発者側で収集しない情報

Weather Notifyには以下の機能はありません。

- ユーザーアカウント
- ログイン
- 広告
- アクセス解析
- 独自のクラウドデータベース
- 開発者が管理するバックエンドサーバー

そのため、アプリ独自の仕組みで利用履歴や監視設定を開発者へ送信することはありません。

## PC内に保存する情報

以下の設定をローカルPCに保存します。

- 現在地として設定した地点
- 監視地点
- 気温・湿度条件
- 監視ON/OFF
- 通知判定に必要な状態

保存先:

```text
%USERPROFILE%\.weather_notify\settings.json
```

## 外部サービスへ送信する情報

### Open-Meteo

天気情報を取得するため、設定地点の緯度・経度をOpen-Meteoへ送信します。

https://open-meteo.com/en/terms

### OpenStreetMap Nominatim

地点検索時は、ユーザーが入力した住所・地名の検索文字列をNominatimへ送信します。

Windowsの現在地から住所を表示する場合は、取得した緯度・経度をNominatimへ送信します。

https://operations.osmfoundation.org/policies/nominatim/

## Windows位置情報

「現在地を取得」を使用した場合のみ、Windowsの位置情報サービスへ現在位置を要求します。

取得精度はGPS、Wi-Fi、ネットワーク環境などPCの位置情報ソースに依存します。

## 補足

外部サービス側で行われるログ保存・データ処理については、それぞれのサービスの利用規約・プライバシーポリシーが適用されます。
