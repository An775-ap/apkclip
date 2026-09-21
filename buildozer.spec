[app]
title = YT Clipper Pro
package.name = ytclipperpro
package.domain = com.clipper
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

# Dependencies needed for yt-dlp, video handling, and network requests
requirements = python3,kivy,yt-dlp,certifi,urllib3,requests

orientation = portrait
fullscreen = 0

# Storage and network permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.add_libs_arm64_v8a = libs/arm64-v8a/*.so

[buildozer]
log_level = 2
warn_on_root = 1
