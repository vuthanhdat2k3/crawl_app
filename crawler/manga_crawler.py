"""
Manga Crawler - Thu thập dữ liệu từ NetTruyen
Lưu trữ: CHỈ SỬ DỤNG CLOUD (MongoDB + ImageKit.io)
Không sử dụng local storage
"""

import os
import re
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Import database và image storage
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import db
from imagekit_storage import image_storage

class MangaCrawler:
    def __init__(self):
        self.base_url = "https://nettruyen.me.uk/"
        self.user_data_dir = os.path.join(os.path.dirname(__file__), "browser_profile")
        
        # Kết nối cloud storage
        db.connect()
        image_storage.connect()
        print("☁️ Cloud-Only Mode: MongoDB + ImageKit")

    def _get_browser_context(self, playwright):
        """Tạo browser context với anti-bot"""
        return playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )

    def upload_cover(self, page, manga_id, thumbnail_url):
        """Tải và upload ảnh bìa lên ImageKit"""
        if not thumbnail_url:
            return None
        
        try:
            # Tải ảnh từ nguồn
            response = page.request.get(thumbnail_url, headers={"referer": self.base_url + "/"})
            if response.status == 200:
                # Upload trực tiếp lên ImageKit
                image_bytes = response.body()
                url = image_storage.upload_from_bytes(
                    image_bytes, 
                    "manga/covers", 
                    f"{manga_id}.jpg"
                )
                if url:
                    print(f"  ☁️ Uploaded cover: {manga_id}")
                    return url
        except Exception as e:
            print(f"  ⚠️ Lỗi upload cover {manga_id}: {e}")
        
        return thumbnail_url  # Fallback về URL gốc

    def crawl_home(self, download_covers=True):
        """Crawl danh sách manga từ trang chủ - LƯU VÀO MONGODB"""
        print("🌍 Đang crawl trang chủ NetTruyen...")
        
        with sync_playwright() as p:
            context = self._get_browser_context(p)
            page = context.new_page()
            page.goto(self.base_url, wait_until="networkidle", timeout=60000)
            
            # Cuộn để load thêm
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
            
            content = page.content()
            soup = BeautifulSoup(content, "lxml")
            
            manga_list = []
            items = soup.select(".item")
            
            for idx, item in enumerate(items):
                title_el = item.select_one("h3 a")
                img_el = item.select_one("img")
                
                if title_el:
                    href = title_el.get('href', '')
                    manga_id = href.split('/')[-1] if href else ''
                    
                    # Lấy thumbnail gốc
                    thumbnail_original = ""
                    if img_el:
                        thumbnail_original = img_el.get('data-original') or img_el.get('data-src') or img_el.get('src', '')
                    
                    # Upload cover lên ImageKit
                    thumbnail = thumbnail_original
                    if download_covers and thumbnail_original:
                        uploaded_url = self.upload_cover(page, manga_id, thumbnail_original)
                        if uploaded_url:
                            thumbnail = uploaded_url
                    
                    # Lấy chapter mới nhất
                    latest_chapter = ""
                    chapter_el = item.select_one(".comic-item .chapter a") or item.select_one(".chapter a")
                    if chapter_el:
                        latest_chapter = chapter_el.get_text(strip=True)
                    
                    manga_list.append({
                        "id": manga_id,
                        "title": title_el.get_text(strip=True),
                        "url": href,
                        "thumbnail": thumbnail,
                        "thumbnail_original": thumbnail_original,
                        "latest_chapter": latest_chapter
                    })
                    
                    print(f"  [{idx+1}/{len(items)}] {title_el.get_text(strip=True)[:30]}...")
            
            # Lưu vào MongoDB
            db.save_manga_list(manga_list)
            print(f"☁️ Đã lưu {len(manga_list)} truyện vào MongoDB")
            
            context.close()
            return manga_list

    def crawl_story_detail(self, manga_id, download_cover=True):
        """Crawl chi tiết một truyện - LƯU VÀO MONGODB"""
        url = f"{self.base_url}/truyen-tranh/{manga_id}"
        print(f"📖 Đang crawl chi tiết truyện: {manga_id}")
        
        with sync_playwright() as p:
            context = self._get_browser_context(p)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            
            print("📜 Đang phân tích chapters...")
            
            content = page.content()
            soup = BeautifulSoup(content, "lxml")
            
            # Lấy thông tin truyện
            title = ""
            title_el = soup.select_one("h1.title-detail")
            if title_el:
                title = title_el.get_text(strip=True)
            
            description = ""
            desc_el = soup.select_one(".detail-content p")
            if desc_el:
                description = desc_el.get_text(strip=True)
            
            # Lấy và upload thumbnail
            thumbnail_original = ""
            thumbnail = ""
            thumb_el = soup.select_one(".col-image img")
            if thumb_el:
                thumbnail_original = thumb_el.get('data-original') or thumb_el.get('data-src') or thumb_el.get('src', '')
            
            if download_cover and thumbnail_original:
                thumbnail = self.upload_cover(page, manga_id, thumbnail_original)
            else:
                thumbnail = thumbnail_original
            
            # Lấy thể loại
            genres = []
            genre_els = soup.select(".kind.row .col-xs-8 a")
            for g in genre_els:
                genres.append(g.get_text(strip=True))
            
            # Lấy tác giả
            author = ""
            author_el = soup.select_one(".author.row .col-xs-8")
            if author_el:
                author = author_el.get_text(strip=True)
            
            # Phân tích pattern chapters
            visible_rows = soup.select("#nt_listchapter ul li.row:not(.heading)")
            
            chapters = []
            chapter_pattern = None
            max_chapter = 0
            min_chapter = float('inf')
            
            for row in visible_rows:
                link = row.select_one("a")
                if link:
                    chap_url = link.get('href', '')
                    
                    url_match = re.search(r'[/-](chuong|chap|chapter)[/-]?(\d+)', chap_url, re.IGNORECASE)
                    if url_match:
                        chapter_num = int(url_match.group(2))
                        prefix = url_match.group(1).lower()
                        
                        if not chapter_pattern:
                            base_url = re.sub(r'[/-](chuong|chap|chapter)[/-]?\d+.*$', '', chap_url, flags=re.IGNORECASE)
                            chapter_pattern = {
                                'base_url': base_url,
                                'prefix': prefix,
                                'separator': '-' if f'{prefix}-' in chap_url.lower() else ''
                            }
                        
                        max_chapter = max(max_chapter, chapter_num)
                        min_chapter = min(min_chapter, chapter_num)
            
            print(f"  📊 Phân tích: Chapter {min_chapter} → {max_chapter}")
            
            # Generate tất cả chapters
            if chapter_pattern and max_chapter > 0:
                for i in range(max_chapter, -1, -1):
                    chap_id = f"{chapter_pattern['prefix']}{chapter_pattern['separator']}{i}"
                    chap_url = f"{chapter_pattern['base_url']}/{chap_id}"
                    
                    if not chap_url.startswith('http'):
                        chap_url = self.base_url + chap_url
                    
                    chapters.append({
                        "id": chap_id,
                        "name": f"Chapter {i}",
                        "url": chap_url
                    })
                
                print(f"  ✅ Đã generate {len(chapters)} chapters!")
            else:
                # Fallback
                for row in visible_rows:
                    link = row.select_one("a")
                    if link:
                        chap_url = link.get('href', '')
                        chap_id = chap_url.split('/')[-1] if chap_url else ''
                        if not chap_url.startswith('http'):
                            chap_url = self.base_url + chap_url
                        chapters.append({
                            "id": chap_id,
                            "name": link.get_text(strip=True),
                            "url": chap_url
                        })
            
            # Chuẩn bị dữ liệu
            data = {
                "id": manga_id,
                "title": title,
                "description": description,
                "thumbnail": thumbnail,
                "thumbnail_original": thumbnail_original,
                "author": author,
                "genres": genres,
                "chapters": chapters,
                "total_chapters": len(chapters)
            }
            
            # Lưu vào MongoDB
            db.save_manga_detail(data)
            print(f"☁️ Đã lưu '{title}' với {len(chapters)} chapters vào MongoDB")
            
            context.close()
            return data

    def download_chapter_images(self, manga_id, chapter_id, chapter_url=None):
        """Tải và upload ảnh chapter lên ImageKit - LƯU URLs VÀO MONGODB"""
        if not chapter_url:
            chapter_url = f"{self.base_url}/truyen-tranh/{manga_id}/{chapter_id}"
        
        # Kiểm tra đã có trên cloud chưa
        existing_urls = db.get_chapter_images(manga_id, chapter_id)
        if existing_urls:
            print(f"⏭️ Chapter {chapter_id} đã có trên cloud ({len(existing_urls)} ảnh)")
            return existing_urls
        
        print(f"📥 Đang tải và upload chapter: {chapter_id}")
        
        with sync_playwright() as p:
            context = self._get_browser_context(p)
            page = context.new_page()
            # Enable Stealth Mode
            from playwright_stealth import stealth_sync
            stealth_sync(page)
            
            page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)
            
            # BYPASS LOGIC 2.0
            max_retries = 3
            for attempt in range(max_retries):
                page_title = page.title()
                print(f"  📄 [{attempt+1}/{max_retries}] Page Title: {page_title}")
                
                if "Just a moment" in page_title or "Attention Required" in page_title or "Cloudflare" in page_title:
                    print("  🛡️ Detect Cloudflare! Waiting for redirect...")
                    page.wait_for_timeout(5000)
                    
                    # Thử click vào bất kỳ iframe/checkbox nào nếu có (basic attempt)
                    try:
                         frames = page.frames
                         for frame in frames:
                             if "challenge" in frame.url:
                                 print("  🖱️ Found Challenge Frame, trying to interact...")
                                 frame.click("body", timeout=2000)
                    except: pass
                    
                    page.wait_for_timeout(5000)
                else:
                    # Đã vào được trang chính
                    break
            
            # Cuộn trang chậm hơn để giả lập người dùng
            print("📜 Đang kích hoạt lazy loading...")
            for i in range(10): # Tăng số lần cuộn
                page.mouse.wheel(0, 1000) # Dùng mouse wheel thay vì scrollTo cho giống người
                page.wait_for_timeout(1000)
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
            
            # Chờ ảnh xuất hiện (quan trọng)
            try:
                page.wait_for_selector(".reading-detail img, .page-chapter img", timeout=5000)
            except:
                print("  ⚠️ Timeout chờ ảnh, thử selector khác...")

            # Lấy tất cả ảnh with enhanced selectors
            imgs = page.query_selector_all(".reading-detail img, .page-chapter img, .reading img, #image-0")
            
            urls = []
            folder_path = f"manga/{manga_id}/{chapter_id}"
            
            print(f"☁️ Tìm thấy {len(imgs)} element ảnh. Bắt đầu upload...")
            
            for idx, img in enumerate(imgs):
                # Thử nhiều attribute chứa link ảnh
                src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                
                if not src:
                    continue
                    
                if "http" not in src:
                     if src.startswith("//"):
                         src = "https:" + src
                     else:
                         continue

                try:
                    response = page.request.get(src, headers={"referer": self.base_url + "/"})
                    if response.status == 200:
                        filename = f"{idx:03d}.jpg"
                        
                        # Upload trực tiếp lên ImageKit
                        url = image_storage.upload_from_bytes(
                            response.body(),
                            folder_path,
                            filename
                        )
                        
                        if url:
                            urls.append(url)
                            print(f"  ☁️ [{idx+1}/{len(imgs)}] Uploaded")
                        else:
                            print(f"  ❌ [{idx+1}/{len(imgs)}] Upload failed")
                except Exception as e:
                    print(f"  ❌ Lỗi ảnh {idx}: {e}")
            
            context.close()
            
            # Lưu URLs vào MongoDB
            if urls:
                db.save_chapter_images(manga_id, chapter_id, urls)
                print(f"☁️ Đã lưu {len(urls)} URLs vào MongoDB")
            
            return urls

    def get_manga_list(self):
        """Lấy danh sách manga từ MongoDB"""
        mangas = db.get_manga_list(limit=200)
        # Chuyển ObjectId thành string
        for m in mangas:
            if '_id' in m:
                m['_id'] = str(m['_id'])
        return mangas

    def get_story_data(self, manga_id):
        """Lấy chi tiết truyện từ MongoDB"""
        data = db.get_manga_detail(manga_id)
        if data and '_id' in data:
            data['_id'] = str(data['_id'])
        return data

    def get_chapter_images(self, manga_id, chapter_id):
        """Lấy danh sách URLs ảnh từ MongoDB"""
        return db.get_chapter_images(manga_id, chapter_id)
    
    def get_download_status(self, manga_id):
        """Lấy trạng thái tải từ MongoDB"""
        return db.get_download_status(manga_id)
        
    def get_downloaded_chapters(self, manga_id):
        """Lấy danh sách chapter IDs đã tải"""
        return db.get_downloaded_chapters(manga_id)


