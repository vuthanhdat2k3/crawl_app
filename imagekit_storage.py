"""
ImageKit Module - Upload và quản lý ảnh trên ImageKit.io
Free tier: 20GB storage, 20GB bandwidth/month
Sử dụng REST API trực tiếp để đảm bảo tương thích
"""

import requests
import os
import sys
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from config import IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT
except ImportError:
    IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY", "")
    IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
    IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "")


class ImageStorage:
    _instance = None
    
    # ImageKit API endpoints
    UPLOAD_URL = "https://upload.imagekit.io/api/v1/files/upload"
    API_URL = "https://api.imagekit.io/v1"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.private_key = IMAGEKIT_PRIVATE_KEY
        self.public_key = IMAGEKIT_PUBLIC_KEY
        self.url_endpoint = IMAGEKIT_URL_ENDPOINT
        self._connected = False
    
    def connect(self):
        """Kiểm tra kết nối ImageKit"""
        if not self._connected:
            if self.private_key and self.url_endpoint:
                print("✅ Đã kết nối ImageKit thành công!")
                self._connected = True
                return True
            else:
                print("❌ Thiếu credentials ImageKit trong config.py")
                return False
        return True
    
    def _get_auth(self):
        """Tạo auth header cho API calls"""
        return (self.private_key, "")
    
    def upload_from_file(self, file_path, folder, file_name=None):
        """
        Upload file từ đường dẫn local
        
        Args:
            file_path: Đường dẫn file local
            folder: Thư mục trên ImageKit
            file_name: Tên file (nếu không có, dùng tên file gốc)
        
        Returns:
            URL của ảnh đã upload hoặc None nếu lỗi
        """
        if not os.path.exists(file_path):
            print(f"❌ File không tồn tại: {file_path}")
            return None
        
        if file_name is None:
            file_name = os.path.basename(file_path)
        
        try:
            with open(file_path, "rb") as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            data = {
                "file": file_data,
                "fileName": file_name,
                "folder": f"/{folder}",
                "useUniqueFileName": "false",
                "overwriteFile": "true"
            }
            
            response = requests.post(
                self.UPLOAD_URL,
                data=data,
                auth=self._get_auth(),
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('url')
            else:
                print(f"❌ Lỗi upload: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi upload {file_name}: {e}")
            return None
    
    def upload_from_bytes(self, file_bytes, folder, file_name):
        """
        Upload file từ bytes
        
        Args:
            file_bytes: Dữ liệu file dạng bytes
            folder: Thư mục trên ImageKit
            file_name: Tên file
        
        Returns:
            URL của ảnh đã upload hoặc None nếu lỗi
        """
        try:
            file_data = base64.b64encode(file_bytes).decode('utf-8')
            
            data = {
                "file": file_data,
                "fileName": file_name,
                "folder": f"/{folder}",
                "useUniqueFileName": "false",
                "overwriteFile": "true"
            }
            
            response = requests.post(
                self.UPLOAD_URL,
                data=data,
                auth=self._get_auth(),
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('url')
            else:
                print(f"❌ Lỗi upload: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi upload {file_name}: {e}")
            return None
    
    def upload_batch_from_bytes(self, items, folder_path, max_workers=5):
        """
        Upload nhiều ảnh song song
        
        Args:
            items: List of (idx, file_bytes) tuples
            folder_path: Folder trên ImageKit
            max_workers: Số thread song song
        
        Returns:
            List các URL đã upload (theo thứ tự)
        """
        results = [None] * len(items)
        
        def upload_one(item):
            idx, file_bytes = item
            filename = f"{idx:03d}.jpg"
            url = self.upload_from_bytes(file_bytes, folder_path, filename)
            return idx, url
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(upload_one, item): item[0] for item in items}
            for future in as_completed(futures):
                try:
                    idx, url = future.result()
                    results[idx] = url
                    print(f"  ☁️ [{idx+1}/{len(items)}] Uploaded")
                except Exception as e:
                    idx = futures[future]
                    print(f"  ❌ [{idx+1}/{len(items)}] Failed: {e}")
        
        return [url for url in results if url]
    
    def upload_from_url(self, url, folder, file_name):
        """
        Upload file từ URL (ImageKit sẽ fetch và lưu)
        
        Args:
            url: URL của ảnh nguồn
            folder: Thư mục trên ImageKit
            file_name: Tên file
        
        Returns:
            URL của ảnh đã upload hoặc None nếu lỗi
        """
        try:
            data = {
                "file": url,
                "fileName": file_name,
                "folder": f"/{folder}",
                "useUniqueFileName": "false",
                "overwriteFile": "true"
            }
            
            response = requests.post(
                self.UPLOAD_URL,
                data=data,
                auth=self._get_auth()
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('url')
            else:
                print(f"❌ Lỗi upload từ URL: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi upload {file_name}: {e}")
            return None
    
    def upload_chapter_images(self, manga_id, chapter_id, local_folder):
        """
        Upload tất cả ảnh của một chapter
        
        Args:
            manga_id: ID của manga
            chapter_id: ID của chapter
            local_folder: Thư mục local chứa ảnh
        
        Returns:
            List các URL đã upload
        """
        if not os.path.exists(local_folder):
            print(f"❌ Thư mục không tồn tại: {local_folder}")
            return []
        
        image_files = sorted([
            f for f in os.listdir(local_folder) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
        ])
        
        if not image_files:
            print(f"⚠️ Không tìm thấy ảnh trong {local_folder}")
            return []
        
        folder_path = f"manga/{manga_id}/{chapter_id}"
        urls = []
        
        print(f"📤 Đang upload {len(image_files)} ảnh cho {chapter_id}...")
        
        for idx, file_name in enumerate(image_files):
            file_path = os.path.join(local_folder, file_name)
            url = self.upload_from_file(file_path, folder_path, file_name)
            
            if url:
                urls.append(url)
                print(f"  ✅ [{idx+1}/{len(image_files)}] {file_name}")
            else:
                print(f"  ❌ [{idx+1}/{len(image_files)}] {file_name} - FAILED")
        
        print(f"📤 Hoàn thành: {len(urls)}/{len(image_files)} ảnh")
        return urls
    
    def upload_cover(self, manga_id, local_path=None, url=None):
        """
        Upload ảnh bìa manga
        
        Args:
            manga_id: ID của manga
            local_path: Đường dẫn local (ưu tiên)
            url: URL ảnh gốc (nếu không có local)
        
        Returns:
            URL của ảnh bìa trên ImageKit
        """
        folder_path = "manga/covers"
        file_name = f"{manga_id}.jpg"
        
        if local_path and os.path.exists(local_path):
            return self.upload_from_file(local_path, folder_path, file_name)
        elif url:
            return self.upload_from_url(url, folder_path, file_name)
        else:
            print(f"❌ Không có ảnh bìa để upload")
            return None
    
    def get_url(self, path, transformations=None):
        """
        Lấy URL với transformations
        
        Args:
            path: Đường dẫn ảnh trên ImageKit
            transformations: List các transformation (resize, quality, etc.)
        
        Returns:
            URL với transformations
        """
        if transformations:
            tr_str = ",".join([f"{k}-{v}" for t in transformations for k, v in t.items()])
            return f"{self.url_endpoint}/tr:{tr_str}/{path}"
        return f"{self.url_endpoint}/{path}"
    
    def delete_file(self, file_id):
        """Xóa file theo ID"""
        try:
            response = requests.delete(
                f"{self.API_URL}/files/{file_id}",
                auth=self._get_auth()
            )
            return response.status_code == 204
        except Exception as e:
            print(f"❌ Lỗi xóa file: {e}")
            return False
    
    def list_files(self, path="", limit=100):
        """Liệt kê files trong folder"""
        try:
            params = {"limit": limit}
            if path:
                params["path"] = path
            
            response = requests.get(
                f"{self.API_URL}/files",
                params=params,
                auth=self._get_auth()
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"❌ Lỗi liệt kê files: {e}")
            return []


# Singleton instance
image_storage = ImageStorage()


# Test connection
if __name__ == "__main__":
    if image_storage.connect():
        print("\n📂 Kiểm tra ImageKit storage...")
        
        # Test upload
        test_file = "web/static/covers/do-de-cua-ta-deu-la-dai-phan-phai.jpg"
        if os.path.exists(test_file):
            print(f"🔄 Test upload: {test_file}")
            url = image_storage.upload_from_file(test_file, "test", "test-image.jpg")
            if url:
                print(f"✅ Upload thành công: {url}")
            else:
                print("❌ Upload thất bại")
        else:
            print(f"⚠️ Không tìm thấy file test: {test_file}")
        
        # List files
        try:
            files = image_storage.list_files(limit=5)
            if files:
                print(f"\n📁 Có {len(files)} files gần đây:")
                for f in files[:5]:
                    print(f"  - {f.get('name', 'N/A')}: {f.get('url', 'N/A')}")
            else:
                print("\n📁 Chưa có file nào")
        except Exception as e:
            print(f"⚠️ Không thể liệt kê files: {e}")
    else:
        print("❌ Không thể kết nối ImageKit!")
        print("📝 Hãy cập nhật credentials trong config.py")
