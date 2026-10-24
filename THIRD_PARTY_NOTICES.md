# 第三方组件声明

本项目的代码采用 MIT 许可证。但本项目**不包含**下列第三方组件的源码，
其中部分组件会以未修改的发行版本随 Windows 发布包一同分发，或由用户在系统中自行安装。

官方 Release 压缩包中包含的第三方运行时：

| 组件 | 版本 | 分发形式 | 许可证 | 项目主页 |
| --- | --- | --- | --- | --- |
| yt-dlp | 2026.10.21 | 打包为 `python_full/Scripts/yt-dlp.exe` 及 `Lib/site-packages/yt_dlp` | Unlicense | https://github.com/yt-dlp/yt-dlp |
| Playwright (Python) | 1.64.1 | `python_full/Lib/site-packages/playwright` | Apache-2.0 | https://github.com/microsoft/playwright-python |
| Python | 3.11.9 | `python_full/`（嵌入发行版） | PSF-2.0 | https://www.python.org/ |
| greenlet | 3.5.6 | Playwright 的依赖 | MIT | https://github.com/python-greenlet/greenlet |
| pyee | 13.0.1 | Playwright 的依赖 | MIT | https://github.com/jfhbrook/pyee |

仅在开发 / 打包阶段使用、不分发给最终用户的组件：

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| Pillow | `make_icon.py` 生成图标 | MIT-CMU |
| PyInstaller | `build_exe.py` 打包 EXE | GPL-2.0-with-exception |
| pip / setuptools | 依赖安装 | MIT |

可选、**不随包分发**、由用户自行安装的组件：

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| FFmpeg | B站 时间段裁剪与音视频合并 | LGPL-2.1+ 或 GPL-2.0+（取决于具体构建） |
| Google Chrome | 抖音下载所使用的浏览器 | 专有软件 |

---

## 关于 B站 下载

**B站 的下载功能由 yt-dlp 提供。**

`video_downloader.py` 中不包含任何 B站 页面解析、签名计算或分片下载逻辑，
它只是构造形如下面的命令行并解析其输出：

```
yt-dlp -f bv*+ba/b --merge-output-format mp4 \
       --download-sections "*00:24:33-00:28:40" --force-keyframes-at-cuts \
       -o "<输出目录>/%(title)s.%(ext)s" "<视频链接>"
```

因此：

- B站 解析若失效，通常是 yt-dlp 需要升级：`python -m pip install -U yt-dlp`
- 与 B站 下载相关的行为、限制与问题，请以 yt-dlp 上游文档为准
- 本项目与 yt-dlp 的作者无隶属关系，也未获得其背书

## 关于图标

`icon.ico` / `icon.png` 由仓库内的 `make_icon.py` 通过几何图形绘制生成，属本项目原创，
随项目一同以 MIT 许可证发布。仓库不含任何游戏或动画作品的官方素材或同人图。

## 关于抖音下载

`douyin_downloader.py` 为本项目自身代码，通过 Playwright 驱动用户本地已安装的 Chrome
访问抖音公开页面并提取视频直链。

> 抖音、哔哩哔哩均为其各自权利人的商标。本项目与二者无任何关联。
