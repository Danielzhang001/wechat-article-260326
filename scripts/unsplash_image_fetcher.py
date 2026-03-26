#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unsplash Image Fetcher for WeChat Articles
Fetches high-quality copyright-free images based on keywords
"""
import requests
import json
from pathlib import Path
from typing import Optional, List
import time


class UnsplashImageFetcher:
    """Fetch images from Unsplash for WeChat articles"""

    # Unsplash API endpoints
    SEARCH_URL = "https://api.unsplash.com/search/photos"
    PHOTO_URL = "https://api.unsplash.com/photos"

    def __init__(self, access_key: str = None):
        """
        Initialize fetcher

        Note: You need to get a free API key from https://unsplash.com/developers
        """
        self.access_key = access_key or self._load_access_key()
        self.session = requests.Session()

    def _load_access_key(self) -> Optional[str]:
        """Load Unsplash access key from config file"""
        config_file = Path(__file__).parent.parent / "data" / "unsplash_config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('access_key')

        return None

    def search_photo(self, query: str, orientation: str = "landscape",
                    per_page: int = 5) -> List[dict]:
        """
        Search for photos on Unsplash

        Args:
            query: Search keywords
            orientation: landscape, portrait, or squarish
            per_page: Number of results

        Returns:
            List of photo info dicts
        """
        if not self.access_key:
            print("⚠️  No Unsplash access key found")
            print("   Get free key at: https://unsplash.com/developers")
            return []

        params = {
            'query': query,
            'orientation': orientation,
            'per_page': per_page,
            'order_by': 'relevant'
        }

        headers = {
            'Authorization': f'Client-ID {self.access_key}'
        }

        try:
            response = requests.get(
                self.SEARCH_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            return results

        except Exception as e:
            print(f"❌ Error searching Unsplash: {e}")
            return []

    def get_photo_download_url(self, photo_id: str, size: str = "regular") -> Optional[str]:
        """
        Get the direct download URL for a photo

        Args:
            photo_id: Unsplash photo ID
            size: raw, full, regular, small, thumb

        Returns:
            Download URL or None
        """
        if not self.access_key:
            return None

        url = f"{self.PHOTO_URL}/{photo_id}"
        headers = {
            'Authorization': f'Client-ID {self.access_key}'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            urls = data.get('urls', {})
            download_url = urls.get(size)

            return download_url

        except Exception as e:
            print(f"❌ Error getting photo URL: {e}")
            return None

    def download_photo(self, photo_id: str, output_path: Path,
                      size: str = "regular") -> bool:
        """
        Download a photo to local file

        Args:
            photo_id: Unsplash photo ID
            output_path: Where to save the file
            size: Image size

        Returns:
            True if successful
        """
        if not self.access_key:
            return False

        url = f"{self.PHOTO_URL}/{photo_id}"
        headers = {
            'Authorization': f'Client-ID {self.access_key}'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            download_url = data['urls'][size]
            author = data['user']['name']
            photo_page = data['links']['html']

            # Download the image
            img_response = requests.get(download_url, timeout=30)
            img_response.raise_for_status()

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(img_response.content)

            print(f"Downloaded: {output_path.name}")
            print(f"   Photo by: {author}")
            print(f"   Source: {photo_page}")

            return True

        except Exception as e:
            print(f"Error downloading photo: {e}")
            return False

    def get_suggested_images(self, keywords: List[str],
                            count: int = 3) -> List[dict]:
        """
        Get suggested images based on keywords

        Args:
            keywords: List of search keywords
            count: Number of images per keyword

        Returns:
            List of (photo_id, description) tuples
        """
        suggestions = []

        for keyword in keywords[:count]:
            results = self.search_photo(keyword, per_page=1)

            if results:
                photo = results[0]
                photo_id = photo['id']
                description = photo.get('description') or photo.get('alt_description', keyword)

                suggestions.append({
                    'photo_id': photo_id,
                    'description': description,
                    'keyword': keyword
                })

            # Rate limiting - be nice to the API
            time.sleep(0.5)

        return suggestions


# Predefined keyword mappings for skincare article
SKINCARE_KEYWORDS = {
    "laser": ["laser treatment", "skincare", "dermatology"],
    "sun": ["sun protection", "sunscreen", "sunny day"],
    "moisturizer": ["skincare", "moisturizer", "beauty"],
    "healing": ["healing", "recovery", "wellness"],
    "routine": ["skincare routine", "beauty", "self care"]
}


def setup_unsplash_config():
    """Help user set up Unsplash API key"""
    print("="*70)
    print("设置 Unsplash API Key")
    print("="*70)
    print()
    print("1. 访问: https://unsplash.com/developers")
    print("2. 注册账号（免费）")
    print("3. 创建 New Application")
    print("4. 复制 Access Key")
    print()

    access_key = input("请输入你的 Access Key: ").strip()

    if not access_key:
        print("❌ 未输入 Access Key")
        return False

    # Save to config
    config_dir = Path(__file__).parent.parent / "data"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "unsplash_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({'access_key': access_key}, f, indent=2)

    print()
    print(f"✅ Access Key 已保存到: {config_file}")
    print()

    return True


if __name__ == "__main__":
    # Test the fetcher
    print("Unsplash Image Fetcher 测试")
    print()

    fetcher = UnsplashImageFetcher()

    if not fetcher.access_key:
        print("未配置 Unsplash API Key")
        print("运行此脚本并按照提示设置:")
        print("  python unsplash_image_fetcher.py")
        print()

        if setup_unsplash_config():
            fetcher = UnsplashImageFetcher()

    if fetcher.access_key:
        # Test search
        print("搜索测试 - 'skincare':")
        print("-"*70)

        results = fetcher.search_photo("skincare", per_page=3)

        for i, photo in enumerate(results[:3], 1):
            print(f"\n{i}. {photo.get('description', 'No description')}")
            print(f"   ID: {photo['id']}")
            print(f"   By: {photo['user']['name']}")
