# -*- coding: utf-8 -*-
"""把界面打包成单文件 EXE。

用法：
    python build_exe.py

产物输出到项目根目录的「视频下载器.exe」。
注意：这个 exe 只是界面外壳，运行时仍需要同目录下的 Python 运行时
与 douyin_downloader.py；要发给别人请把这些一起打压缩包。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(ROOT, "icon.ico")
ENTRY = os.path.join(ROOT, "video_downloader.py")
APP_NAME = "视频下载器"
WORK = os.path.join(ROOT, "build")

# 优先用随包运行时，源码用户则用当前解释器
BUNDLED_PY = os.path.join(ROOT, "python_full", "python.exe")
PY = BUNDLED_PY if os.path.exists(BUNDLED_PY) else sys.executable


def main():
    for p in (ICON, ENTRY):
        if not os.path.exists(p):
            print("[!] 缺少文件:", p)
            return 1

    if not os.path.exists(PY):
        print("[!] 找不到 Python 解释器:", PY)
        return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[!] 未安装 PyInstaller，请先运行: pip install pyinstaller")
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
    print("$", " ".join(cmd))
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        print("[!] 打包失败")
        return 1

    built = os.path.join(WORK, "dist", APP_NAME + ".exe")
    if not os.path.exists(built):
        print("[!] 未找到产物:", built)
        return 1

    target = os.path.join(ROOT, APP_NAME + ".exe")
    shutil.copy2(built, target)
    shutil.rmtree(WORK, ignore_errors=True)

    print()
    print("=" * 52)
    print(f"[OK] {target}  ({os.path.getsize(target) / 1024 / 1024:.1f} MB)")
    print("=" * 52)
    print("提示：分发时需要连同 python_full/ 和 douyin_downloader.py 一起打包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
