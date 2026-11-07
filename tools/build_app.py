#!/usr/bin/env python3
"""Builds a single app from apps/<slug> into dist/<slug>-<version>.apk.

No Gradle: aapt2 compiles and links resources, ecj compiles the Java sources
against android.jar, d8 turns the class files into classes.dex, then zipalign
and apksigner finish the APK.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
JAVA_HOME = pathlib.Path(os.environ['JAVA_HOME'])
ANDROID_HOME = pathlib.Path(os.environ['ANDROID_HOME'])
BUILD_TOOLS = ANDROID_HOME / 'build-tools' / os.environ.get('BUILD_TOOLS_VERSION', '34.0.0')
PLATFORM = ANDROID_HOME / 'platforms' / os.environ.get('ANDROID_PLATFORM', 'android-34')
ANDROID_JAR = PLATFORM / 'android.jar'
JAVA = JAVA_HOME / 'bin' / 'java'
ECJ = pathlib.Path(os.environ.get('ECJ_JAR', ROOT / 'tools' / 'ecj.jar'))
KEYSTORE = pathlib.Path(os.environ.get('KEYSTORE', ROOT / 'tools' / 'debug.keystore'))
MIN_SDK = os.environ.get('MIN_SDK', '26')
TARGET_SDK = os.environ.get('TARGET_SDK', '34')


def run(cmd, **kw):
    print('  $', ' '.join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def build(slug):
    app_dir = ROOT / 'apps' / slug
    cfg = json.loads((app_dir / 'app.json').read_text())
    work = ROOT / 'build' / slug
    if work.exists():
        shutil.rmtree(work)
    (work / 'classes').mkdir(parents=True)
    (work / 'dex').mkdir(parents=True)

    print('==> %s (%s)' % (cfg['name'], cfg['applicationId']))

    # 1. resources
    run([BUILD_TOOLS / 'aapt2', 'compile', '--dir', app_dir / 'res', '-o', work / 'res.zip'])

    # 2. link: manifest + resources + assets -> unsigned apk
    run([BUILD_TOOLS / 'aapt2', 'link',
         '-o', work / 'base.apk',
         '-I', ANDROID_JAR,
         '--manifest', app_dir / 'AndroidManifest.xml',
         '-R', work / 'res.zip',
         '-A', app_dir / 'assets',
         '--min-sdk-version', MIN_SDK,
         '--target-sdk-version', TARGET_SDK,
         '--version-code', str(cfg['versionCode']),
         '--version-name', cfg['versionName'],
         '--auto-add-overlay'])

    # 3. java -> class files (ecj, because not every JDK image ships javac)
    sources = sorted(str(p) for p in (ROOT / 'shared/src').rglob('*.java'))
    run([JAVA, '-jar', ECJ,
         '-source', '8', '-target', '8', '-nowarn', '-proc:none',
         '-bootclasspath', ANDROID_JAR,
         '-d', work / 'classes'] + sources)

    # 4. class files -> dex
    classes = sorted(str(p) for p in (work / 'classes').rglob('*.class'))
    run([JAVA, '-cp', BUILD_TOOLS / 'lib' / 'd8.jar', 'com.android.tools.r8.D8',
         '--lib', ANDROID_JAR,
         '--min-api', MIN_SDK,
         '--output', work / 'dex'] + classes)

    # 5. put classes.dex inside the apk
    with zipfile.ZipFile(work / 'base.apk', 'a', zipfile.ZIP_DEFLATED) as z:
        z.write(work / 'dex' / 'classes.dex', 'classes.dex')

    # 6. align, then sign
    run([BUILD_TOOLS / 'zipalign', '-f', '-p', '4', work / 'base.apk', work / 'aligned.apk'])
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    out = dist / ('%s-%s.apk' % (slug, cfg['versionName']))
    run([JAVA, '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'sign',
         '--ks', KEYSTORE, '--ks-type', 'PKCS12',
         '--ks-pass', 'pass:android', '--ks-key-alias', 'androiddebugkey',
         '--key-pass', 'pass:android',
         '--min-sdk-version', MIN_SDK,
         '--v4-signing-enabled', 'false',
         '--out', out, work / 'aligned.apk'])

    run([JAVA, '-jar', BUILD_TOOLS / 'lib' / 'apksigner.jar', 'verify', '--print-certs', out],
        stdout=subprocess.DEVNULL)
    print('    -> %s (%.1f KB)' % (out.relative_to(ROOT), out.stat().st_size / 1024))
    return out


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('usage: build_app.py <slug>')
    build(sys.argv[1])
