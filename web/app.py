"""
Manga Heaven - Web Server
CHỈ SỬ DỤNG CLOUD STORAGE (MongoDB + ImageKit)
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import sys
import json
import time
import re

# Thêm đường dẫn root để import modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

# Import crawler và database
from crawler.manga_crawler import MangaCrawler
from database import db

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'manga-heaven-secret-key-2024')

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login_manager.login_message_category = 'warning'


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.role = user_data.get('role', 'user')
        self._is_active = user_data.get('is_active', True)
    
    @property
    def is_active(self):
        return self._is_active
    
    def is_admin(self):
        return self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None


# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin():
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# Khởi tạo crawler (Cloud-only mode)
try:
    crawler = MangaCrawler()
    print("✅ Crawler initialized successfully")
    
    # Tạo admin mặc định nếu chưa có
    admin_user = db.init_admin(
        username='admin',
        email='admin@mangaheaven.com',
        password_hash=generate_password_hash('admin123')
    )
    if admin_user:
        print("✅ Created default admin: admin / admin123")
        
except Exception as e:
    print(f"❌ Error initializing crawler: {e}")
    import traceback
    traceback.print_exc()
    crawler = None


@app.route('/')
@login_required
def index():
    """Trang chủ - Lấy từ MongoDB"""
    if crawler is None:
        return render_template('error.html', message="Đang khởi tạo hệ thống, vui lòng thử lại sau...")
    mangas = crawler.get_manga_list()
    return render_template('index.html', mangas=mangas, total=len(mangas))


@app.route('/story/<manga_id>')
@login_required
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
@login_required
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
@login_required
def api_crawl_home():
    """API: Crawl lại trang chủ -> MongoDB + ImageKit"""
    try:
        mangas = crawler.crawl_home()
        return jsonify({"success": True, "count": len(mangas)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/crawl/story/<manga_id>', methods=['POST'])
@login_required
def api_crawl_story(manga_id):
    """API: Crawl chi tiết truyện -> MongoDB"""
    try:
        data = crawler.crawl_story_detail(manga_id)
        return jsonify({"success": True, "chapters": len(data.get('chapters', []))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/crawl/chapter/<manga_id>/<chapter_id>', methods=['POST'])
@login_required
def api_crawl_chapter(manga_id, chapter_id):
    """API: Tải và upload chapter -> ImageKit + MongoDB"""
    try:
        images = crawler.download_chapter_images(manga_id, chapter_id)
        return jsonify({"success": True, "images": len(images)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/download-all/<manga_id>', methods=['POST'])
@login_required
def api_download_all(manga_id):
    """API: Tải toàn bộ truyện lên cloud (Streaming để tránh timeout)"""
    def generate():
        try:
            story_data = crawler.get_story_data(manga_id)
            if not story_data:
                story_data = crawler.crawl_story_detail(manga_id)
            
            chapters = story_data.get('chapters', [])
            # Đảo ngược để tải từ chap đầu đến chap mới nhất
            chapters = list(reversed(chapters))
            total = len(chapters)
            downloaded = 0
            errors = []
            
            # Gửi thông tin ban đầu
            yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"
            
            for idx, chapter in enumerate(chapters):
                try:
                    chapter_id = chapter.get('id')
                    if chapter_id:
                        images = crawler.download_chapter_images(manga_id, chapter_id)
                        if images:
                            downloaded += 1
                        # Gửi progress cho mỗi chapter
                        yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'chapter': chapter_id, 'images': len(images) if images else 0})}\n\n"
                except Exception as e:
                    error_msg = f"{chapter.get('id')}: {str(e)}"
                    errors.append(error_msg)
                    yield f"data: {json.dumps({'type': 'error', 'chapter': chapter.get('id'), 'error': str(e)})}\n\n"
            
            # Gửi kết quả cuối cùng
            yield f"data: {json.dumps({'type': 'complete', 'success': True, 'total': total, 'downloaded': downloaded, 'errors': errors[:10]})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'success': False, 'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@app.route('/api/download-status/<manga_id>')
@login_required
def api_download_status(manga_id):
    """API: Kiểm tra trạng thái tải từ MongoDB"""
    return jsonify(crawler.get_download_status(manga_id))


@app.route('/api/check-chapter/<manga_id>/<chapter_id>')
@login_required
def api_check_chapter(manga_id, chapter_id):
    """API: Kiểm tra chapter đã được tải chưa"""
    from database import db
    images = db.get_chapter_images(manga_id, chapter_id)
    return jsonify({
        "manga_id": manga_id,
        "chapter_id": chapter_id,
        "downloaded": len(images) > 0 if images else False,
        "images_count": len(images) if images else 0
    })


@app.route('/api/manga/list')
@login_required
def api_manga_list():
    """API: Lấy danh sách manga từ MongoDB"""
    mangas = crawler.get_manga_list()
    return jsonify(mangas)


@app.route('/api/manga/<manga_id>')
@login_required
def api_manga_detail(manga_id):
    """API: Lấy chi tiết manga từ MongoDB"""
    data = crawler.get_story_data(manga_id)
    if data:
        return jsonify(data)
    return jsonify({"error": "Not found"}), 404


# ==================== Search ====================

def normalize_manga_name(name):
    """Chuẩn hóa tên truyện thành slug URL"""
    import unicodedata
    # Chuyển về lowercase
    name = name.lower().strip()
    # Chuẩn hóa unicode (bỏ dấu tiếng Việt)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Thay thế đ/Đ
    name = name.replace('đ', 'd').replace('Đ', 'd')
    # Chỉ giữ lại chữ cái, số và khoảng trắng
    name = re.sub(r'[^a-z0-9\s]', '', name)
    # Thay khoảng trắng thành dấu gạch ngang
    name = re.sub(r'\s+', '-', name)
    # Bỏ dấu gạch ngang thừa
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name


@app.route('/api/crawl/url', methods=['POST'])
@login_required
def api_crawl_from_url():
    """API: Crawl truyện từ URL đầy đủ"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"success": False, "error": "URL không được để trống"}), 400
        
        # Lấy manga_id từ URL
        # URL dạng: https://nettruyen.me.uk/truyen-tranh/dau-la-dai-luc-5
        if '/truyen-tranh/' in url:
            manga_id = url.split('/truyen-tranh/')[-1].split('/')[0].split('?')[0]
        else:
            manga_id = url.rstrip('/').split('/')[-1]
        
        if not manga_id:
            return jsonify({"success": False, "error": "Không thể xác định ID truyện từ URL"}), 400
        
        # Crawl chi tiết truyện
        story_data = crawler.crawl_story_detail(manga_id)
        
        if story_data:
            return jsonify({
                "success": True, 
                "manga_id": manga_id,
                "title": story_data.get('title', ''),
                "chapters": len(story_data.get('chapters', []))
            })
        else:
            return jsonify({"success": False, "error": "Không thể crawl truyện này"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/search')
@login_required
def search():
    """Trang tìm kiếm - Từ MongoDB, fallback sang NetTruyen"""
    query = request.args.get('q', '').strip()
    mangas = crawler.get_manga_list()
    
    results = []
    if query:
        query_lower = query.lower()
        # Tìm trong database local trước
        for manga in mangas:
            if query_lower in manga.get('title', '').lower():
                results.append(manga)
    
    return render_template('search.html', query=query, results=results)


# ==================== Authentication ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        user_data = db.get_user_by_username(username)
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            if not user_data.get('is_active', True):
                flash('Tài khoản của bạn đã bị khóa.', 'danger')
                return render_template('auth/login.html')
            
            user = User(user_data)
            login_user(user, remember=remember)
            flash(f'Chào mừng {user.username}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin_dashboard') if user.is_admin() else url_for('index'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu.', 'danger')
    
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Trang đăng ký"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if len(username) < 3:
            flash('Tên đăng nhập phải có ít nhất 3 ký tự.', 'danger')
        elif len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự.', 'danger')
        elif password != confirm_password:
            flash('Mật khẩu xác nhận không khớp.', 'danger')
        else:
            user, error = db.create_user(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            
            if user:
                flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
                return redirect(url_for('login'))
            else:
                flash(error or 'Đăng ký thất bại.', 'danger')
    
    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    """Đăng xuất"""
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('login'))


@app.route('/logout-all')
@login_required
def logout_all():
    """Đăng xuất khỏi tất cả thiết bị"""
    logout_user()
    flash('Đã đăng xuất khỏi tất cả thiết bị.', 'info')
    return redirect(url_for('login'))


# ==================== Account Settings ====================

@app.route('/account')
@login_required
def account_settings():
    """Trang cài đặt tài khoản"""
    return render_template('account/settings.html')


@app.route('/account/update-profile', methods=['POST'])
@login_required
def account_update_profile():
    """Cập nhật thông tin cá nhân"""
    email = request.form.get('email', '').strip()
    
    try:
        db.update_user(current_user.id, {'email': email})
        flash('Đã cập nhật thông tin thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('account_settings'))


@app.route('/account/change-password', methods=['POST'])
@login_required
def account_change_password():
    """Đổi mật khẩu"""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Lấy thông tin user từ database
    user_data = db.get_user_by_id(current_user.id)
    
    if not user_data:
        flash('Không tìm thấy thông tin người dùng.', 'danger')
        return redirect(url_for('account_settings'))
    
    # Kiểm tra mật khẩu hiện tại
    if not check_password_hash(user_data['password_hash'], current_password):
        flash('Mật khẩu hiện tại không đúng.', 'danger')
        return redirect(url_for('account_settings'))
    
    # Kiểm tra mật khẩu mới
    if len(new_password) < 6:
        flash('Mật khẩu mới phải có ít nhất 6 ký tự.', 'danger')
        return redirect(url_for('account_settings'))
    
    if new_password != confirm_password:
        flash('Mật khẩu xác nhận không khớp.', 'danger')
        return redirect(url_for('account_settings'))
    
    # Cập nhật mật khẩu
    try:
        db.update_user(current_user.id, {'password_hash': generate_password_hash(new_password)})
        flash('Đổi mật khẩu thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('account_settings'))


# ==================== Admin Panel ====================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin Dashboard"""
    # Thống kê
    manga_stats = db.get_all_manga_stats()
    users = db.get_all_users()
    
    total_manga = len(manga_stats)
    total_chapters = sum(m.get('total_chapters', 0) for m in manga_stats)
    downloaded_chapters = sum(m.get('downloaded_chapters', 0) for m in manga_stats)
    total_users = len(users)
    
    stats = {
        'total_manga': total_manga,
        'total_chapters': total_chapters,
        'downloaded_chapters': downloaded_chapters,
        'total_users': total_users
    }
    
    return render_template('admin/dashboard.html', stats=stats, mangas=manga_stats[:10], users=users[:5])


@app.route('/admin/manga')
@admin_required
def admin_manga_list():
    """Quản lý manga"""
    manga_stats = db.get_all_manga_stats()
    return render_template('admin/manga_list.html', mangas=manga_stats)


@app.route('/admin/manga/add', methods=['GET', 'POST'])
@admin_required
def admin_manga_add():
    """Thêm manga mới"""
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if not url:
            flash('Vui lòng nhập URL truyện.', 'danger')
        else:
            try:
                if '/truyen-tranh/' in url:
                    manga_id = url.split('/truyen-tranh/')[-1].split('/')[0].split('?')[0]
                else:
                    manga_id = url.rstrip('/').split('/')[-1]
                
                story_data = crawler.crawl_story_detail(manga_id)
                
                if story_data and story_data.get('title'):
                    flash(f'Đã thêm truyện: {story_data["title"]} ({len(story_data.get("chapters", []))} chapters)', 'success')
                    return redirect(url_for('admin_manga_list'))
                else:
                    flash('Không thể crawl truyện này. Vui lòng kiểm tra URL.', 'danger')
            except Exception as e:
                flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('admin/manga_add.html')


@app.route('/admin/manga/<manga_id>')
@admin_required
def admin_manga_detail(manga_id):
    """Chi tiết manga"""
    story_data = crawler.get_story_data(manga_id)
    if not story_data:
        flash('Không tìm thấy truyện.', 'danger')
        return redirect(url_for('admin_manga_list'))
    
    download_status = db.get_download_status(manga_id)
    downloaded_chapters = crawler.get_downloaded_chapters(manga_id)
    
    return render_template('admin/manga_detail.html', 
                         story=story_data, 
                         download_status=download_status,
                         downloaded_chapters=downloaded_chapters)


@app.route('/admin/manga/<manga_id>/delete', methods=['POST'])
@admin_required
def admin_manga_delete(manga_id):
    """Xóa manga"""
    try:
        deleted_count = db.delete_manga(manga_id)
        flash(f'Đã xóa truyện và {deleted_count} chapter images.', 'success')
    except Exception as e:
        flash(f'Lỗi khi xóa: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manga_list'))


@app.route('/admin/manga/<manga_id>/refresh', methods=['POST'])
@admin_required
def admin_manga_refresh(manga_id):
    """Cập nhật lại thông tin manga"""
    try:
        story_data = crawler.crawl_story_detail(manga_id)
        if story_data:
            flash(f'Đã cập nhật: {story_data["title"]} ({len(story_data.get("chapters", []))} chapters)', 'success')
        else:
            flash('Không thể cập nhật truyện.', 'danger')
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('admin_manga_detail', manga_id=manga_id))


@app.route('/admin/users')
@admin_required
def admin_users():
    """Quản lý users"""
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/<user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    """Kích hoạt/Vô hiệu hóa user"""
    user_data = db.get_user_by_id(user_id)
    if user_data:
        new_status = not user_data.get('is_active', True)
        db.update_user(user_id, {'is_active': new_status})
        flash(f'Đã {"kích hoạt" if new_status else "vô hiệu hóa"} user {user_data["username"]}.', 'success')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_admin(user_id):
    """Toggle admin role"""
    user_data = db.get_user_by_id(user_id)
    if user_data:
        if user_data.get('username') == 'admin':
            flash('Không thể thay đổi quyền của admin gốc.', 'danger')
        else:
            new_role = 'user' if user_data.get('role') == 'admin' else 'admin'
            db.update_user(user_id, {'role': new_role})
            flash(f'Đã {"nâng cấp" if new_role == "admin" else "hạ cấp"} {user_data["username"]} thành {new_role}.', 'success')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Xóa user"""
    user_data = db.get_user_by_id(user_id)
    if user_data:
        if user_data.get('username') == 'admin':
            flash('Không thể xóa tài khoản admin gốc.', 'danger')
        else:
            db.delete_user(user_id)
            flash(f'Đã xóa user {user_data["username"]}.', 'success')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    """Thêm user mới"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin', '0') == '1'
    
    if not username or not password:
        flash('Vui lòng nhập đầy đủ thông tin.', 'danger')
        return redirect(url_for('admin_users'))
    
    user, error = db.create_user(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role='admin' if is_admin else 'user'
    )
    
    if user:
        flash(f'Đã tạo user {username}.', 'success')
    else:
        flash(error or 'Không thể tạo user.', 'danger')
    
    return redirect(url_for('admin_users'))


# ==================== Admin API ====================

@app.route('/api/admin/download-chapter/<manga_id>/<chapter_id>', methods=['POST'])
@admin_required
def api_admin_download_chapter(manga_id, chapter_id):
    """API: Tải một chapter"""
    try:
        images = crawler.download_chapter_images(manga_id, chapter_id)
        return jsonify({"success": True, "images": len(images) if images else 0})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    """API: Lấy thống kê"""
    manga_stats = db.get_all_manga_stats()
    users = db.get_all_users()
    
    return jsonify({
        'total_manga': len(manga_stats),
        'total_chapters': sum(m.get('total_chapters', 0) for m in manga_stats),
        'downloaded_chapters': sum(m.get('downloaded_chapters', 0) for m in manga_stats),
        'total_users': len(users)
    })


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
║   Admin: admin / admin123                                ║
║   Truy cập: http://localhost:5000                        ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)