"""
CloudScraper Client - Bypass Cloudflare protection without browser
Sử dụng cho Vercel serverless (không cần FlareSolverr hay Playwright)
"""

import cloudscraper
from bs4 import BeautifulSoup


class CloudScraperClient:
    def __init__(self):
        self.scraper = None
        self.available = False
        self._init_scraper()
    
    def _init_scraper(self):
        """Khởi tạo cloudscraper với các options tốt nhất"""
        try:
            self.scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=1  # Giảm delay để tránh timeout trên Vercel
            )
            
            # Thêm headers giả lập browser thật
            self.scraper.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
            
            self.available = True
            print("✅ CloudScraper initialized successfully")
        except Exception as e:
            print(f"❌ CloudScraper init error: {e}")
            self.available = False
    
    def check_connection(self):
        """Kiểm tra cloudscraper có hoạt động không"""
        return self.available
    
    def get_page(self, url, max_timeout=30, retries=2):
        """Lấy HTML của trang qua CloudScraper với retry logic"""
        if not self.available or not self.scraper:
            print("⚠️ CloudScraper not available, trying to reinit...")
            self._init_scraper()
            if not self.available:
                return None
        
        for attempt in range(retries):
            try:
                print(f"🌐 CloudScraper attempt {attempt + 1}/{retries}: {url[:60]}...")
                response = self.scraper.get(url, timeout=max_timeout)
                
                if response.status_code == 200:
                    print(f"✅ CloudScraper success: {len(response.text)} bytes")
                    return {
                        "html": response.text,
                        "cookies": response.cookies.get_dict(),
                        "status": response.status_code
                    }
                else:
                    print(f"⚠️ CloudScraper response: {response.status_code}")
                    
            except cloudscraper.exceptions.CloudflareChallengeError as e:
                print(f"❌ Cloudflare challenge failed (attempt {attempt + 1}): {e}")
                # Reinit scraper để thử lại
                self._init_scraper()
            except Exception as e:
                print(f"❌ CloudScraper request failed (attempt {attempt + 1}): {e}")
        
        return None
    
    def get_image(self, url, referer=None, timeout=30):
        """Tải ảnh về dưới dạng bytes"""
        if not self.available or not self.scraper:
            return None
        
        try:
            headers = {}
            if referer:
                headers['Referer'] = referer
            
            response = self.scraper.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200 and len(response.content) > 1000:
                return response.content
                
        except Exception as e:
            print(f"❌ CloudScraper image download failed: {e}")
        
        return None
    
    def get_session_cookies(self):
        """Lấy cookies đã bypass Cloudflare"""
        if self.scraper:
            return self.scraper.cookies.get_dict()
        return {}


# Singleton instance
cloudscraper_client = CloudScraperClient()
