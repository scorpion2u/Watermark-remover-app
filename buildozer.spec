[app]
title = WatermarkRemover
package.name = watermarkremover
package.domain = org.example

# 关键：指定源码目录（项目根）
source.dir = .

# 要包含的文件类型
source.include_exts = py,png,jpg,kv,txt

version = 0.1
# 根据你的需求可以把 kivy 版本换成别的
requirements = python3,kivy==2.1.0,Pillow

orientation = portrait

# Android 设置（可按需调整）
android.api = 33
android.sdk = 33
android.ndk = 23.1.7779620

android.arch = arm64-v8a,armeabi-v7a
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

log_level = 2
warn_on_root = 1
