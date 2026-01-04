"""
FlareSolverr Client - Bypass Cloudflare protection
https://github.com/FlareSolverr/FlareSolverr
"""

import os
import requests
from bs4 import BeautifulSoup

class FlareSolverrClient:
    def __init__(self):
        # FlareSolverr URL - có thể từ env variable hoặc default
        self.base_url = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")
        self.timeout = 60000  # 60 seconds
        self.available = False
        
    def check_connection(self):
        """Kiểm tra FlareSolverr có sẵn không"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.available = True
                print(f"✅ FlareSolverr connected at {self.base_url}")
                return True
        except:
            pass
        
        self.available = False
        print(f"⚠️ FlareSolverr not available at {self.base_url}")
        return False
    
    def get_page(self, url, max_timeout=60000):
        """Lấy HTML của trang qua FlareSolverr"""
        if not self.available:
            return None
            
        try:
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": max_timeout
            }
            
            response = requests.post(
                f"{self.base_url}/v1",
                json=payload,
                timeout=max_timeout/1000 + 10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    solution = data.get("solution", {})
                    return {
                        "html": solution.get("response", ""),
                        "cookies": solution.get("cookies", []),
                        "user_agent": solution.get("userAgent", ""),
                        "status": solution.get("status", 0)
                    }
                else:
                    print(f"⚠️ FlareSolverr error: {data.get('message', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ FlareSolverr request failed: {e}")
        
        return None
    
    def get_session_cookies(self, url):
        """Lấy cookies đã bypass Cloudflare để dùng cho requests"""
        result = self.get_page(url)
        if result:
            return result.get("cookies", []), result.get("user_agent", "")
        return [], ""


# Singleton instance
flaresolverr = FlareSolverrClient()
