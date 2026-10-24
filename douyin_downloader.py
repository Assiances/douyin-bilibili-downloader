# -*- coding: utf-8 -*-
"""
抖音无水印视频下载器（Playwright 版）
用法:
    python douyin_downloader.py "https://v.douyin.com/xxxxxx/"
    python douyin_downloader.py "https://www.douyin.com/video/73xxxxxxxxxxxxxxxxx"
    python douyin_downloader.py links.txt            # 批量，每行一个链接或分享文案
    python douyin_downloader.py "链接" -o D:\videos
依赖:
    pip install playwright
说明:
    自动调用系统已安装的 Chrome 浏览器。
    第一次运行会弹出浏览器窗口，请扫码登录抖音；登录状态会保存在本地，
    之后再运行就不需要重新登录了。
注意: 请尊重版权，仅用于个人学习或下载自己的作品。
"""

import argparse
import asyncio
import os
import re
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("缺少 playwright，请先运行: pip install playwright")
    sys.exit(1)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(SCRIPT_DIR, ".douyin_profile")


def extract_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s，。！!？?、]+", text)
    return m.group(0) if m else None


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name).strip()
    return name[:100] or "douyin_video"


async def wait_for_login(page, timeout_sec=180):
    """等待用户登录抖音。检测右上角是否出现头像。"""
    print("  检查登录状态...")
    for i in range(timeout_sec):
        try:
            logged_in = await page.evaluate("""
                () => {
                    const avatar = document.querySelector('[data-e2e="avatar"]') ||
                                   document.querySelector('.avatar') ||
                                   document.querySelector('[class*="Avatar"]');
                    return !!avatar;
                }
            """)
            if logged_in:
                print("  已登录 ✓")
                return True
        except Exception:
            # 页面导航中，忽略继续等
            pass
        if i == 5:
            print("  未登录，请在弹出的浏览器窗口中扫码登录抖音...")
        await asyncio.sleep(1)
    print("  等待登录超时")
    return False


async def extract_video_info(page) -> dict:
    """从当前页面提取视频信息。"""
    info = await page.evaluate("""
        () => {
            const rd = document.getElementById('RENDER_DATA');
            if (rd) {
                try {
                    return JSON.parse(decodeURIComponent(rd.textContent));
                } catch(e) {}
            }
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const t = s.textContent || '';
                if (t.startsWith('window._ROUTER_DATA')) {
                    try {
                        const json = t.substring(t.indexOf('{'), t.lastIndexOf('}') + 1);
                        return JSON.parse(json);
                    } catch(e) {}
                }
            }
            return null;
        }
    """)

    if not info:
        return None

    def find_aweme(obj):
        if isinstance(obj, dict):
            if "item_list" in obj and isinstance(obj["item_list"], list):
                for item in obj["item_list"]:
                    if item.get("video"):
                        return item
            for v in obj.values():
                r = find_aweme(v)
                if r:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = find_aweme(v)
                if r:
                    return r
        return None

    return find_aweme(info)


async def extract_video_urls_from_dom(page):
    """激进搜索：拿页面 HTML，在 Python 里用正则找视频 URL。"""
    html = await page.content()
    urls = set()

    patterns = [
        r'https?://[^\s"\'<>]+?douyinvod[^\s"\'<>]+',
        r'https?://[^\s"\'<>]+?douyinpic[^\s"\'<>]+?video[^\s"\'<>]+',
        r'https?://[^\s"\'<>]+?/v\d+-web[^\s"\'<>]+',
        r'https?://[^\s"\'<>]+?\.mp4[^\s"\'<>]*',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html):
            u = m.group(0).replace('\\u0026', '&').replace('\\/', '/')
            u = u.rstrip('",}')
            if not u.startswith('blob:') and 'bytednsdoc' not in u and 'douyin_pc_client' not in u:
                urls.add(u)

    return list(urls)


