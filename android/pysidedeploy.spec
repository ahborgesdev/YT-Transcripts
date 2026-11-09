[app]
title = BuscadorYT
project_dir = .
input_file = main.py
exec_directory = dist
project_file = 
icon = icon.png

[python]
packages = 
android_packages = buildozer==1.6.0,cython==0.29.37

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Core,Gui,Widgets
plugins = 

[android]
wheel_pyside = /Users/amadahernandezborges/deepseek_harness/transcrip/.android-build/wheels/pyside6-6.12.0-android_aarch64.whl
wheel_shiboken = /Users/amadahernandezborges/deepseek_harness/transcrip/.android-build/wheels/shiboken6-6.12.0-android_aarch64.whl
plugins = platforms_qtforandroid

[buildozer]
mode = debug
recipe_dir = /Users/amadahernandezborges/deepseek_harness/transcrip/android/deployment/recipes
jars_dir = /Users/amadahernandezborges/deepseek_harness/transcrip/android/deployment/jar/PySide6/jar
ndk_path = /Users/amadahernandezborges/deepseek_harness/transcrip/.android-build/home/.pyside6_android_deploy/android-ndk/android-ndk-r28c
sdk_path = /Users/amadahernandezborges/deepseek_harness/transcrip/.android-build/home/.pyside6_android_deploy/android-sdk
local_libs = plugins_platforms_qtforandroid
arch = aarch64

