#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Article Publisher
Publishes articles to WeChat Official Account drafts
"""

import os
import sys
import json
import base64
import hashlib
import argparse
import requests
from pathlib import Path
from typing import Optional, List, Tuple

# Set UTF-8 encoding for Windows console
if os.name == 'nt' and __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    TOKEN_ENDPOINT, UPLOAD_MEDIA_ENDPOINT, UPLOAD_DRAFT_ENDPOINT, UPLOAD_PIC_ENDPOINT,
    MEDIA_IMAGE, REQUEST_TIMEOUT, MAX_RETRIES, MAX_IMAGE_SIZE, SUPPORTED_IMAGE_FORMATS,
    FIELD_TITLE, FIELD_AUTHOR, FIELD_DIGEST, FIELD_CONTENT,
    DEFAULT_AUTHOR, MAX_TITLE_LENGTH, MAX_DIGEST_LENGTH,
    CONFIG_FILE, IMAGES_DIR, ensure_directories
)
from wechat_config import WeChatConfig


class WeChatPublisher:
    """Publishes articles to WeChat Official Account"""

    def __init__(self):
        self.config = WeChatConfig()
        self.access_token = None
        self.last_error = None

    def _clear_error(self) -> None:
        self.last_error = None

    def get_last_error(self) -> Optional[dict]:
        return self.last_error

    def _get_public_ip(self) -> Optional[str]:
        providers = [
            ("https://api.ipify.org?format=json", "json", "ip"),
            ("https://ifconfig.me/ip", "text", None),
        ]
        for url, mode, field in providers:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                if mode == "json":
                    data = response.json()
                    value = data.get(field or "", "").strip()
                else:
                    value = response.text.strip()
                if value:
                    return value
            except Exception:
                continue
        return None

    def _record_api_error(self, stage: str, data: dict, extra: Optional[dict] = None) -> dict:
        errcode = data.get("errcode")
        errmsg = str(data.get("errmsg", "Unknown error"))
        lower = errmsg.lower()
        error_type = "api_error"

        if errcode == 40164 or "not in whitelist" in lower or "invalid ip" in lower or "白名单" in errmsg:
            error_type = "whitelist_ip"

        payload = {
            "stage": stage,
            "type": error_type,
            "errcode": errcode,
            "errmsg": errmsg,
        }
        if extra:
            payload.update(extra)

        if error_type == "whitelist_ip":
            public_ip = self._get_public_ip()
            if public_ip:
                payload["public_ip"] = public_ip
            payload["fix_hint"] = (
                "到微信公众号后台 `设置与开发 -> 基本配置 -> IP白名单` 添加当前出口IP，"
                "保存后重新执行上传。"
            )

        self.last_error = payload
        return payload

    def _print_last_error(self) -> None:
        if not self.last_error:
            return
        print(f" Error type: {self.last_error.get('type', 'unknown')}")
        print(f" Error detail: {self.last_error.get('errmsg', 'Unknown error')}")
        if self.last_error.get("public_ip"):
            print(f" Current public IP: {self.last_error['public_ip']}")
        if self.last_error.get("fix_hint"):
            print(f" Fix hint: {self.last_error['fix_hint']}")

    def _parse_json_response(self, response: requests.Response) -> dict:
        try:
            return json.loads(response.content.decode("utf-8"))
        except Exception:
            response.encoding = "utf-8"
            return response.json()

    def _get_access_token(self) -> Optional[str]:
        """Get access token from WeChat API"""
        self._clear_error()
        if not self.config.is_configured():
            print(" WeChat not configured. Run 'python run.py wechat_config.py setup' first")
            return None

        credentials = self.config.get_credentials()

        # Check if we have a cached token (optional enhancement)
        # For now, always fetch a new one

        params = {
            'grant_type': 'client_credential',
            'appid': credentials['appid'],
            'secret': credentials['appsecret']
        }

        try:
            print(" Getting access token...")
            response = requests.get(TOKEN_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT)
            data = self._parse_json_response(response)

            if 'access_token' in data:
                self.access_token = data['access_token']
                print(f" Access token obtained: {self.access_token[:20]}...")
                return self.access_token
            else:
                print(f" Error getting token: {data.get('errmsg', 'Unknown error')}")
                self._record_api_error("get_access_token", data)
                self._print_last_error()
                return None

        except Exception as e:
            print(f" Error: {e}")
            self.last_error = {
                "stage": "get_access_token",
                "type": "request_error",
                "errmsg": str(e),
            }
            return None

    def _upload_thumb_media(self, image_path: str) -> Optional[str]:
        """Upload an image as thumb media and return its media_id"""
        image_file = Path(image_path)

        if not image_file.exists():
            print(f"️  Image not found: {image_path}")
            return None

        # Check file size (thumb media has stricter limits: 128KB for JPG, 500KB for others)
        file_size = image_file.stat().st_size
        max_size = 128 * 1024 if image_file.suffix.lower() in ['.jpg', '.jpeg'] else 500 * 1024
        if file_size > max_size:
            print(f"️  Cover image too large: {file_size / 1024:.2f}KB (max {max_size / 1024:.0f}KB)")
            return None

        if not self.access_token:
            if not self._get_access_token():
                return None

        url = f"{UPLOAD_MEDIA_ENDPOINT}?access_token={self.access_token}&type=thumb"

        try:
            print(f" Uploading cover image: {image_file.name}")
            with open(image_file, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)

            data = self._parse_json_response(response)

            if 'media_id' in data:
                print(f" Cover uploaded: {data['media_id']}")
                return data['media_id']
            else:
                print(f" Upload failed: {data.get('errmsg', 'Unknown error')}")
                self._record_api_error("upload_thumb_media", data, {"image_path": str(image_file)})
                self._print_last_error()
                return None

        except Exception as e:
            print(f" Error uploading cover: {e}")
            self.last_error = {
                "stage": "upload_thumb_media",
                "type": "request_error",
                "errmsg": str(e),
                "image_path": str(image_file),
            }
            return None

    def _upload_image(self, image_path: str) -> Optional[str]:
        """Upload an image and return its URL"""
        image_file = Path(image_path)

        if not image_file.exists():
            print(f"️  Image not found: {image_path}")
            return None

        # Check file size
        file_size = image_file.stat().st_size
        if file_size > MAX_IMAGE_SIZE:
            print(f"️  Image too large: {file_size / 1024 / 1024:.2f}MB (max 2MB)")
            return None

        # Check format
        if image_file.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            print(f"️  Unsupported format: {image_file.suffix}")
            return None

        if not self.access_token:
            if not self._get_access_token():
                return None

        url = f"{UPLOAD_PIC_ENDPOINT}?access_token={self.access_token}"

        try:
            print(f" Uploading image: {image_file.name}")
            with open(image_file, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)

            data = self._parse_json_response(response)

            if 'url' in data:
                print(f" Image uploaded: {data['url']}")
                return data['url']
            else:
                print(f" Upload failed: {data.get('errmsg', 'Unknown error')}")
                self._record_api_error("upload_image", data, {"image_path": str(image_file)})
                self._print_last_error()
                return None

        except Exception as e:
            print(f" Error uploading image: {e}")
            self.last_error = {
                "stage": "upload_image",
                "type": "request_error",
                "errmsg": str(e),
                "image_path": str(image_file),
            }
            return None

    def upload_images(self, image_paths: List[str]) -> List[str]:
        """Upload multiple images and return their URLs"""
        urls = []
        for path in image_paths:
            url = self._upload_image(path.strip())
            if url:
                urls.append(url)
        return urls

    def publish(self, title: str, content: str, author: Optional[str] = None,
                digest: Optional[str] = None, images: Optional[List[str]] = None,
                draft: bool = True) -> bool:
        """Publish an article (as draft by default)"""

        self._clear_error()
        if not self._get_access_token():
            return False

        # Validate title
        if not title or len(title) > MAX_TITLE_LENGTH:
            print(f"️  Title must be 1-{MAX_TITLE_LENGTH} characters")
            return False

        # Set default author
        if not author:
            author = self.config.get_author()

        # CRITICAL: Upload first image as PERMANENT thumb material for cover
        thumb_media_id = None
        if images:
            print("\n Processing cover image...")
            cover_image = images[0]

            # Upload as permanent thumb material (required for draft API)
            thumb_media_id = self._upload_thumb_media(cover_image)

            if thumb_media_id:
                print(f"    Cover will be used as thumb_media_id")
            else:
                print(f"   ️  Cover upload failed, will try without cover")

        # Upload other images and embed in content
        if images and len(images) > 1:
            for img in images[1:]:
                url = self._upload_image(img)
                if url:
                    content = content.replace(img, url)
                    print(f"   Image embedded in content")

        # Build article data - using CORRECT field names (snake_case as per WeChat API)
        article = {
            "title": title,
            "author": author,
            "content": content,
            "need_open_comment": 1,  # Allow comments
            "only_fans_can_comment": 0  # Allow all to comment
        }

        # Add digest if provided
        if digest:
            article["digest"] = digest[:MAX_DIGEST_LENGTH]

        # CRITICAL: Add thumb_media_id and show_cover_pic if we have a cover
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id
            article["show_cover_pic"] = 1  # Show the cover
        else:
            article["show_cover_pic"] = 0  # Don't show cover

        # Upload draft
        url = f"{UPLOAD_DRAFT_ENDPOINT}?access_token={self.access_token}"

        payload = {
            "articles": [article]
        }

        try:
            print(f"\n{' Saving as draft...' if draft else ' Publishing...'}")

            # CRITICAL: Manually encode JSON to avoid double-escaping HTML
            import json
            json_data = json.dumps(payload, ensure_ascii=False)

            # Debug: print what we're sending
            print(f"   Content preview: {content[:100]}...")

            response = requests.post(
                url,
                data=json_data.encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=UTF-8'},
                timeout=REQUEST_TIMEOUT
            )
            data = self._parse_json_response(response)

            # Success is indicated by presence of media_id
            if data.get('media_id'):
                media_id = data.get('media_id', '')
                print(f" Successfully {'saved as draft' if draft else 'published'}!")
                print(f"   Draft Media ID: {media_id}")
                return True
            else:
                print(f" Error: {data.get('errmsg', 'Unknown error')}")
                print(f"   Error code: {data.get('errcode', 'N/A')}")
                self._record_api_error("publish_draft", data, {"title": title})
                self._print_last_error()
                return False

        except Exception as e:
            print(f" Error: {e}")
            import traceback
            traceback.print_exc()
            self.last_error = {
                "stage": "publish_draft",
                "type": "request_error",
                "errmsg": str(e),
                "title": title,
            }
            return False

    def batch_get_drafts(self, offset: int = 0, count: int = 20, no_content: int = 0) -> Optional[dict]:
        if not self.access_token and not self._get_access_token():
            return None

        url = f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={self.access_token}"
        payload = {"offset": offset, "count": count, "no_content": no_content}

        try:
            response = requests.post(
                url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=UTF-8"},
                timeout=REQUEST_TIMEOUT,
            )
            data = self._parse_json_response(response)
            if "item" in data or data.get("total_count", 0) >= 0:
                return data
            self._record_api_error("batch_get_drafts", data)
            self._print_last_error()
            return None
        except Exception as e:
            self.last_error = {
                "stage": "batch_get_drafts",
                "type": "request_error",
                "errmsg": str(e),
            }
            print(f" Error fetching drafts: {e}")
            return None

    def find_draft_by_title(self, title: str, count: int = 20, no_content: int = 0) -> Tuple[Optional[str], Optional[dict]]:
        data = self.batch_get_drafts(offset=0, count=count, no_content=no_content)
        if not data:
            return None, None
        for item in data.get("item", []):
            news = ((item.get("content") or {}).get("news_item") or [{}])[0]
            if news.get("title") == title:
                return item.get("media_id"), news
        return None, None

    def update_draft(self, media_id: str, article: dict, index: int = 0) -> bool:
        self._clear_error()
        if not self.access_token and not self._get_access_token():
            return False

        url = f"https://api.weixin.qq.com/cgi-bin/draft/update?access_token={self.access_token}"
        payload = {"media_id": media_id, "index": index, "articles": article}

        try:
            response = requests.post(
                url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=UTF-8"},
                timeout=REQUEST_TIMEOUT,
            )
            data = self._parse_json_response(response)
            if data.get("errcode", 0) == 0:
                print(f" Draft updated: {media_id}")
                return True
            self._record_api_error("update_draft", data, {"media_id": media_id})
            self._print_last_error()
            return False
        except Exception as e:
            self.last_error = {
                "stage": "update_draft",
                "type": "request_error",
                "errmsg": str(e),
                "media_id": media_id,
            }
            print(f" Error updating draft: {e}")
            return False

    def upload_image_command(self, image_path: str) -> bool:
        """Command to upload a single image"""
        if not self._get_access_token():
            return False

        url = self._upload_image(image_path)
        if url:
            print(f"\n Image URL: {url}")
            print("You can use this URL in your article content")
            return True
        return False


def main():
    parser = argparse.ArgumentParser(description='WeChat Article Publisher')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Publish command
    parser_publish = subparsers.add_parser('publish', help='Publish an article')
    parser_publish.add_argument('--title', required=True, help='Article title')
    parser_publish.add_argument('--content', required=True, help='Article content (HTML)')
    parser_publish.add_argument('--author', help='Author name')
    parser_publish.add_argument('--digest', help='Article summary/digest')
    parser_publish.add_argument('--images', help='Comma-separated image paths')
    parser_publish.add_argument('--draft', action='store_true', default=True,
                                help='Save as draft (default: True)')
    parser_publish.add_argument('--publish', action='store_false', dest='draft',
                                help='Publish immediately (instead of draft)')

    # Upload image command
    parser_upload = subparsers.add_parser('upload-image', help='Upload a single image')
    parser_upload.add_argument('--image', required=True, help='Image file path')

    # Upload images command
    parser_upload_multi = subparsers.add_parser('upload-images', help='Upload multiple images')
    parser_upload_multi.add_argument('--images', required=True, help='Comma-separated image paths')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    publisher = WeChatPublisher()

    if args.command == 'publish':
        images = None
        if args.images:
            images = [img.strip() for img in args.images.split(',')]

        success = publisher.publish(
            title=args.title,
            content=args.content,
            author=args.author,
            digest=args.digest,
            images=images,
            draft=args.draft
        )
        return 0 if success else 1

    elif args.command == 'upload-image':
        success = publisher.upload_image_command(args.image)
        return 0 if success else 1

    elif args.command == 'upload-images':
        if not publisher._get_access_token():
            return 1

        image_list = [img.strip() for img in args.images.split(',')]
        urls = publisher.upload_images(image_list)

        if urls:
            print("\n Uploaded images:")
            for url in urls:
                print(f"   {url}")
            return 0
        return 1


if __name__ == "__main__":
    sys.exit(main())
