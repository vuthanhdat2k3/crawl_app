# Deploy FlareSolverr trên Railway

## Vì sao cần FlareSolverr?

**Vấn đề:** Cloudflare chặn request từ server Railway vì:
- IP datacenter bị blacklist
- Headless browser bị detect
- Không có session/cookie đã verify

**Giải pháp:** FlareSolverr là proxy service chuyên bypass Cloudflare, hoạt động độc lập với app chính.

---

## Cách deploy FlareSolverr trên Railway

### Bước 1: Tạo Service mới

1. Vào Dashboard Railway
2. Click "New Service" trong project hiện tại
3. Chọn "Docker Image"
4. Nhập: `ghcr.io/flaresolverr/flaresolverr:latest`

### Bước 2: Cấu hình Service

**Variables:**
```
LOG_LEVEL=info
LOG_HTML=false
CAPTCHA_SOLVER=none
TZ=Asia/Ho_Chi_Minh
```

**Settings:**
- Port: `8191`
- Health Check Path: `/`

### Bước 3: Cấu hình Private Networking

1. Trong FlareSolverr service → Settings → Networking
2. Enable "Private Networking"
3. Ghi nhớ internal hostname (vd: `flaresolverr.railway.internal`)

### Bước 4: Kết nối với App chính

Thêm biến môi trường vào app chính:

```
FLARESOLVERR_URL=http://flaresolverr.railway.internal:8191
```

Hoặc nếu dùng public domain:
```
FLARESOLVERR_URL=https://your-flaresolverr.up.railway.app
```

---

## Kiểm tra hoạt động

FlareSolverr sẽ log:
```
FlareSolverr v3.x.x
...
Listening on http://0.0.0.0:8191
```

App sẽ log:
```
✅ FlareSolverr connected at http://flaresolverr.railway.internal:8191
```

---

## Giải pháp thay thế (không cần FlareSolverr)

### Option 1: Crawl từ Local
Chạy crawler trên máy local, dữ liệu tự động sync lên MongoDB + ImageKit:
```bash
cd crawler
python manga_crawler.py chapter <manga-id> <chapter-id>
```

### Option 2: Sử dụng Proxy Service
Dùng residential proxy như:
- Bright Data
- Oxylabs
- SmartProxy

Cấu hình qua env:
```
PROXY_URL=http://user:pass@proxy.example.com:8080
```

### Option 3: Chuyển sang nguồn khác
Tìm website manga không dùng Cloudflare protection.

---

## Lưu ý quan trọng

⚠️ **FlareSolverr tốn RAM:** Khoảng 512MB-1GB
⚠️ **Không bypass được mọi trường hợp:** CAPTCHA vẫn có thể xuất hiện
⚠️ **Rate limiting:** Không spam requests quá nhanh
