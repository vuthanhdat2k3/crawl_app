# 🚀 Deploy Manga Heaven lên Railway

## Chuẩn bị

### 1. Tạo tài khoản các dịch vụ (Free)
- **Railway**: https://railway.app (signup với GitHub)
- **MongoDB Atlas**: https://mongodb.com/cloud/atlas (M0 free tier)
- **ImageKit.io**: https://imagekit.io (20GB free)

### 2. Lấy credentials
Theo hướng dẫn trong `CLOUD_SETUP.md`

---

## Deploy lên Railway

### Bước 1: Push code lên GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/manga-heaven.git
git push -u origin main
```

### Bước 2: Deploy trên Railway
1. Truy cập https://railway.app
2. Click **"New Project"** > **"Deploy from GitHub repo"**
3. Chọn repository `manga-heaven`
4. Railway sẽ tự động detect Dockerfile

### Bước 3: Cấu hình Environment Variables
Trong Railway Dashboard > Project > Variables, thêm:

```
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=manga_heaven
IMAGEKIT_PUBLIC_KEY=public_xxxxx
IMAGEKIT_PRIVATE_KEY=private_xxxxx
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id
```

### Bước 4: Expose port
- Vào Settings > Networking
- Click **"Generate Domain"** để có URL public

---

## Cập nhật code để đọc từ Environment Variables

Đã cập nhật `config.py` để hỗ trợ biến môi trường:

```python
import os

MONGODB_URI = os.getenv("MONGODB_URI", "your_default_uri")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "manga_heaven")
IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY", "")
IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "")
```

---

## Kiểm tra deployment

1. Truy cập URL Railway cung cấp
2. Trang chủ sẽ trống (chưa có data)
3. Chạy crawler local để đẩy data lên cloud:
   ```bash
   python crawler/manga_crawler.py home
   python crawler/manga_crawler.py story <manga-id>
   ```
4. Refresh trang web để xem data

---

## Lưu ý

### Free Tier Limits:
- **Railway**: $5 credit/tháng (đủ cho hobby project)
- **MongoDB Atlas M0**: 512MB storage
- **ImageKit.io**: 20GB storage, 20GB bandwidth/tháng

### Tips:
- Crawler nên chạy local, chỉ deploy web server lên Railway
- Data được lưu trên MongoDB + ImageKit, không phụ thuộc server
- Có thể scale horizontal nếu cần

---

## Troubleshooting

### Error "Connection refused":
- Kiểm tra MONGODB_URI có đúng không
- Đảm bảo đã whitelist IP 0.0.0.0/0 trong MongoDB Atlas

### Error "ImageKit upload failed":
- Kiểm tra IMAGEKIT_PRIVATE_KEY
- Đảm bảo không có ký tự đặc biệt bị escape

### Build failed:
- Kiểm tra Dockerfile syntax
- Xem logs trong Railway Dashboard