# CLI Interface
if __name__ == "__main__":
    import sys
    
    crawler = MangaCrawler()
    
    if len(sys.argv) < 2:
        print("""
╔═══════════════════════════════════════════════════════════╗
║           🎌 MANGA CRAWLER - CLOUD ONLY MODE 🎌           ║
╠═══════════════════════════════════════════════════════════╣
║  Lưu trữ: MongoDB (data) + ImageKit (ảnh 20GB free)       ║
╠═══════════════════════════════════════════════════════════╣
║  Cách sử dụng:                                            ║
║   python manga_crawler.py home                            ║
║   python manga_crawler.py story <manga-id>                ║
║   python manga_crawler.py chapter <manga-id> <chapter-id> ║
╚═══════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "home":
        crawler.crawl_home()
    
    elif command == "story" and len(sys.argv) >= 3:
        manga_id = sys.argv[2]
        crawler.crawl_story_detail(manga_id)
    
    elif command == "chapter" and len(sys.argv) >= 4:
        manga_id = sys.argv[2]
        chapter_id = sys.argv[3]
        crawler.download_chapter_images(manga_id, chapter_id)
    
    else:
        print("❌ Lệnh không hợp lệ!")
        print("Sử dụng: python manga_crawler.py [home|story|chapter] [args...]")