async def extract_video_from_window(page):
    """从已知全局变量和 performance 资源里找视频 URL（轻量）。"""
    result = await page.evaluate(r"""
        () => {
            const found = { urls: [], title: '', author: '', aweme_id: '' };
            const candidates = [window._ROUTER_DATA, window.__INITIAL_STATE__, window.__NEXT_DATA__];
            for (const root of candidates) {
                if (!root) continue;
                try {
                    const json = JSON.stringify(root);
                    if (json && json.includes('play_addr')) {
                        const regex = /https?:\/\/[^"\\]+?play[^"\\]+/g;
                        let m;
                        while ((m = regex.exec(json)) !== null) {
                            let u = m[0].replace(/\\u0026/g, '&').replace(/\\\//g, '/');
                            if (!u.startsWith('blob:')) found.urls.push(u);
                        }
                        const tMatch = json.match(/"desc":"([^"]+)"/);
                        if (tMatch && !found.title) found.title = tMatch[1];
                        const aMatch = json.match(/"nickname":"([^"]+)"/);
                        if (aMatch && !found.author) found.author = aMatch[1];
                    }
                } catch(e) {}
            }
            try {
                const resources = performance.getEntriesByType('resource');
                for (const r of resources) {
                    const name = r.name;
                    if (name.startsWith('blob:')) continue;
                    if (name.includes('douyinvod') || name.includes('v26-web') || name.includes('v3-web')) {
                        if (r.transferSize > 100000 || r.decodedBodySize > 100000) {
                            found.urls.push(name);
                        }
                    }
                }
            } catch(e) {}
            return found;
        }
    """)
    return result or {"urls": [], "title": "", "author": "", "aweme_id": ""}


