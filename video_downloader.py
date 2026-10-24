# -*- coding: utf-8 -*-
"""
视频下载器 — Codex 风格界面
支持抖音 / B站 下载，深色极简、等宽字体、键盘优先。
"""
import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog

APP_DIR = (os.path.dirname(sys.executable)
           if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))

VERSION = "1.0.0"

# 打包成窗口程序后，子进程不能再弹黑框
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
ICON_PATH = os.path.join(APP_DIR, "icon.ico")

# ───────────────────────── 设计令牌 ─────────────────────────
BG       = "#0A0A0A"
PANEL    = "#111111"
PANEL_2  = "#161616"
BORDER   = "#262626"
BORDER_2 = "#333333"
TEXT     = "#EDEDED"
DIM      = "#8B8B8B"
FAINT    = "#5C5C5C"
SUCCESS  = "#4ADE80"
WARN     = "#FBBF24"
ERROR    = "#F87171"
ACCENT   = "#EDEDED"

F_MONO   = ("Cascadia Mono", 10)
F_MONO_S = ("Cascadia Mono", 9)
F_SANS_S = ("Microsoft YaHei UI", 9)
F_TITLE  = ("Microsoft YaHei UI", 17, "bold")
F_LABEL  = ("Cascadia Mono", 8)


def find_python():
    """返回可执行脚本的 python 解释器。

    注意：打包成 EXE 后 sys.executable 指向 EXE 自己，不能再当解释器用，
    必须直接用同目录的 python_full\\python.exe。
    """
    cands = []
    if not getattr(sys, "frozen", False):
        cands.append(sys.executable)
    cands.append(os.path.join(APP_DIR, "python_full", "python.exe"))
    for c in cands:
        if c and os.path.exists(c) and "WindowsApps" not in c:
            return c
    return cands[-1]


def ytdlp_version():
    """探测 yt-dlp 版本，用于状态栏。"""
    exe = os.path.join(APP_DIR, "python_full", "Scripts", "yt-dlp.exe")
    for cmd in ([exe, "--version"], ["yt-dlp", "--version"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=8,
                               creationflags=NO_WINDOW)
            if r.returncode == 0:
                return (r.stdout or "").strip().splitlines()[0]
        except Exception:
            continue
    return None


# ───────────────────────── 基础控件 ─────────────────────────
class Hairline(tk.Frame):
    """一像素分隔线。"""
    def __init__(self, parent, color=BORDER):
        super().__init__(parent, bg=color, height=1)


class FlatEntry(tk.Frame):
    """带边框的等宽输入框。"""
    def __init__(self, parent, placeholder=""):
        super().__init__(parent, bg=BORDER, padx=1, pady=1)
        self.placeholder = placeholder
        self.entry = tk.Entry(
            self, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=F_MONO, highlightthickness=0, bd=0,
        )
        self.entry.pack(fill="both", expand=True, ipady=7)
        if placeholder:
            self._show_placeholder()
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<FocusIn>", lambda e: self.configure(bg=BORDER_2), add="+")
        self.entry.bind("<FocusOut>", lambda e: self.configure(bg=BORDER), add="+")

    def _show_placeholder(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self.placeholder)
        self.entry.configure(fg=FAINT)

    def _focus_in(self, _e):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=TEXT)

    def _focus_out(self, _e):
        if not self.entry.get().strip():
            self._show_placeholder()

    def get(self):
        v = self.entry.get().strip()
        return "" if v == self.placeholder else v

    def set(self, value):
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, value)
            self.entry.configure(fg=TEXT)
        elif self.placeholder:
            self._show_placeholder()


