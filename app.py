import os
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://nettruyen.me.uk/trang-chu"

# Kiểm tra xem đang chạy trên Vercel (serverless) hay local
IS_VERCEL = os.environ.get('VERCEL', False) or os.environ.get('VERCEL_ENV', False)

# Trên Vercel, chỉ /tmp mới có thể ghi được
if IS_VERCEL:
    DATA_DIR = "/tmp/data"
    USER_DATA_DIR = "/tmp/crawler/browser_profile"
else:
    DATA_DIR = "data"
    USER_DATA_DIR = "crawler/browser_profile"

# Chỉ tạo thư mục khi không chạy trong serverless context hoặc khi sử dụng /tmp
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    pass  # Bỏ qua lỗi nếu không thể tạo thư mục

def crawl_home():
    with sync_playwright() as p:
        # Sử dụng persistent context để giữ session và né bot
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()
        print("🌍 Đang truy cập trang chủ NetTruyen...")
        
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        
        # Lấy nội dung HTML sau khi đã load xong
        content = page.content()
        soup = BeautifulSoup(content, "lxml")
        
        manga_list = []
        items = soup.select(".item")
        
        for item in items:
            title_el = item.select_one("h3 a")
            img_el = item.select_one("img")
            
            if title_el:
                manga_list.append({
                    "id": title_el['href'].split('/')[-1],
                    "title": title_el.get_text(strip=True),
                    "url": title_el['href'],
                    "thumbnail": img_el['data-original'] if img_el.has_attr('data-original') else img_el['src']
                })

        # Lưu vào file JSON để Web Flask sử dụng
        with open(os.path.join(DATA_DIR, "manga_list.json"), "w", encoding="utf-8") as f:
            json.dump(manga_list, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Đã lưu {len(manga_list)} truyện vào data/manga_list.json")
        context.close()

if __name__ == "__main__":
    crawl_home()