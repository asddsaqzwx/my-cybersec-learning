#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载小工具

原理流程：
  1. 用 Playwright 驱动本机 Edge/Chrome 打开视频详情页，自动过 byted_acrawler 反爬挑战；
  2. 页面本身会调用签名接口 /aweme/v1/web/aweme/detail/，我们只监听抓包，不需要自己算 a_bogus；
  3. 从返回 JSON 的 video.bit_rate 里挑选码率最高的 play_addr 直链；
  4. 用 requests 下载（带 UA/Referer），校验 MP4 头与时长。

用法：
  python douyin_video_downloader.py 7687127366488974501 -o out.mp4
  python douyin_video_downloader.py https://www.douyin.com/video/7687127366488974501 -o out.mp4

依赖：
  pip install playwright requests
  playwright 会复用系统安装的 Edge/Chrome（无需 playwright install download）
"""

import argparse
import asyncio
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

import requests
from playwright.async_api import async_playwright

# 常用浏览器路径（按顺序探测，找到即用）
BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def pick_browser():
    for p in BROWSER_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("未找到 Edge/Chrome，请手动指定浏览器路径")


def extract_play_urls(api_body: str) -> list:
    """从 aweme/detail接口的响应里解析出 {quality, bitrate, url} 列表，按码率降序。"""
    obj = json.loads(api_body)
    detail = obj.get("aweme_detail") or {}
    video = detail.get("video") or {}
    out = []
    for br in video.get("bit_rate", []):
        url_list = (br.get("play_addr") or {}).get("url_list") or []
        if not url_list:
            continue
        out.append({
            "quality": br.get("gear_name", "?"),
            "bitrate": br.get("bit_rate", 0),
            "url": url_list[0],
        })
    return sorted(out, key=lambda x: x["bitrate"], reverse=True)


async def capture_detail_api(video_url: str, browser_path: str, timeout_s: int) -> str:
    """打开视频页，抓取 aweme/detail 接口的响应体，返回 JSON 文本。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=browser_path, headless=True,
                                          args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(user_agent=UA, locale="zh-CN")
        page = await ctx.new_page()

        captured = {}

        async def on_resp(resp):
            u = resp.url
            if "/aweme/v1/web/aweme/detail" in u:
                try:
                    body = await resp.body()
                    if json.loads(body.decode("utf-8", "replace")).get("aweme_detail"):
                        captured["detail"] = body.decode("utf-8", "replace")
                        # 拿到详情后，等页面真正发起视频流请求（Optional，可提前结束等待）
                        media_hint.set()
                except Exception:
                    pass

        page.on("response", on_resp)

        await page.goto(video_url, wait_until="domcontentloaded", timeout=timeout_s * 1000)

        # 轮询等待 detail 接口出现
        for _ in range(timeout_s):
            if "detail" in captured:
                # 抓到后多等 3 秒，让页面也确实发起了 CDN 视频直链请求（便于核对）
                await asyncio.sleep(3)
                break
            await page.wait_for_timeout(1000)

        await browser.close()
        if "detail" not in captured:
            raise RuntimeError("没抓到 aweme/detail 接口，可能遇到登录墙或视频不存在")
        return captured["detail"]


def download(url: str, out_path: str) -> None:
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.douyin.com/",
    }
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)


def verify_mp4(path: str) -> None:
    """校验文件头是否 MP4(ftyp)。"""
    with open(path, "rb") as f:
        head = f.read(12)
    if b"ftyp" in head:
        print(f"OK: {path} 文件头正确 (MP4)")
    else:
        print(f"警告: {path} 文件头异常: {head[:8]}")


def main():
    ap = argparse.ArgumentParser(description="抖音视频下载（学习用途）")
    ap.add_argument("video", help="视频ID 或 douyin.com/video/<id> URL")
    ap.add_argument("-o", "--output", default="douyin_video.mp4", help="输出文件名")
    ap.add_argument("--timeout", type=int, default=45, help="等待接口最长时间(秒)")
    args = ap.parse_args()

    vid = args.video
    m = re.search(r"/video/(\d+)", vid)
    if m:
        vid = m.group(1)

    video_url = f"https://www.douyin.com/video/{vid}"
    browser = pick_browser()
    print(f"[1/4] 用浏览器({os.path.basename(browser)})打开 {video_url}")
    api_body = asyncio.run(capture_detail_api(video_url, browser, args.timeout))

    plays = extract_play_urls(api_body)
    if not plays:
        raise SystemExit("响应里没有可用的 play_addr")
    best = plays[0]
    print(f"[2/4] 已获得 {len(plays)} 档清晰度，选用最高档: "
          f"{best['quality']} @ {best['bitrate']}bps")

    print("[3/4] 开始下载 ...")
    download(best["url"], args.output)
    print(f"[4/4] 下载完成: {args.output}")

    if os.environ.get("DOUYIN_FFPROBE"):
        os.system(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "{args.output}"')
    verify_mp4(args.output)


if __name__ == "__main__":
    main()