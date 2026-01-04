import os
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "browser_profile"

def download_chapter(url, manga_id, chap_name):
    save_dir = f"downloads/{manga_id}/{chap_name.replace(' ', '_')}"
    os.makedirs(save_dir, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR, 
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # Cuộn trang để load ảnh (Lazy loading)
        print("📜 Đang kích hoạt load ảnh...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)

        imgs = page.query_selector_all(".reading-detail img")
        
        for idx, img in enumerate(imgs):
            src = img.get_attribute("data-src") or img.get_attribute("src")
            if not src or "http" not in src: continue
            
            # Tải bằng page.request để đính kèm Referer tránh 403
            try:
                response = page.request.get(src, headers={"referer": "https://nettruyen.me.uk/"})
                if response.status == 200:
                    with open(f"{save_dir}/{idx:03d}.jpg", "wb") as f:
                        f.write(response.body())
                    print(f"📸 Đã tải ảnh {idx}")
            except Exception as e:
                print(f"❌ Lỗi ảnh {idx}: {e}")

        context.close()

if __name__ == "__main__":
    test_url = "https://nettruyen.me.uk/truyen-tranh/do-de-cua-ta-deu-la-dai-phan-phai/chuong-461"
    download_chapter(test_url, "do-de-cua-ta", "chap-461")