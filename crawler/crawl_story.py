import os
import json
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "browser_profile"
STORY_URL = "https://nettruyen.me.uk/truyen-tranh/do-de-cua-ta-deu-la-dai-phan-phai" # Ví dụ

def crawl_story_detail(url):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # Click "Xem thêm" nếu có để hiện đầy đủ chapter
        try:
            if page.query_selector(".show-more"):
                page.click(".show-more")
                page.wait_for_timeout(1000)
        except:
            pass

        chapters = []
        rows = page.query_selector_all("#nt_listchapter ul li.row:not(.heading)")
        
        for row in rows:
            link = row.query_selector("a")
            if link:
                chapters.append({
                    "name": link.inner_text().strip(),
                    "url": link.get_attribute("href")
                })

        data = {
            "title": page.query_selector("h1.title-detail").inner_text(),
            "chapters": chapters
        }

        # Lưu dữ liệu truyện
        manga_id = url.split('/')[-1]
        with open(f"../data/{manga_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Đã lấy xong {len(chapters)} chương của truyện.")
        context.close()

if __name__ == "__main__":
    crawl_story_detail(STORY_URL)