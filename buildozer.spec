[app]
title = YT Downloader Pro
package.name = ytdownloader
package.domain = org.masshet
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,yt-dlp
orientation = portrait
osx.kivy_version = 1.9.1
osx.mac_deps =
osx.mac_deps.kivy =
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
