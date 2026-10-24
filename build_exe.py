# -*- coding: utf-8 -*-
"""把界面打包成单文件 EXE。依赖仍留在同目录（python_full / douyin_downloader.py）。"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, "python_full", "python.exe")
ICON = os.path.join(ROOT, "icon.ico")
ENTRY = os.path.join(ROOT, "video_downloader.py")
APP_NAME = "视频下载器"
WORK = os.path.join(ROOT, "build")


def run(cmd):
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT)
    return p.returncode


def main():
    for p in (PY, ICON, ENTRY):
        if not os.path.exists(p):
            print("[!] 缺少文件:", p)
            return 1

    if os.path.isdir(WORK):
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)

    cmd = [
        PY, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", APP_NAME,
        "--icon", ICON,
        "--distpath", os.path.join(WORK, "dist"),
        "--workpath", os.path.join(WORK, "tmp"),
        "--specpath", os.path.join(WORK, "spec"),
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "PIL",
        ENTRY,
    ]
    code = run(cmd)
    if code != 0:
        print("[!] 打包失败，退出码", code)
        return code

    built = os.path.join(WORK, "dist", APP_NAME + ".exe")
    if not os.path.exists(built):
        print("[!] 未找到产物:", built)
        return 1

    target = os.path.join(ROOT, APP_NAME + ".exe")
    shutil.copy2(built, target)
    size = os.path.getsize(target) / 1024 / 1024
    print()
    print("=" * 52)
    print(f"[OK] {target}  ({size:.1f} MB)")
    print("=" * 52)
    return 0


if __name__ == "__main__":
    sys.exit(main())
