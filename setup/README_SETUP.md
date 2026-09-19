# Weather Notify Setup Build

## 配布するファイル

`build_setup.bat` が成功すると、次のファイルが生成されます。

```text
dist_setup\WeatherNotify_Setup_v0.1.21.exe
```

このSetup EXEをGitHub Releases等で配布できます。利用者側にPythonは不要です。

## Setupに含まれる情報

- WeatherNotify.exe
- README.md
- PRIVACY.md
- THIRD_PARTY_NOTICES.md
- LICENSE.md
- CHANGELOG.md

## 更新

同じAppIdを維持しているため、旧バージョンが入っているPCでは上書き更新されます。

設定は `%USERPROFILE%\.weather_notify\settings.json` に保存されるため、同じWindowsユーザーでは更新後も引き継がれます。別PC・別Windowsユーザーの初回インストールでは初期状態です。