async def download_video(url: str, save_path: str, cookies: list):
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
    }
    cookie_dict = {c["name"]: c["value"] for c in cookies}
    with requests.get(url, headers=headers, cookies=cookie_dict, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r  下载: {pct:3d}% ({downloaded//1024} KB)", end="", flush=True)
        print()


async def download_one(playwright, share_url: str, save_dir: str):
    print(f"\n>>> {share_url}")

    # 始终显示浏览器窗口，方便扫码和观察
    ctx = await playwright.chromium.launch_persistent_context(
        USER_DATA_DIR,
        channel="chrome",
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"],
    )

    try:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # 拦截网络请求，收集视频和音频 URL（DASH 流两者分开）
        captured_video_urls = []
        captured_audio_urls = []
        def on_response(response):
            url = response.url
            if url.startswith("blob:"):
                return
            if any(bad in url for bad in [".ts", ".m3u8", ".jpg", ".jpeg", ".png", ".webp",
                                          ".css", ".js", ".woff", ".ico",
                                          "douyin_pc_client", "bytednsdoc",
                                          "passport", "/sticker/"]):
                return
            try:
                ct = response.headers.get("content-type", "")
            except Exception:
                ct = ""
            is_audio = "audio" in ct or "audio" in url.lower()
            is_video = ("video" in ct or "mp4" in ct or
                        any(k in url for k in ["play", "douyinvod", "v26-web", "v3-web", "/video/"]))
            if is_audio:
                if url not in captured_audio_urls:
                    captured_audio_urls.append(url)
            elif is_video:
                if url not in captured_video_urls:
                    captured_video_urls.append(url)
        page.on("response", on_response)

        # 先访问首页，确保登录状态
        print("  打开抖音首页...")
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 等待登录（如果需要）
        await wait_for_login(page, timeout_sec=180)

        # 打开目标链接
        print(f"  打开目标链接...")
        await page.goto(share_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        current_url = page.url
        print(f"  当前地址: {current_url}")

        # 如果被重定向到首页，尝试直接构造视频 URL
        if current_url.rstrip("/") in ("https://www.douyin.com", "https://www.douyin.com/jingxuan"):
            m = re.search(r"/video/(\d+)", share_url)
            if m:
                video_url = f"https://www.douyin.com/video/{m.group(1)}"
                print(f"  尝试直接访问: {video_url}")
                await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                current_url = page.url
                print(f"  当前地址: {current_url}")

        # 循环等待视频加载（最多 25 秒）
        print("  等待视频加载...")
        video_urls = []
        title = ""
        author = ""
        aweme_id = ""

        for wait_round in range(30):
            await asyncio.sleep(1)

            # 方法1: 从 RENDER_DATA 提取
            if not video_urls:
                item = await extract_video_info(page)
                if item:
                    title = item.get("desc", "")
                    author = (item.get("author") or {}).get("nickname", "")
                    aweme_id = item.get("aweme_id", "")
                    video = item.get("video", {})
                    for u in (video.get("play_addr") or {}).get("url_list", []):
                        if not u.startswith("blob:"):
                            video_urls.append(u)
                    for br in (video.get("bit_rate") or []):
                        for u in (br.get("play_addr") or {}).get("url_list", []):
                            if not u.startswith("blob:"):
                                video_urls.append(u)

            # 方法2: 从 window 对象里搜索视频数据（长视频数据在 JS 内存里）
            if not video_urls:
                win_data = await extract_video_from_window(page)
                if win_data and win_data.get("urls"):
                    for u in win_data["urls"]:
                        if not u.startswith("blob:"):
                            video_urls.append(u)
                    if win_data.get("title"):
                        title = win_data["title"]
                    if win_data.get("author"):
                        author = win_data["author"]
                    if win_data.get("aweme_id"):
                        aweme_id = win_data["aweme_id"]
                    if video_urls:
                        print(f"  (从 window 对象找到 {len(video_urls)} 个候选)")

            # 方法3: 激进搜索页面 HTML 里的视频 URL
            if not video_urls:
                dom_urls = await extract_video_urls_from_dom(page)
                if dom_urls:
                    for u in dom_urls:
                        if not u.startswith("blob:"):
                            video_urls.append(u)
                    if video_urls:
                        print(f"  (从页面 HTML 搜索到 {len(video_urls)} 个候选)")

            # 方法4: 从拦截的网络请求里找（长视频 MSE 时用这个）
            if not video_urls and captured_video_urls:
                def _score(u):
                    s = 0
                    if ".mp4" in u: s += 10
                    if "play" in u: s += 5
                    if "douyinvod" in u: s += 8
                    if "v26-web" in u or "v3-web" in u: s += 8
                    return -s
                sorted_urls = sorted(captured_video_urls, key=_score)
                for u in sorted_urls:
                    if not u.startswith("blob:"):
                        video_urls.append(u)
                if video_urls:
                    print(f"  (从网络请求捕获 {len(video_urls)} 个视频候选)")

            # 方法5: 从 <video> 标签拿 src（仅非 blob）
            if not video_urls:
                try:
                    src = await page.evaluate("""
                        () => {
                            const v = document.querySelector('video');
                            if (v) {
                                const s = v.src || v.currentSrc;
                                if (s && !s.startsWith('blob:')) return s;
                            }
                            return null;
                        }
                    """)
                    if src:
                        video_urls.append(src)
                        if not title:
                            title = await page.title()
                except Exception:
                    pass

            if video_urls:
                break

        if not video_urls:
            print("  !! 未能获取视频地址")
            print(f"  (拦截到 {len(captured_video_urls)} 个视频, {len(captured_audio_urls)} 个音频)")
            return None

        # 去水印 + 去重
        cleaned = []
        seen = set()
        for u in video_urls:
            u2 = u.replace("playwm", "play")
            if u2 not in seen:
                seen.add(u2)
                cleaned.append(u2)

        # 调试：打印前3个候选
        print(f"  视频候选 {len(cleaned)} 个, 音频候选 {len(captured_audio_urls)} 个")
        for ci, cu in enumerate(cleaned[:3]):
            print(f"    [{ci+1}] {cu[:120]}...")

        print(f"  标题: {title or '(未知)'}")
        print(f"  作者: {author or '(未知)'}")

        title_safe = sanitize_filename(title or "douyin_video")
        author_safe = sanitize_filename(author or "unknown")
        filename = f"{author_safe}_{title_safe}_{aweme_id}.mp4" if aweme_id else f"{author_safe}_{title_safe}.mp4"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        cookies = await ctx.cookies()

        for i, vurl in enumerate(cleaned):
            try:
                print(f"  线路 {i+1}/{len(cleaned)}...")
                await download_video(vurl, save_path, cookies)
                size_mb = os.path.getsize(save_path) / 1024 / 1024
                if size_mb < 0.1:
                    print(f"  文件太小 ({size_mb:.2f} MB)，试下一个...")
                    os.remove(save_path)
                    continue

                # 如果有音频流，下载并用 ffmpeg 合并
                if captured_audio_urls:
                    audio_path = os.path.join(os.path.dirname(save_path), "_tmp_audio.mp4")
                    best_audio = next((a for a in captured_audio_urls if "audio" in a.lower()), captured_audio_urls[0])
                    print(f"  下载音频流...")
                    await download_video(best_audio, audio_path, cookies)
                    if os.path.getsize(audio_path) > 10000:
                        print(f"  合并音视频...")
                        merged = save_path + ".merged.mp4"
                        ret = os.system(f'ffmpeg -y -i "{save_path}" -i "{audio_path}" -c copy "{merged}"')
                        if ret == 0 and os.path.exists(merged) and os.path.getsize(merged) > 100000:
                            os.replace(merged, save_path)
                            print(f"  合并成功，音频已加入")
                        else:
                            if os.path.exists(merged): os.remove(merged)
                            print(f"  合并失败，保留无音频版本")
                        os.remove(audio_path)
                    else:
                        os.remove(audio_path)

                size_mb = os.path.getsize(save_path) / 1024 / 1024
                print(f"  已保存: {save_path} ({size_mb:.2f} MB)")
                return save_path
            except Exception as e:
                print(f"  失败: {e}")
                continue

        print("  !! 所有线路都失败")
        return None

    finally:
        await ctx.close()


async def main_async():
    parser = argparse.ArgumentParser(description="抖音无水印视频下载器")
    parser.add_argument("target", nargs="?", default=None, help="分享链接 / 完整视频URL / 包含链接的文本文件")
    parser.add_argument("-o", "--output", default="./downloads", help="保存目录，默认 ./downloads")
    args = parser.parse_args()

    target = args.target
    if not target:
        print("=" * 40)
        print("  抖音无水印视频下载器")
        print("=" * 40)
        print()
        target = input("请粘贴抖音分享链接或文案: ").strip()
        print()

    target = target.strip()

    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        urls = []
        for ln in lines:
            u = extract_url(ln)
            if u:
                urls.append(u)
    else:
        u = extract_url(target)
        urls = [u] if u else [target]

    if not urls:
        print("没有解析到任何链接。")
        sys.exit(1)

    print(f"共 {len(urls)} 个链接，保存到: {os.path.abspath(args.output)}")
    print(f"登录状态目录: {USER_DATA_DIR}")

    async with async_playwright() as p:
        ok, fail = 0, 0
        for i, u in enumerate(urls, 1):
            print(f"\n{'='*50}")
            print(f"[{i}/{len(urls)}]")
            try:
                result = await download_one(p, u, args.output)
                if result:
                    ok += 1
                else:
                    fail += 1
            except Exception as e:
                print(f"  !! 出错: {e}")
                fail += 1
            await asyncio.sleep(2)

    print(f"\n完成: 成功 {ok}，失败 {fail}")


if __name__ == "__main__":
    asyncio.run(main_async())
