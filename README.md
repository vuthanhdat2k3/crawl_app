# 📚 Dự Án Crawl Manga

Dự án thu thập và quản lý truyện tranh từ website NetTruyen sử dụng Python, Playwright và Flask.

## 📋 Mục Lục

- [Giới Thiệu](#giới-thiệu)
- [Cấu Trúc Dự Án](#cấu-trúc-dự-án)
- [Công Nghệ Sử Dụng](#công-nghệ-sử-dụng)
- [Cài Đặt](#cài-đặt)
- [Cách Sử Dụng](#cách-sử-dụng)
- [Chi Tiết Các Module](#chi-tiết-các-module)

## 🎯 Giới Thiệu

Dự án này được xây dựng để:
- **Thu thập dữ liệu** truyện tranh từ NetTruyen (nettruyen.me.uk)
- **Tải xuống hình ảnh** từng chapter một cách tự động
- **Hiển thị truyện** qua giao diện web đơn giản với Flask
- **Vượt qua các biện pháp chống bot** như Cloudflare sử dụng Playwright

## 📁 Cấu Trúc Dự Án

```
crawl_manga/
│
├── app.py                          # Script chính crawl trang chủ
├── requirements.txt                # Danh sách thư viện cần thiết
├── README.md                       # Tài liệu dự án (file này)
│
├── crawler/                        # Thư mục chứa các script crawler
│   ├── crawl_story.py             # Crawl thông tin chi tiết 1 truyện
│   ├── crawl_20_chapters.py       # Crawl 20 chapter đầu tiên
│   ├── crawl_images_one_chapter.py # Crawl hình ảnh từ 1 chapter
│   ├── download_images_playwright.py # Tải hình ảnh sử dụng Playwright
│   ├── test.py                    # File test các tính năng
│   ├── browser_profile/           # Profile trình duyệt để né bot detection
│   ├── downloads/                 # Thư mục lưu ảnh đã tải (theo chapter)
│   └── images/                    # Thư mục backup hình ảnh
│
├── data/                          # Thư mục chứa dữ liệu JSON
│   └── do-de-cua-ta.json         # Dữ liệu chi tiết truyện đã crawl
│
└── web/                           # Thư mục ứng dụng web Flask
    ├── app.py                     # Server Flask
    ├── static/                    # Tài nguyên tĩnh (CSS, images)
    │   ├── style.css             
    │   └── chapters/             # Lưu hình ảnh chapter để hiển thị
    └── templates/                 # HTML templates
        ├── index.html            # Trang chủ
        ├── story.html            # Trang chi tiết truyện
        └── chapter.html          # Trang đọc chapter

```

## 🛠 Công Nghệ Sử Dụng

### Backend & Crawler
- **Python 3.x** - Ngôn ngữ lập trình chính
- **Playwright** - Automation browser, vượt qua các biện pháp chống bot
- **BeautifulSoup4** - Parse HTML và trích xuất dữ liệu
- **Requests** - HTTP requests đơn giản
- **lxml** - Parser HTML/XML nhanh

### Web Framework
- **Flask** - Micro web framework để hiển thị truyện

## 📦 Cài Đặt

### 1. Clone hoặc tải dự án về

```bash
git clone <repository-url>
cd crawl_manga
```

### 2. Cài đặt thư viện Python

```bash
pip install -r requirements.txt
```

### 3. Cài đặt browser cho Playwright

```bash
playwright install chromium
```

## 🚀 Cách Sử Dụng

### 1. Crawl Trang Chủ

Chạy script để lấy danh sách truyện từ trang chủ:

```bash
python app.py
```

### 2. Crawl Chi Tiết Một Truyện

Crawl thông tin đầy đủ của một truyện (tiêu đề, danh sách chapters):

```bash
cd crawler
python crawl_story.py
```

Kết quả được lưu vào `data/do-de-cua-ta.json`

### 3. Crawl 20 Chapters Đầu

Lấy thông tin 20 chapter đầu tiên:

```bash
cd crawler
python crawl_20_chapters.py
```

### 4. Tải Hình Ảnh Một Chapter

Tải toàn bộ hình ảnh của một chapter:

```bash
cd crawler
python download_images_playwright.py
```

Hình ảnh được lưu vào `crawler/downloads/chap_XXX/`

### 5. Chạy Web Server

Xem truyện đã crawl qua giao diện web:

```bash
cd web
python app.py
```

Truy cập: `http://localhost:5000`

## 📖 Chi Tiết Các Module

### `app.py` (Root)

**Chức năng:** Crawl danh sách truyện từ trang chủ NetTruyen

**Đặc điểm:**
- Sử dụng Playwright để mở trình duyệt thật
- Auto-scroll để load thêm truyện (lazy loading)
- Trích xuất tiêu đề và link của từng truyện

**Selector quan trọng:**
```python
items = soup.select(".item")
title = item.select_one("h3 a")
```

### `crawler/crawl_story.py`

**Chức năng:** Crawl toàn bộ thông tin của một truyện cụ thể

**Đặc điểm:**
- Click nút "Xem thêm" để load hết chapters
- Lưu tiêu đề truyện và danh sách chapters
- Xuất ra file JSON trong `data/`

**Dữ liệu thu thập:**
- Tên truyện
- Danh sách chapters (name, url)

### `crawler/crawl_20_chapters.py`

**Chức năng:** Lấy nhanh 20 chapters đầu tiên

**Đặc điểm:**
- Không click "Xem thêm"
- Chỉ lấy những chapter hiển thị ban đầu
- Phục vụ mục đích test nhanh

### `crawler/download_images_playwright.py`

**Chức năng:** Tải hình ảnh từ một chapter cụ thể

**Đặc điểm:**
- **Sử dụng persistent context** để giả lập browser người dùng thật
- **Vượt qua Cloudflare/Anti-bot** bằng cách:
  - Tắt cờ automation: `--disable-blink-features=AutomationControlled`
  - Sử dụng User-Agent thật
  - Lưu browser profile để giữ cookies/session
- **Auto-scroll** để kích hoạt lazy loading
- Lấy ảnh từ attribute `data-src` hoặc `src`
- Tải ảnh qua `page.request.get()` để giữ referer

**Kỹ thuật chống detection:**
```python
context = p.chromium.launch_persistent_context(
    USER_DATA_DIR,
    headless=True,
    args=["--disable-blink-features=AutomationControlled"],
    user_agent="Mozilla/5.0..."
)
```

### `crawler/crawl_images_one_chapter.py`

**Chức năng:** Crawl hình ảnh theo cách đơn giản hơn (nếu không cần vượt bot)

### `web/app.py`

**Chức năng:** Flask web server để xem truyện

**Routes:**
- `/` - Trang chủ (index)
- `/story` - Xem thông tin truyện
- `/chapter/<idx>` - Đọc chapter theo index

**Dữ liệu:** 
- Load từ `data/do-de-cua-ta.json`

### `browser_profile/`

**Chức năng:** Lưu trữ profile trình duyệt Chromium

**Nội dung:**
- Cookies, Local Storage, Session Storage
- Cache, History, Preferences
- Extensions (nếu có)

**Lợi ích:**
- Giữ session giữa các lần chạy
- Né bot detection tốt hơn
- Không phải verify Cloudflare mỗi lần

## ⚠️ Lưu Ý

### 1. Legal & Ethics
- Dự án này chỉ phục vụ mục đích **học tập và nghiên cứu**
- Tôn trọng `robots.txt` và Terms of Service của website
- Không sử dụng để thương mại hóa nội dung

### 2. Rate Limiting
- Thêm delay giữa các requests để tránh quá tải server
- Sử dụng `time.sleep()` hoặc `page.wait_for_timeout()`

### 3. Selectors
- Selectors CSS có thể thay đổi khi website update
- Cần kiểm tra và cập nhật thường xuyên

### 4. Anti-Bot
- Website có thể tăng cường biện pháp chống bot
- Có thể cần thêm CAPTCHA solver hoặc proxy

## 🔧 Cấu Hình

### Thay đổi URL target

Trong mỗi file crawler, tìm và sửa:

```python
BASE_URL = "https://nettruyen.me.uk"
STORY_URL = "https://nettruyen.me.uk/truyen-tranh/..."
CHAPTER_URL = "https://nettruyen.me.uk/truyen-tranh/.../chuong-XXX"
```

### Thay đổi thư mục lưu

```python
SAVE_DIR = "downloads/chap_XXX"
OUT_FILE = "../data/ten-truyen.json"
```

## 📊 Dữ Liệu JSON

Format của file `data/do-de-cua-ta.json`:

```json
{
  "title": "Tên Truyện",
  "chapters": [
    {
      "name": "Chapter 461",
      "url": "https://nettruyen.me.uk/truyen-tranh/.../chuong-461"
    }
  ]
}
```

## 🐛 Troubleshooting

### Lỗi: Không tải được ảnh (403 Forbidden)
- Kiểm tra referer header
- Sử dụng browser context để giữ cookies

### Lỗi: Timeout khi load trang
- Tăng timeout: `page.goto(..., timeout=120000)`
- Kiểm tra kết nối internet
- Website có thể bị chặn/bảo trì

### Lỗi: Không tìm thấy elements
- Inspect website để kiểm tra selectors
- Website có thể đã thay đổi cấu trúc
- Thử dùng XPath thay vì CSS selector

## 📝 TODO / Cải Tiến

- [ ] Thêm multi-threading để tải ảnh nhanh hơn
- [ ] Tích hợp database (SQLite/PostgreSQL)
- [ ] Xây dựng queue system để crawl nhiều truyện
- [ ] Thêm admin panel để quản lý crawl jobs
- [ ] Tối ưu storage (nén ảnh, CDN)
- [ ] Thêm tính năng search và filter
- [ ] Responsive design cho mobile

## 📄 License

Dự án này được tạo ra cho mục đích học tập. Vui lòng tôn trọng bản quyền của nội dung gốc.

## 👤 Tác Giả

Dự án được tạo để thực hành web scraping và automation với Python.

---

**Lưu ý cuối:** Hãy sử dụng công cụ này một cách có trách nhiệm và tuân thủ luật pháp địa phương về sở hữu trí tuệ!
