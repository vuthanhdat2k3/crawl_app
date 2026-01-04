"""
Script tải ảnh cho 10 chapters đầu tiên
Sử dụng Playwright để vượt bot và tải ảnh
"""

import os
import sys
from manga_crawler import MangaCrawler

def download_10_chapters():
    crawler = MangaCrawler()
    
    # Truyện mẫu: Đồ đệ của ta đều là đại phản phái
    manga_id = "do-de-cua-ta-deu-la-dai-phan-phai"
    
    # 10 chapters để tải (từ mới nhất)
    chapters_to_download = [
        "chuong-461",
        "chuong-460", 
        "chuong-459",
        "chuong-458",
        "chuong-457",
        "chuong-456",
        "chuong-455",
        "chuong-454",
        "chuong-453",
        "chuong-452"
    ]
    
    print("="*50)
    print("📥 BẮT ĐẦU TẢI 10 CHAPTERS")
    print("="*50)
    
    for idx, chapter_id in enumerate(chapters_to_download, 1):
        print(f"\n[{idx}/10] Đang tải: {chapter_id}")
        print("-"*40)
        
        try:
            images = crawler.download_chapter_images(manga_id, chapter_id)
            print(f"✅ Hoàn thành {chapter_id}: {len(images)} ảnh")
        except Exception as e:
            print(f"❌ Lỗi {chapter_id}: {e}")
        
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH TẢI 10 CHAPTERS!")
    print("="*50)

if __name__ == "__main__":
    download_10_chapters()
