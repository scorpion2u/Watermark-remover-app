[app]
# App identity
title = WatermarkRemover
package.name = watermarkremover
package.domain = org.example

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,txt

# App versioning
version = 0.1

# Requirements - 请根据实际需要添加
requirements = python3,kivy==2.1.0,Pillow

# Orientation
orientation = portrait

# Android specific
android.api = 33
android.minapi = 21
android.build_tools_version = 33.0.2
# Use the NDK string that matches the one installed by the workflow
android.ndk = 23.1.7779620
android.archs = arm64-v8a,armeabi-v7a

# Permissions (按需修改)
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Logging
log_level = 2
warn_on_root = 1