class TextBox(tk.Frame):
    """等宽文本域，带边框与滚动条。"""
    def __init__(self, parent, height=5, readonly=False):
        super().__init__(parent, bg=BORDER, padx=1, pady=1)
        self.text = tk.Text(
            self, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=F_MONO, height=height, wrap="word",
            highlightthickness=0, bd=0, padx=10, pady=8,
            selectbackground=BORDER_2, selectforeground=TEXT,
        )
        self.scroll = ttk.Scrollbar(
            self, command=self.text.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        if readonly:
            self.text.configure(state="disabled")
        self.text.bind("<FocusIn>", lambda e: self.configure(bg=BORDER_2))
        self.text.bind("<FocusOut>", lambda e: self.configure(bg=BORDER))

    def write(self, line):
        self.text.configure(state="normal")
        self.text.insert("end", line + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class Button(tk.Label):
    """扁平按钮：主按钮白底黑字，次按钮描边。"""
    def __init__(self, parent, text, command, primary=False, small=False):
        self.primary = primary
        bg = ACCENT if primary else PANEL
        fg = BG if primary else TEXT
        font = F_MONO_S if small else ("Microsoft YaHei UI", 9, "bold" if primary else "normal")
        super().__init__(
            parent, text=text, bg=bg, fg=fg, font=font,
            padx=13 if small else 22, pady=5 if small else 9,
            cursor="hand2",
            highlightthickness=0 if primary else 1,
            highlightbackground=BORDER_2, highlightcolor=BORDER_2,
        )
        self._bg, self._fg = bg, fg
        self._hover = BORDER_2 if primary else PANEL_2
        self._cmd = command
        self._enabled = True
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _click(self, _e):
        if self._enabled:
            self._cmd()

    def _enter(self, _e):
        if self._enabled:
            self.configure(bg=self._hover)

    def _leave(self, _e):
        if self._enabled:
            self.configure(bg=self._bg)

    def set_enabled(self, enabled, text=None):
        self._enabled = enabled
        if text:
            self.configure(text=text)
        self.configure(
            bg=self._bg if enabled else PANEL_2,
            fg=self._fg if enabled else FAINT,
            cursor="hand2" if enabled else "arrow",
        )


class TabBar(tk.Frame):
    """下划线式分段标签栏。"""
    def __init__(self, parent, names, on_change):
        super().__init__(parent, bg=BG)
        self.on_change = on_change
        self.items = []
        for i, name in enumerate(names):
            wrap = tk.Frame(self, bg=BG)
            wrap.pack(side="left", padx=(0, 26))
            label = tk.Label(
                wrap, text=name, bg=BG, fg=DIM,
                font=("Microsoft YaHei UI", 10), pady=8, cursor="hand2",
            )
            label.pack()
            bar = tk.Frame(wrap, bg=BG, height=2)
            bar.pack(fill="x")
            label.bind("<Button-1>", lambda e, idx=i: self.select(idx))
            bar.bind("<Button-1>", lambda e, idx=i: self.select(idx))
            self.items.append((label, bar))

    def select(self, index):
        for i, (label, bar) in enumerate(self.items):
            if i == index:
                label.configure(fg=TEXT, font=("Microsoft YaHei UI", 10, "bold"))
                bar.configure(bg=TEXT)
            else:
                label.configure(fg=DIM, font=("Microsoft YaHei UI", 10))
                bar.configure(bg=BG)
        self.on_change(index)


class StatusBar(tk.Frame):
    """底部状态栏：彩色圆点 + 等宽文字。"""
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL)
        Hairline(self, BORDER).pack(fill="x")
        row = tk.Frame(self, bg=PANEL)
        row.pack(fill="x", padx=18, pady=7)
        self.dot = tk.Label(row, text="●", bg=PANEL, fg=FAINT, font=("Cascadia Mono", 8))
        self.dot.pack(side="left")
        self.msg = tk.Label(row, text="就绪", bg=PANEL, fg=DIM, font=F_MONO_S)
        self.msg.pack(side="left", padx=(8, 0))
        self.right = tk.Label(row, text="", bg=PANEL, fg=FAINT, font=F_MONO_S)
        self.right.pack(side="right")

    def set(self, text, kind="idle"):
        color = {"idle": FAINT, "run": WARN, "ok": SUCCESS, "err": ERROR}.get(kind, FAINT)
        fg = {"idle": DIM, "run": TEXT, "ok": SUCCESS, "err": ERROR}.get(kind, DIM)
        self.dot.configure(fg=color)
        self.msg.configure(text=text, fg=fg)

    def set_right(self, text):
        self.right.configure(text=text)


def setup_style():
    """暗色细滚动条。"""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Dark.Vertical.TScrollbar",
        background=BORDER_2, troughcolor=PANEL_2,
        bordercolor=PANEL_2, darkcolor=BORDER_2, lightcolor=BORDER_2,
        arrowcolor=DIM, arrowsize=9, width=9,
        relief="flat", borderwidth=0,
    )
    style.map(
        "Dark.Vertical.TScrollbar",
        background=[("active", FAINT), ("pressed", DIM)],
        arrowcolor=[("active", TEXT)],
    )


