"""
Database Module - MongoDB Integration
Quản lý dữ liệu manga trên MongoDB Atlas
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
import os
import sys

# Import config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from config import MONGODB_URI, MONGODB_DB_NAME
except ImportError:
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "manga_heaven")


class Database:
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self):
        """Kết nối đến MongoDB"""
        if self._client is None:
            try:
                self._client = MongoClient(MONGODB_URI)
                self._db = self._client[MONGODB_DB_NAME]
                # Test connection
                self._client.admin.command('ping')
                print("✅ Đã kết nối MongoDB thành công!")
            except ConnectionFailure as e:
                print(f"❌ Lỗi kết nối MongoDB: {e}")
                return False
        return True
    
    @property
    def db(self):
        if self._db is None:
            self.connect()
        return self._db
    
    # ==================== MANGA OPERATIONS ====================
    
    def save_manga_list(self, manga_list):
        """Lưu danh sách manga (update or insert)"""
        collection = self.db.mangas
        
        for manga in manga_list:
            collection.update_one(
                {"id": manga["id"]},
                {
                    "$set": {
                        **manga,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        
        print(f"✅ Đã lưu {len(manga_list)} manga vào MongoDB")
        return True
    
    def get_manga_list(self, limit=100, skip=0):
        """Lấy danh sách manga"""
        collection = self.db.mangas
        cursor = collection.find({}).sort("updated_at", -1).skip(skip).limit(limit)
        return list(cursor)
    
    def get_manga_by_id(self, manga_id):
        """Lấy thông tin manga theo ID"""
        collection = self.db.mangas
        return collection.find_one({"id": manga_id})
    
    def save_manga_detail(self, manga_data):
        """Lưu chi tiết manga (bao gồm chapters)"""
        collection = self.db.manga_details
        
        result = collection.update_one(
            {"id": manga_data["id"]},
            {
                "$set": {
                    **manga_data,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        print(f"✅ Đã lưu chi tiết manga: {manga_data.get('title', manga_data['id'])}")
        return result
    
    def get_manga_detail(self, manga_id):
        """Lấy chi tiết manga"""
        collection = self.db.manga_details
        return collection.find_one({"id": manga_id})
    
    # ==================== CHAPTER OPERATIONS ====================
    
    def save_chapter_images(self, manga_id, chapter_id, images):
        """Lưu danh sách URL ảnh của chapter"""
        collection = self.db.chapter_images
        
        result = collection.update_one(
            {"manga_id": manga_id, "chapter_id": chapter_id},
            {
                "$set": {
                    "manga_id": manga_id,
                    "chapter_id": chapter_id,
                    "images": images,  # List of ImageKit URLs
                    "image_count": len(images),
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return result
    
    def get_chapter_images(self, manga_id, chapter_id):
        """Lấy danh sách URL ảnh của chapter"""
        collection = self.db.chapter_images
        doc = collection.find_one({"manga_id": manga_id, "chapter_id": chapter_id})
        return doc.get("images", []) if doc else []
    
    def get_downloaded_chapters(self, manga_id):
        """Lấy danh sách các chapter_id đã tải của một manga"""
        collection = self.db.chapter_images
        cursor = collection.find({"manga_id": manga_id}, {"chapter_id": 1, "_id": 0})
        return [doc["chapter_id"] for doc in cursor]
    
    def get_download_status(self, manga_id):
        """Lấy trạng thái tải của một manga"""
        collection = self.db.chapter_images
        
        # Đếm số chapter đã tải
        downloaded = collection.count_documents({"manga_id": manga_id})
        
        # Lấy tổng số chapter từ manga_details
        detail = self.get_manga_detail(manga_id)
        total = len(detail.get("chapters", [])) if detail else 0
        
        return {
            "total": total,
            "downloaded": downloaded,
            "percentage": round(downloaded / total * 100, 1) if total > 0 else 0
        }
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username, email, password_hash, role='user'):
        """Tạo user mới"""
        collection = self.db.users
        
        # Kiểm tra username/email đã tồn tại
        if collection.find_one({"$or": [{"username": username}, {"email": email}]}):
            return None, "Username hoặc email đã tồn tại"
        
        user = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "role": role,  # 'admin' hoặc 'user'
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = collection.insert_one(user)
        user["_id"] = result.inserted_id
        return user, None
    
    def get_user_by_username(self, username):
        """Lấy user theo username"""
        collection = self.db.users
        return collection.find_one({"username": username})
    
    def get_user_by_email(self, email):
        """Lấy user theo email"""
        collection = self.db.users
        return collection.find_one({"email": email})
    
    def get_user_by_id(self, user_id):
        """Lấy user theo ID"""
        collection = self.db.users
        return collection.find_one({"_id": ObjectId(user_id)})
    
    def get_all_users(self):
        """Lấy tất cả users"""
        collection = self.db.users
        return list(collection.find({}).sort("created_at", -1))
    
    def update_user(self, user_id, data):
        """Cập nhật thông tin user"""
        collection = self.db.users
        data["updated_at"] = datetime.utcnow()
        return collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )
    
    def delete_user(self, user_id):
        """Xóa user"""
        collection = self.db.users
        return collection.delete_one({"_id": ObjectId(user_id)})
    
    def init_admin(self, username, email, password_hash):
        """Tạo admin mặc định nếu chưa có"""
        collection = self.db.users
        
        # Kiểm tra đã có admin chưa
        if collection.find_one({"role": "admin"}):
            return None
        
        return self.create_user(username, email, password_hash, role='admin')
    
    # ==================== MANGA MANAGEMENT ====================
    
    def delete_manga(self, manga_id):
        """Xóa manga và tất cả dữ liệu liên quan"""
        # Xóa từ mangas
        self.db.mangas.delete_one({"id": manga_id})
        
        # Xóa từ manga_details
        self.db.manga_details.delete_one({"id": manga_id})
        
        # Xóa tất cả chapter images
        result = self.db.chapter_images.delete_many({"manga_id": manga_id})
        
        return result.deleted_count
    
    def get_all_manga_stats(self):
        """Lấy thống kê tất cả manga"""
        mangas = list(self.db.mangas.find({}).sort("updated_at", -1))
        
        stats = []
        for manga in mangas:
            manga_id = manga.get("id")
            detail = self.get_manga_detail(manga_id)
            downloaded = self.db.chapter_images.count_documents({"manga_id": manga_id})
            total = len(detail.get("chapters", [])) if detail else 0
            
            stats.append({
                **manga,
                "total_chapters": total,
                "downloaded_chapters": downloaded,
                "download_percentage": round(downloaded / total * 100, 1) if total > 0 else 0
            })
        
        return stats
    
    # ==================== SEARCH ====================
    
    def search_manga(self, query, limit=50):
        """Tìm kiếm manga theo tên"""
        collection = self.db.mangas
        
        # Tạo text index nếu chưa có
        collection.create_index([("title", "text")])
        
        # Tìm kiếm
        cursor = collection.find(
            {"$text": {"$search": query}}
        ).limit(limit)
        
        return list(cursor)
    
    def search_manga_regex(self, query, limit=50):
        """Tìm kiếm manga bằng regex (fallback)"""
        collection = self.db.mangas
        
        cursor = collection.find({
            "title": {"$regex": query, "$options": "i"}
        }).limit(limit)
        
        return list(cursor)


# Singleton instance
db = Database()


# Test connection
if __name__ == "__main__":
    if db.connect():
        print("📊 Database collections:")
        for name in db.db.list_collection_names():
            count = db.db[name].count_documents({})
            print(f"  - {name}: {count} documents")
    else:
        print("❌ Không thể kết nối MongoDB!")
        print("📝 Hãy cập nhật MONGODB_URI trong config.py")
