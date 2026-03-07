# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Use the directory containing this spec file so it works on any OS
_HERE = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(_HERE, 'eyeguard'),     'eyeguard'),
    (os.path.join(_HERE, 'templates'),    'templates'),
    (os.path.join(_HERE, 'media'),        'media'),
    (os.path.join(_HERE, 'staticfiles'),  'staticfiles'),
]
binaries = []
hiddenimports = ['django', 'rest_framework', 'corsheaders', 'daphne', 'cv2', 'torch', 'torchvision', 'numpy', 'ultralytics', 'channels', 'channels_redis', 'whitenoise', 'whitenoise.middleware', 'whitenoise.runserver_nostatic', 'django_filters', 'PIL', 'psycopg2', 'psycopg2._psycopg', 'dotenv', 'asgiref', 'asgiref.sync', 'asgiref.wsgi', 'twisted', 'rest_framework.authentication', 'rest_framework.permissions', 'rest_framework.filters', 'corsheaders.middleware', 'django.contrib.staticfiles', 'django.contrib.staticfiles.management.commands.runserver']
tmp_ret = collect_all('whitenoise')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('corsheaders')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rest_framework')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('django_filters')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('psycopg2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('eyeguard')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(_HERE, 'launcher.py')],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EyeGuard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