# ───────────────────────── 主程序 ─────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title(f"视频下载器 v{VERSION}")
        root.geometry("1000x880")
        root.minsize(880, 700)
        root.configure(bg=BG)
        self.py = find_python()
        self.proc = None
        self.current = "douyin"

        self._build()
        self.tabbar.select(0)
        self._probe_env()

    # ── 布局 ──
    def _build(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=24, pady=(22, 0))
        tk.Label(head, text="视频下载器", bg=BG, fg=TEXT, font=F_TITLE).pack(anchor="w")
        tk.Label(
            head, text=f"{APP_DIR}   ·   抖音 / B站", bg=BG, fg=FAINT, font=F_MONO_S,
        ).pack(anchor="w", pady=(4, 0))

        tk.Frame(self.root, bg=BG, height=14).pack()

        bar_wrap = tk.Frame(self.root, bg=BG)
        bar_wrap.pack(fill="x", padx=24)
        self.tabbar = TabBar(bar_wrap, ["抖音", "B 站"], self._switch)
        self.tabbar.pack(anchor="w")
        Hairline(self.root).pack(fill="x")

        self.host = tk.Frame(self.root, bg=BG)
        self.host.pack(fill="both", expand=True)
        self.views = {}
        self.views["douyin"] = self._build_douyin(self.host)
        self.views["bili"] = self._build_bili(self.host)
        for v in self.views.values():
            v.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.status = StatusBar(self.root)
        self.status.pack(fill="x", side="bottom")

        self.root.bind("<Control-Return>", lambda e: self._start_current())
        self.root.bind("<Control-l>", lambda e: self._clear_current())

    def _switch(self, index):
        self.current = "douyin" if index == 0 else "bili"
        self.views[self.current].lift()
        self.root.focus_set()

    def _build_douyin(self, parent):
        page = tk.Frame(parent, bg=BG)

        self._caption(page, "LINKS", "每行一个分享链接或文案")
        self.dy_links = TextBox(page, height=5)
        self.dy_links.pack(fill="both", expand=True, padx=24, pady=(6, 0))

        self._caption(page, "OUTPUT", "下载文件保存位置")
        self.dy_out = self._path_row(page)

        self.dy_btn = Button(page, "▶   开始下载", self.start_douyin, primary=True)
        self.dy_btn.pack(anchor="w", padx=24, pady=(16, 0))
        self._hint(page, "Ctrl + Enter 开始   ·   Ctrl + L 清空")

        self._caption(page, "LOG")
        self.dy_log = TextBox(page, height=8, readonly=True)
        self.dy_log.pack(fill="both", expand=True, padx=24, pady=(6, 18))
        return page

    def _build_bili(self, parent):
        page = tk.Frame(parent, bg=BG)

        self._caption(page, "URL", "B站视频链接")
        self.bi_url = FlatEntry(page, placeholder="https://www.bilibili.com/video/BV...")
        self.bi_url.pack(fill="x", padx=24, pady=(6, 0))

        self._caption(page, "TIME RANGE", "留空下载完整视频；HH:MM:SS，可只填一端")
        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", padx=24, pady=(6, 0))
        left = tk.Frame(row, bg=BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(left, text="START", bg=BG, fg=FAINT, font=F_LABEL).pack(anchor="w")
        self.bi_start = FlatEntry(left, placeholder="00:00:00")
        self.bi_start.pack(fill="x", pady=(4, 0))
        right = tk.Frame(row, bg=BG)
        right.pack(side="left", fill="x", expand=True)
        tk.Label(right, text="END", bg=BG, fg=FAINT, font=F_LABEL).pack(anchor="w")
        self.bi_end = FlatEntry(right, placeholder="00:00:00")
        self.bi_end.pack(fill="x", pady=(4, 0))

        self._caption(page, "OUTPUT", "下载文件保存位置")
        self.bi_out = self._path_row(page)

        self.bi_btn = Button(page, "▶   开始下载", self.start_bili, primary=True)
        self.bi_btn.pack(anchor="w", padx=24, pady=(16, 0))
        self._hint(page, "Ctrl + Enter 开始   ·   Ctrl + L 清空")

        self._caption(page, "LOG")
        self.bi_log = TextBox(page, height=8, readonly=True)
        self.bi_log.pack(fill="both", expand=True, padx=24, pady=(6, 18))
        return page

    def _caption(self, parent, text, note=""):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(row, text=text, bg=BG, fg=FAINT, font=F_LABEL).pack(side="left")
        if note:
            tk.Label(row, text=note, bg=BG, fg=FAINT, font=F_SANS_S).pack(side="left", padx=(12, 0))

    def _hint(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=FAINT, font=F_MONO_S).pack(anchor="w", padx=24, pady=(6, 0))

    def _path_row(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=(6, 0))
        entry = FlatEntry(row)
        entry.pack(side="left", fill="x", expand=True)
        entry.set(self._default_dir())
        Button(row, "选择", lambda: self._pick_dir(entry), small=True).pack(side="left", padx=(8, 0))
        Button(row, "打开", lambda: self._open_dir(entry), small=True).pack(side="left", padx=(8, 0))
        return entry

    def _default_dir(self):
        d = os.path.join(os.path.expanduser("~"), "Downloads")
        return d if os.path.isdir(d) else APP_DIR

    def _pick_dir(self, entry):
        d = filedialog.askdirectory(initialdir=entry.get() or self._default_dir())
        if d:
            entry.set(os.path.normpath(d))

    def _open_dir(self, entry):
        d = entry.get()
        if d and os.path.isdir(d):
            os.startfile(d)
        else:
            self.status.set("目录不存在", "err")

    # ── 环境探测 ──
    def _probe_env(self):
        def work():
            try:
                ver = ytdlp_version()
                # 自带运行时看目录；源码运行时看当前解释器是否能 import
                bundled = os.path.join(
                    APP_DIR, "python_full", "Lib", "site-packages", "playwright")
                if os.path.isdir(bundled):
                    has_pw = True
                else:
                    import importlib.util
                    has_pw = importlib.util.find_spec("playwright") is not None
                has_login = os.path.isdir(os.path.join(APP_DIR, ".douyin_profile"))
                text = "   ·   ".join([
                    f"v{VERSION}",
                    f"yt-dlp {ver}" if ver else "yt-dlp 未安装",
                    "playwright OK" if has_pw else "playwright 缺失",
                    "已登录" if has_login else "未登录",
                ])
                self.root.after(0, lambda: self._safe(self.status.set_right, text))
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _safe(self, fn, *a, **kw):
        """主窗口已销毁时安静退出。"""
        try:
            fn(*a, **kw)
        except Exception:
            pass

    # ── 抖音 ──
    def start_douyin(self):
        raw = self.dy_links.text.get("1.0", "end").strip()
        if not raw:
            self.dy_log.write("[!] 请先填入至少一个链接")
            self.status.set("没有输入链接", "err")
            return
        out = self.dy_out.get() or self._default_dir()
        try:
            os.makedirs(out, exist_ok=True)
        except Exception as e:
            self.dy_log.write(f"[!] 无法创建目录: {e}")
            return

        urls = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        tmp = os.path.join(APP_DIR, ".links.txt")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(urls))
        except Exception as e:
            self.dy_log.write(f"[!] 无法写入临时文件: {e}")
            return

        script = os.path.join(APP_DIR, "douyin_downloader.py")
        if not os.path.exists(script):
            self.dy_log.write(f"[!] 找不到脚本: {script}")
            self.status.set("引擎脚本缺失", "err")
            return

        cmd = [self.py, "-u", script, tmp, "-o", out]
        if os.path.normcase(self.py) == os.path.normcase(sys.executable):
            self.dy_log.write("[!] 解释器解析错误（不能用 EXE 自身启动脚本）")
            self.status.set("引擎解释器异常", "err")
            return
        self._run(cmd, self.dy_log, self.dy_btn, "抖音", len(urls), out)

    # ── B站 ──
    def start_bili(self):
        url = self.bi_url.get()
        if not url or not url.startswith("http"):
            self.bi_log.write("[!] 请填入有效的 B站 链接")
            self.status.set("链接无效", "err")
            return
        out = self.bi_out.get() or self._default_dir()
        try:
            os.makedirs(out, exist_ok=True)
        except Exception as e:
            self.bi_log.write(f"[!] 无法创建目录: {e}")
            return

        start = self.bi_start.get()
        end = self.bi_end.get()

        yt = os.path.join(APP_DIR, "python_full", "Scripts", "yt-dlp.exe")
        exe = yt if os.path.exists(yt) else "yt-dlp"

        cmd = [exe, "-f", "bv*+ba/b", "--merge-output-format", "mp4"]
        if start or end:
            section = f"*{start}-{end}" if (start and end) else (f"*{start}-" if start else f"*-{end}")
            cmd += ["--download-sections", section, "--force-keyframes-at-cuts"]
        cmd += ["-o", os.path.join(out, "%(title)s.%(ext)s"), url]

        self._run(cmd, self.bi_log, self.bi_btn, "B站", 1, out)

    # ── 执行 ──
    def _run(self, cmd, log, btn, label, count, out_dir):
        log.clear()
        btn.set_enabled(False, "■   下载中…")
        self.status.set(f"{label}：正在下载（{count} 个）", "run")
        log.write(f"[{label}] 开始 · {count} 个任务")
        log.write(f"$ {' '.join(cmd)}")
        log.write("")

        def work():
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            code = -1
            try:
                self.proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    bufsize=1, env=env, cwd=APP_DIR,
                    creationflags=NO_WINDOW,
                )
                for raw in self.proc.stdout:
                    if not raw:
                        continue
                    parts = [p.strip() for p in raw.replace("\r", "\n").split("\n") if p.strip()]
                    if not parts:
                        continue
                    if len(parts) > 3:
                        parts = [parts[-1]]
                    for p in parts:
                        self.root.after(0, lambda t=p: log.write(t))
                self.proc.wait()
                code = self.proc.returncode
            except FileNotFoundError:
                self.root.after(0, lambda: log.write("[!] 找不到可执行文件，请检查依赖"))
            except Exception as e:
                self.root.after(0, lambda: log.write(f"[!] 运行出错: {e}"))
            finally:
                self.proc = None

                def done():
                    log.write("")
                    if code == 0:
                        log.write(f"[OK] 完成 · 保存到 {out_dir}")
                        self.status.set(f"{label}：下载完成", "ok")
                    else:
                        log.write(f"[FAIL] 退出码 {code}")
                        self.status.set(f"{label}：下载失败（{code}）", "err")
                    btn.set_enabled(True, "▶   开始下载")

                self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    # ── 快捷键 ──
    def _start_current(self):
        if self.current == "douyin":
            self.start_douyin()
        else:
            self.start_bili()

    def _clear_current(self):
        if self.current == "douyin":
            self.dy_links.text.delete("1.0", "end")
            self.dy_log.clear()
        else:
            self.bi_url.set("")
            self.bi_start.set("")
            self.bi_end.set("")
            self.bi_log.clear()
        self.status.set("已清空", "idle")


def main():
    root = tk.Tk()
    setup_style()
    if os.path.exists(ICON_PATH):
        try:
            root.iconbitmap(default=ICON_PATH)
        except Exception:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
