# -*- coding: utf-8 -*-
"""可选：用 Playwright 重拍 Word 案例里引用的演示截图 outputs/img/demo.png
（载入示例数据 → 筛选「质量安全」）。只在演示页改版后需要运行；pip install playwright && playwright install chromium。
运行：python src/09_screenshot.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'demo' / '投诉分拣演示.html'
OUT = ROOT / 'outputs' / 'img' / 'demo.png'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1.5)
    page.goto(PAGE.as_uri())
    page.click('#btn-sample')
    page.check('input[name="cat"][value="质量安全"]')
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT), full_page=False)
    browser.close()
print('写出：', OUT)
