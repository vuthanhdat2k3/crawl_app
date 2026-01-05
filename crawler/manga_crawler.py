"""
Manga Crawler - Thu thập dữ liệu từ NetTruyen
Lưu trữ: CHỈ SỬ DỤNG CLOUD (MongoDB + ImageKit.io)
Không sử dụng local storage
Ưu tiên FlareSolverr để bypass Cloudflare (cả local và production)
"""

import os
import re
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# Import database và image storage
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import db
from imagekit_storage import image_storage
from crawler.flaresolverr_client import flaresolverr

class MangaCrawler:
    def __init__(self):
        self.base_url = "https://nettruyen.me.uk"
        self.user_data_dir = os.path.join(os.path.dirname(__file__), "browser_profile")
        
        # Kết nối cloud storage
        db.connect()
        image_storage.connect()
        print("☁️ Cloud-Only Mode: MongoDB + ImageKit")
        
        # Kiểm tra FlareSolverr (ưu tiên dùng cả local và production)
        self.use_flaresolverr = flaresolverr.check_connection()
        if self.use_flaresolverr:
            print("🚀 FlareSolverr Mode: Ưu tiên FlareSolverr cho tất cả requests")
        
        # Session cho requests (dùng cookies từ FlareSolverr)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": self.base_url
        })
        
        # Cookies từ FlareSolverr để bypass Cloudflare
        self.cf_cookies = None

    def _get_browser_context(self, playwright):
        """Tạo browser context với anti-bot (fallback khi không có FlareSolverr)"""
        return playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )

    def _update_session_cookies(self, cookies):
        """Cập nhật cookies từ FlareSolverr vào session requests"""
        self.cf_cookies = cookies
        for cookie in cookies:
            self.session.cookies.set(cookie.get("name"), cookie.get("value"))

    def upload_cover_via_requests(self, manga_id, thumbnail_url):
        """Tải và upload ảnh bìa lên ImageKit sử dụng requests (cho FlareSolverr)"""
        if not thumbnail_url:
            return None
        
        try:
            # Dùng cookies từ FlareSolverr nếu có
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "Referer": self.base_url,
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            
            # Set cookies từ FlareSolverr
            cookies = {}
            if self.cf_cookies:
                for cookie in self.cf_cookies:
                    cookies[cookie.get('name')] = cookie.get('value')
            
            response = requests.get(thumbnail_url, headers=headers, cookies=cookies, timeout=30)
            if response.status_code == 200 and len(response.content) > 1000:
                # Upload lên ImageKit
                url = image_storage.upload_from_bytes(
                    response.content, 
                    "manga/covers", 
                    f"{manga_id}.jpg"
                )
                if url:
                    print(f"  ☁️ Uploaded cover: {manga_id}")
                    return url
        except Exception as e:
            print(f"  ⚠️ Lỗi upload cover {manga_id}: {e}")
        
        return thumbnail_url  # Fallback về URL gốc

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
        
        # Ưu tiên FlareSolverr
        if self.use_flaresolverr:
            manga_list = self._crawl_home_via_flaresolverr(download_covers)
            if manga_list:
                return manga_list
            print("⚠️ FlareSolverr thất bại, thử Playwright...")
        
        # Fallback: Playwright
        return self._crawl_home_via_playwright(download_covers)
    
    def _crawl_home_via_flaresolverr(self, download_covers=True):
        """Crawl trang chủ qua FlareSolverr"""
        print("🔓 Đang crawl trang chủ qua FlareSolverr...")
        
        result = flaresolverr.get_page(self.base_url)
        if not result or not result.get("html"):
            print("❌ FlareSolverr không thể lấy được trang")
            return None
        
        # Lưu cookies để dùng cho các request khác
        self._update_session_cookies(result.get("cookies", []))
        
        html = result["html"]
        soup = BeautifulSoup(html, "lxml")
        
        manga_list = []
        items = soup.select(".item")
        
        # Thu thập thông tin trước
        manga_data = []
        for item in items:
            title_el = item.select_one("h3 a")
            img_el = item.select_one("img")
            
            if title_el:
                href = title_el.get('href', '')
                manga_id = href.split('/')[-1] if href else ''
                
                thumbnail_original = ""
                if img_el:
                    thumbnail_original = img_el.get('data-original') or img_el.get('data-src') or img_el.get('src', '')
                
                latest_chapter = ""
                chapter_el = item.select_one(".comic-item .chapter a") or item.select_one(".chapter a")
                if chapter_el:
                    latest_chapter = chapter_el.get_text(strip=True)
                
                manga_data.append({
                    "id": manga_id,
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "thumbnail_original": thumbnail_original,
                    "latest_chapter": latest_chapter
                })
        
        # Upload covers song song nếu cần
        if download_covers and manga_data:
            print(f"☁️ Upload {len(manga_data)} covers song song...")
            thumbnails = self._upload_covers_parallel(manga_data)
            for i, manga in enumerate(manga_data):
                manga["thumbnail"] = thumbnails.get(manga["id"], manga["thumbnail_original"])
        
        # Tạo manga_list
        for manga in manga_data:
            manga_list.append({
                "id": manga["id"],
                "title": manga["title"],
                "url": manga["url"],
                "thumbnail": manga.get("thumbnail", manga["thumbnail_original"]),
                "thumbnail_original": manga["thumbnail_original"],
                "latest_chapter": manga["latest_chapter"]
            })
            print(f"  ✅ {manga['title'][:40]}...")
        
        # Lưu vào MongoDB
        db.save_manga_list(manga_list)
        print(f"☁️ Đã lưu {len(manga_list)} truyện vào MongoDB")
        
        return manga_list
    
    def _upload_covers_parallel(self, manga_data):
        """Upload nhiều cover song song"""
        results = {}
        
        def upload_one(manga):
            thumbnail = self.upload_cover_via_requests(manga["id"], manga["thumbnail_original"])
            return manga["id"], thumbnail
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(upload_one, m): m["id"] for m in manga_data if m["thumbnail_original"]}
            for future in as_completed(futures):
                try:
                    manga_id, thumbnail = future.result()
                    results[manga_id] = thumbnail
                except Exception as e:
                    print(f"  ⚠️ Upload cover lỗi: {e}")
        
        return results
    
    def _crawl_home_via_playwright(self, download_covers=True):
        """Crawl trang chủ qua Playwright (fallback)"""
        from playwright.sync_api import sync_playwright
        
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
        
        # Ưu tiên dùng FlareSolverr trên production
        if self.use_flaresolverr:
            data = self._crawl_story_via_flaresolverr(manga_id, url, download_cover)
            if data and data.get('title'):
                return data
            print("⚠️ FlareSolverr thất bại, thử Playwright...")
        
        # Fallback: Sử dụng Playwright
        return self._crawl_story_via_playwright(manga_id, url, download_cover)
    
    def _crawl_story_via_flaresolverr(self, manga_id, url, download_cover=True):
        """Crawl story detail qua FlareSolverr"""
        print(f"🔓 Đang bypass Cloudflare qua FlareSolverr...")
        
        result = flaresolverr.get_page(url)
        if not result or not result.get("html"):
            print("❌ FlareSolverr không thể lấy được trang")
            return None
        
        # Lưu cookies từ FlareSolverr để dùng cho requests
        self.cf_cookies = result.get("cookies", [])
        
        html = result["html"]
        soup = BeautifulSoup(html, "lxml")
        
        # Lấy và upload thumbnail qua requests
        thumbnail_original = ""
        thumb_el = soup.select_one(".col-image img")
        if thumb_el:
            thumbnail_original = thumb_el.get('data-original') or thumb_el.get('data-src') or thumb_el.get('src', '')
        
        thumbnail = thumbnail_original
        if download_cover and thumbnail_original:
            thumbnail = self.upload_cover_via_requests(manga_id, thumbnail_original)
        
        return self._parse_story_detail(soup, manga_id, download_cover, thumbnail, thumbnail_original)
    
    def _crawl_story_via_playwright(self, manga_id, url, download_cover=True):
        """Crawl story detail qua Playwright (fallback)"""
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            context = self._get_browser_context(p)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            
            print("📜 Đang phân tích chapters...")
            
            content = page.content()
            soup = BeautifulSoup(content, "lxml")
            
            # Upload cover nếu dùng Playwright
            thumbnail_original = ""
            thumb_el = soup.select_one(".col-image img")
            if thumb_el:
                thumbnail_original = thumb_el.get('data-original') or thumb_el.get('data-src') or thumb_el.get('src', '')
            
            thumbnail = thumbnail_original
            if download_cover and thumbnail_original:
                thumbnail = self.upload_cover(page, manga_id, thumbnail_original)
            
            data = self._parse_story_detail(soup, manga_id, download_cover, thumbnail, thumbnail_original)
            
            context.close()
            return data
    
    def _parse_story_detail(self, soup, manga_id, download_cover=True, thumbnail=None, thumbnail_original=None):
        """Parse HTML để lấy thông tin truyện"""
        print("📜 Đang phân tích chapters...")
        
        # Lấy thông tin truyện
        title = ""
        title_el = soup.select_one("h1.title-detail")
        if title_el:
            title = title_el.get_text(strip=True)
        
        description = ""
        desc_el = soup.select_one(".detail-content p")
        if desc_el:
            description = desc_el.get_text(strip=True)
        
        # Lấy thumbnail nếu chưa có
        if not thumbnail_original:
            thumb_el = soup.select_one(".col-image img")
            if thumb_el:
                thumbnail_original = thumb_el.get('data-original') or thumb_el.get('data-src') or thumb_el.get('src', '')
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
        
        # Lấy trạng thái
        status = ""
        status_el = soup.select_one(".status.row .col-xs-8")
        if status_el:
            status = status_el.get_text(strip=True)
        
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
            "status": status,
            "genres": genres,
            "chapters": chapters,
            "total_chapters": len(chapters)
        }
        
        # Lưu vào MongoDB (cả manga_details và mangas)
        db.save_manga_detail(data)
        
        # Thêm vào danh sách manga trên trang chủ
        manga_item = {
            "id": manga_id,
            "title": title,
            "url": f"{self.base_url}/truyen-tranh/{manga_id}",
            "thumbnail": thumbnail,
            "thumbnail_original": thumbnail_original,
            "latest_chapter": chapters[0]["name"] if chapters else ""
        }
        db.save_manga_list([manga_item])
        
        print(f"☁️ Đã lưu '{title}' với {len(chapters)} chapters vào MongoDB")
        
        return data

    def _download_chapter_via_flaresolverr(self, manga_id, chapter_id, chapter_url):
        """Download chapter sử dụng FlareSolverr - Download + Upload song song"""
        print(f"🔓 Đang bypass Cloudflare qua FlareSolverr...")
        
        result = flaresolverr.get_page(chapter_url)
        if not result or not result.get("html"):
            print("❌ FlareSolverr không thể lấy được trang")
            return []
        
        html = result["html"]
        soup = BeautifulSoup(html, "lxml")
        
        # Tìm tất cả ảnh chapter
        imgs = soup.select(".reading-detail img, .page-chapter img, .reading img")
        
        if not imgs:
            print(f"⚠️ Không tìm thấy ảnh trong chapter")
            return []
        
        print(f"☁️ Tìm thấy {len(imgs)} ảnh. Download + Upload song song...")
        
        folder_path = f"manga/{manga_id}/{chapter_id}"
        
        # Cập nhật cookies từ FlareSolverr vào session
        self._update_session_cookies(result.get("cookies", []))
        
        if result.get("user_agent"):
            self.session.headers["User-Agent"] = result["user_agent"]
        
        # Download và Upload song song trong cùng 1 task
        def download_and_upload(item):
            idx, img = item
            src = img.get("data-original") or img.get("data-src") or img.get("src")
            if not src:
                return None
            if "http" not in src:
                if src.startswith("//"):
                    src = "https:" + src
                else:
                    return None
            try:
                # Download
                response = self.session.get(src, timeout=30)
                if response.status_code == 200 and len(response.content) > 1000:
                    # Upload ngay sau khi download xong
                    filename = f"{idx:03d}.jpg"
                    url = image_storage.upload_from_bytes(response.content, folder_path, filename)
                    if url:
                        return (idx, url)
            except Exception as e:
                print(f"  ❌ Ảnh {idx} lỗi: {e}")
            return None
        
        # Chạy song song: download + upload cùng lúc
        urls = [None] * len(imgs)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(download_and_upload, (idx, img)): idx for idx, img in enumerate(imgs)}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    idx, url = result
                    urls[idx] = url
                    completed += 1
                    print(f"  ☁️ [{completed}/{len(imgs)}] Downloaded + Uploaded")
        
        # Lọc bỏ None
        urls = [url for url in urls if url]
        print(f"✅ Hoàn thành {len(urls)}/{len(imgs)} ảnh")
        
        return urls

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
        
        # Ưu tiên sử dụng FlareSolverr để bypass Cloudflare (cho production)
        if self.use_flaresolverr:
            urls = self._download_chapter_via_flaresolverr(manga_id, chapter_id, chapter_url)
            if urls:
                db.save_chapter_images(manga_id, chapter_id, urls)
                print(f"☁️ Đã lưu {len(urls)} URLs vào MongoDB (via FlareSolverr)")
                return urls
            else:
                print("⚠️ FlareSolverr thất bại, thử Playwright...")
        
        # Fallback: Sử dụng Playwright (hoạt động tốt trên local)
        try:
            urls = self._download_chapter_via_playwright(manga_id, chapter_id, chapter_url)
            if urls:
                db.save_chapter_images(manga_id, chapter_id, urls)
                print(f"☁️ Đã lưu {len(urls)} URLs vào MongoDB")
            return urls
        except Exception as e:
            print(f"❌ Lỗi Playwright: {e}")
            return []

    def _download_chapter_via_playwright(self, manga_id, chapter_id, chapter_url):
        """Download chapter sử dụng Playwright (fallback khi không có FlareSolverr)"""
        from playwright.sync_api import sync_playwright
        
        print("🎭 Đang sử dụng Playwright (fallback)...")
        
        with sync_playwright() as p:
            context = self._get_browser_context(p)
            page = context.new_page()
            
            # Additional anti-detection measures
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)
            
            page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)
            
            # BYPASS LOGIC 2.0
            max_retries = 3
            for attempt in range(max_retries):
                page_title = page.title()
                print(f"  📄 [{attempt+1}/{max_retries}] Page Title: {page_title}")
                
                if "Just a moment" in page_title or "Attention Required" in page_title or "Cloudflare" in page_title:
                    print("  🛡️ Detect Cloudflare! Waiting for redirect...")
                    page.wait_for_timeout(5000)
                    
                    try:
                         frames = page.frames
                         for frame in frames:
                             if "challenge" in frame.url:
                                 print("  🖱️ Found Challenge Frame, trying to interact...")
                                 frame.click("body", timeout=2000)
                    except: pass
                    
                    page.wait_for_timeout(5000)
                else:
                    break
            
            # Cuộn trang để load lazy images
            print("📜 Đang kích hoạt lazy loading...")
            for i in range(10):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(800)
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            
            try:
                page.wait_for_selector(".reading-detail img, .page-chapter img", timeout=5000)
            except:
                print("  ⚠️ Timeout chờ ảnh...")

            # Lấy tất cả ảnh
            imgs = page.query_selector_all(".reading-detail img, .page-chapter img, .reading img, #image-0")
            
            folder_path = f"manga/{manga_id}/{chapter_id}"
            
            print(f"☁️ Tìm thấy {len(imgs)} ảnh. Download + Upload song song...")
            
            # Thu thập tất cả src trước
            img_sources = []
            for idx, img in enumerate(imgs):
                src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                if src:
                    if "http" not in src:
                        if src.startswith("//"):
                            src = "https:" + src
                        else:
                            continue
                    img_sources.append((idx, src))
            
            # Tải ảnh qua Playwright và lưu vào dict
            downloaded = {}
            for idx, src in img_sources:
                try:
                    response = page.request.get(src, headers={"referer": self.base_url + "/"})
                    if response.status == 200:
                        downloaded[idx] = response.body()
                        print(f"  📥 Downloaded {len(downloaded)}/{len(img_sources)}")
                except Exception as e:
                    print(f"  ❌ Lỗi download {idx}: {e}")
            
            context.close()
        
        # Upload song song sau khi đóng browser
        if downloaded:
            print(f"☁️ Upload {len(downloaded)} ảnh song song...")
            
            def upload_one(item):
                idx, data = item
                filename = f"{idx:03d}.jpg"
                return idx, image_storage.upload_from_bytes(data, folder_path, filename)
            
            urls = [None] * (max(downloaded.keys()) + 1)
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(upload_one, item): item[0] for item in downloaded.items()}
                for future in as_completed(futures):
                    try:
                        idx, url = future.result()
                        if url:
                            urls[idx] = url
                            print(f"  ☁️ Uploaded {sum(1 for u in urls if u)}/{len(downloaded)}")
                    except Exception as e:
                        print(f"  ❌ Upload error: {e}")
            
            return [url for url in urls if url]
        
        return []

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
