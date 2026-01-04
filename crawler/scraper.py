import os
import json
import time
from playwright.sync_api import sync_playwright

class MangaScraper:
    def __init__(self, user_data_dir="browser_profile"):
        self.user_data_dir = user_data_dir
        self.base_url = "https://nettruyen.me.uk"

    def start_browser(self, p):
        # Sử dụng Persistent Context để giữ session và né bot detection
        context = p.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=False, # Để False nếu cần manual verify Cloudflare lần đầu
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        return context

    def get_home_manga(self):
        """Lấy danh sách truyện mới nhất từ trang chủ"""
        with sync_playwright() as p:
            context = self.start_browser(p)
            page = context.new_page()
            page.goto(self.base_url, wait_until="networkidle")
            
            manga_list = []
            items = page.query_selector_all(".item")
            
            for item in items:
                title_el = item.query_selector("h3 a")
                img_el = item.query_selector("img")
                if title_el:
                    manga_list.append({
                        "title": title_el.inner_text(),
                        "url": title_el.get_attribute("href"),
                        "thumbnail": img_el.get_attribute("src") if img_el else "",
                        "id": title_el.get_attribute("href").split("/")[-1]
                    })
            context.close()
            return manga_list

    def download_chapter(self, chapter_url, save_path):
        """Tải toàn bộ ảnh của một chương"""
        if not os.path.exists(save_path): os.makedirs(save_path)
        
        with sync_playwright() as p:
            context = self.start_browser(p)
            page = context.new_page()
            page.goto(chapter_url, wait_until="domcontentloaded")
            
            # Cuộn trang để kích hoạt Lazy Load
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)

            imgs = page.query_selector_all(".reading-detail img")
            for idx, img in enumerate(imgs):
                src = img.get_attribute("data-src") or img.get_attribute("src")
                if src and "http" in src:
                    # Tải ảnh qua page.request để giữ Referer (tránh 403)
                    response = page.request.get(src, headers={"referer": self.base_url})
                    with open(f"{save_path}/{idx:03d}.jpg", "wb") as f:
                        f.write(response.body())
            context.close()