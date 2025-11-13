[app]
title = WatermarkRemover
package.name = watermarkremover
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,txt
version = 0.1
requirements = python3,kivy==2.1.0,numpy,Pillow,opencv-python-headless
orientation = portrait
android.arch = arm64-v8a,armeabi-v7a
icon.filename = icon.png
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# buildozer settings
log_level = 2
warn_on_root = 1
