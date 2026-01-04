"""
Manga Heaven - Web Server
CHỈ SỬ DỤNG CLOUD STORAGE (MongoDB + ImageKit)
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys

# Thêm đường dẫn root để import modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

# Import crawler
from crawler.manga_crawler import MangaCrawler

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Khởi tạo crawler (Cloud-only mode)
try:
    crawler = MangaCrawler()
    print("✅ Crawler initialized successfully")
except Exception as e:
    print(f"❌ Error initializing crawler: {e}")
    import traceback
    traceback.print_exc()
    crawler = None


@app.route('/')
def index():
    """Trang chủ - Lấy từ MongoDB"""
    if crawler is None:
        return render_template('error.html', message="Đang khởi tạo hệ thống, vui lòng thử lại sau...")
    mangas = crawler.get_manga_list()
    return render_template('index.html', mangas=mangas, total=len(mangas))


@app.route('/story/<manga_id>')
def story(manga_id):
    """Trang chi tiết truyện - Lấy từ MongoDB"""
    story_data = crawler.get_story_data(manga_id)
    
    if not story_data:
        try:
            story_data = crawler.crawl_story_detail(manga_id)
        except Exception as e:
            return render_template('error.html', message=f"Không thể tải truyện: {e}")
    
    if not story_data:
        return render_template('error.html', message="Không tìm thấy truyện này")
    
    # Lấy danh sách chapters đã tải
    downloaded_chapters = crawler.get_downloaded_chapters(manga_id)
    
    return render_template('story.html', story=story_data, downloaded_chapters=downloaded_chapters)


@app.route('/reader/<manga_id>/<chapter_id>')
def reader(manga_id, chapter_id):
    """Trang đọc chapter - Lấy URLs từ MongoDB"""
    story_data = crawler.get_story_data(manga_id)
    
    if not story_data:
        try:
            story_data = crawler.crawl_story_detail(manga_id)
        except:
            story_data = {"title": manga_id, "chapters": []}
    
    # Tìm chapter hiện tại
    chapters = story_data.get('chapters', [])
    current_idx = -1
    chapter_info = {"id": chapter_id, "name": chapter_id}
    
    for idx, chap in enumerate(chapters):
        if chap.get('id') == chapter_id:
            current_idx = idx
            chapter_info = chap
            break
    
    # Tính chapter trước/sau
    prev_chapter = chapters[current_idx + 1] if current_idx + 1 < len(chapters) else None
    next_chapter = chapters[current_idx - 1] if current_idx > 0 else None
    
    # Lấy URLs ảnh từ MongoDB (ImageKit URLs)
    images = crawler.get_chapter_images(manga_id, chapter_id)
    
    # Nếu chưa có, tải và upload lên ImageKit
    if not images:
        try:
            images = crawler.download_chapter_images(manga_id, chapter_id)
        except Exception as e:
            print(f"Lỗi tải ảnh: {e}")
            images = []
    
    # Tất cả images giờ đều là cloud URLs
    is_cloud_urls = True
    
    return render_template('reader.html', 
                         manga_id=manga_id,
                         chapter=chapter_info,
                         images=images,
                         is_cloud_urls=is_cloud_urls,
                         story=story_data,
                         prev_chapter=prev_chapter,
                         next_chapter=next_chapter)


# ==================== API Endpoints ====================

@app.route('/api/crawl/home', methods=['POST'])
def api_crawl_home():
    """API: Crawl lại trang chủ -> MongoDB + ImageKit"""
    try:
        mangas = crawler.crawl_home()
        return jsonify({"success": True, "count": len(mangas)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/crawl/story/<manga_id>', methods=['POST'])
def api_crawl_story(manga_id):
    """API: Crawl chi tiết truyện -> MongoDB"""
    try:
        data = crawler.crawl_story_detail(manga_id)
        return jsonify({"success": True, "chapters": len(data.get('chapters', []))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/crawl/chapter/<manga_id>/<chapter_id>', methods=['POST'])
def api_crawl_chapter(manga_id, chapter_id):
    """API: Tải và upload chapter -> ImageKit + MongoDB"""
    try:
        images = crawler.download_chapter_images(manga_id, chapter_id)
        return jsonify({"success": True, "images": len(images)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/download-all/<manga_id>', methods=['POST'])
def api_download_all(manga_id):
    """API: Tải toàn bộ truyện lên cloud"""
    try:
        story_data = crawler.get_story_data(manga_id)
        if not story_data:
            story_data = crawler.crawl_story_detail(manga_id)
        
        chapters = story_data.get('chapters', [])
        total = len(chapters)
        downloaded = 0
        errors = []
        
        for idx, chapter in enumerate(chapters):
            try:
                chapter_id = chapter.get('id')
                if chapter_id:
                    images = crawler.download_chapter_images(manga_id, chapter_id)
                    if images:
                        downloaded += 1
                    print(f"📥 [{downloaded}/{total}] {chapter_id}: {len(images)} ảnh")
            except Exception as e:
                errors.append(f"{chapter.get('id')}: {str(e)}")
        
        return jsonify({
            "success": True, 
            "total": total,
            "downloaded": downloaded,
            "errors": errors[:10]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/download-status/<manga_id>')
def api_download_status(manga_id):
    """API: Kiểm tra trạng thái tải từ MongoDB"""
    return jsonify(crawler.get_download_status(manga_id))


@app.route('/api/manga/list')
def api_manga_list():
    """API: Lấy danh sách manga từ MongoDB"""
    mangas = crawler.get_manga_list()
    return jsonify(mangas)


@app.route('/api/manga/<manga_id>')
def api_manga_detail(manga_id):
    """API: Lấy chi tiết manga từ MongoDB"""
    data = crawler.get_story_data(manga_id)
    if data:
        return jsonify(data)
    return jsonify({"error": "Not found"}), 404


# ==================== Search ====================

@app.route('/search')
def search():
    """Trang tìm kiếm - Từ MongoDB"""
    query = request.args.get('q', '').lower().strip()
    mangas = crawler.get_manga_list()
    
    results = []
    if query:
        for manga in mangas:
            if query in manga.get('title', '').lower():
                results.append(manga)
    
    return render_template('search.html', query=query, results=results)


# ==================== Error Handler ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Trang không tồn tại"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', message="Lỗi server"), 500


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║         🎌 MANGA HEAVEN - CLOUD ONLY MODE 🎌             ║
║   Data: MongoDB Atlas | Images: ImageKit.io (20GB)       ║
║   Truy cập: http://localhost:5000                        ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)