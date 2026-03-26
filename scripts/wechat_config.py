#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Configuration Manager
Manages WeChat Official Account credentials and settings
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Set UTF-8 encoding for Windows console
if os.name == 'nt' and __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG_FILE, DATA_DIR, ensure_directories


class WeChatConfig:
    """Manages WeChat configuration"""

    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
                return {}
        return {}

    def _save_config(self):
        """Save configuration to file"""
        try:
            ensure_directories()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

    def setup(self):
        """Interactive setup for WeChat configuration"""
        print("🔧 WeChat Official Account Configuration")
        print("=" * 50)
        print("\nTo publish articles to WeChat, you need:")
        print("  1. AppID - from WeChat MP Platform")
        print("  2. AppSecret - from WeChat MP Platform")
        print("\nGet them here: https://mp.weixin.qq.com/")
        print("Path: Development -> Basic Configuration")
        print()

        # Check if config already exists
        if self.config.get('appid'):
            print("⚠️  Existing configuration found:")
            print(f"   AppID: {self.config.get('appid')}")
            print(f"   Author: {self.config.get('author', 'Not set')}")
            overwrite = input("\nOverwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("Cancelled.")
                return False

        print("\nEnter your WeChat MP credentials:")
        print("(Press Enter to leave blank and skip)")
        print()

        # AppID
        appid = input("AppID: ").strip()
        if not appid:
            print("⚠️  AppID is required for publishing articles")
            return False

        # AppSecret
        appsecret = input("AppSecret: ").strip()
        if not appsecret:
            print("⚠️  AppSecret is required for publishing articles")
            return False

        # Optional settings
        print("\nOptional settings:")
        print("(Press Enter to use default values)")
        print()

        author = input(f"Default author name [{self.config.get('author', 'Author')}]: ").strip()
        if not author:
            author = self.config.get('author', 'Author')

        images_dir = input(f"Local images directory [{IMAGES_DIR}]: ").strip()
        if not images_dir:
            images_dir = str(IMAGES_DIR)

        # Save configuration
        self.config = {
            'appid': appid,
            'appsecret': appsecret,
            'author': author,
            'images_dir': images_dir
        }

        if self._save_config():
            print("\n✅ Configuration saved successfully!")
            print(f"   Location: {self.config_file}")
            return True
        else:
            print("\n❌ Failed to save configuration")
            return False

    def status(self):
        """Show current configuration status"""
        print("📋 WeChat Configuration Status")
        print("=" * 50)
        print()

        if not self.config:
            print("⚠️  No configuration found")
            print("\nRun 'python run.py wechat_config.py setup' to configure")
            return

        # Show masked configuration
        appid = self.config.get('appid', '')
        if appid:
            # Show first 8 and last 4 characters
            masked_appid = appid[:8] + '****' + appid[-4:] if len(appid) > 12 else '****'
            print(f"AppID:     {masked_appid}")
            print(f"Status:    ✅ Configured")
        else:
            print("AppID:     ❌ Not configured")

        appsecret = self.config.get('appsecret', '')
        if appsecret:
            print("AppSecret: **** (hidden)")
        else:
            print("AppSecret: ❌ Not configured")

        author = self.config.get('author', '')
        print(f"Author:    {author or 'Not set'}")

        images_dir = self.config.get('images_dir', str(IMAGES_DIR))
        print(f"Images:    {images_dir}")

        print()
        print(f"Config file: {self.config_file}")

    def update(self, field=None, value=None):
        """Update specific configuration fields"""
        if not self.config:
            print("⚠️  No configuration found. Run 'setup' first.")
            return False

        if field and value:
            # Update specific field
            valid_fields = ['appid', 'appsecret', 'author', 'images_dir']
            if field not in valid_fields:
                print(f"❌ Invalid field. Valid fields: {', '.join(valid_fields)}")
                return False

            self.config[field] = value
            if self._save_config():
                print(f"✅ Updated {field}")
                return True
            return False
        else:
            # Interactive update
            print("🔧 Update WeChat Configuration")
            print("=" * 50)
            print("\nCurrent values:")
            print(f"  AppID:     {self.config.get('appid', '')}")
            print(f"  AppSecret: ****")
            print(f"  Author:    {self.config.get('author', '')}")
            print(f"  Images:    {self.config.get('images_dir', '')}")
            print()

            print("Enter new values (press Enter to keep current):")
            print()

            # AppID
            new_appid = input(f"AppID [{self.config.get('appid', '')}]: ").strip()
            if new_appid:
                self.config['appid'] = new_appid

            # AppSecret
            new_secret = input("AppSecret: ").strip()
            if new_secret:
                self.config['appsecret'] = new_secret

            # Author
            new_author = input(f"Author [{self.config.get('author', '')}]: ").strip()
            if new_author:
                self.config['author'] = new_author
            elif 'author' not in self.config:
                self.config['author'] = 'Author'

            # Images directory
            current_images = self.config.get('images_dir', str(IMAGES_DIR))
            new_images = input(f"Images dir [{current_images}]: ").strip()
            if new_images:
                self.config['images_dir'] = new_images

            if self._save_config():
                print("\n✅ Configuration updated!")
                return True
            return False

    def clear(self):
        """Clear all configuration"""
        if not self.config_file.exists():
            print("⚠️  No configuration to clear")
            return

        print("⚠️  This will delete your WeChat credentials")
        confirm = input("Are you sure? (yes/NO): ").strip().lower()
        if confirm == 'yes':
            try:
                self.config_file.unlink()
                self.config = {}
                print("✅ Configuration cleared")
            except Exception as e:
                print(f"❌ Error clearing config: {e}")
        else:
            print("Cancelled")

    def get_credentials(self):
        """Get credentials for API calls"""
        return {
            'appid': self.config.get('appid', ''),
            'appsecret': self.config.get('appsecret', '')
        }

    def get_author(self):
        """Get default author"""
        return self.config.get('author', 'Author')

    def is_configured(self):
        """Check if WeChat is properly configured"""
        return bool(self.config.get('appid') and self.config.get('appsecret'))


def main():
    parser = argparse.ArgumentParser(description='WeChat Configuration Manager')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup command
    parser_setup = subparsers.add_parser('setup', help='Initial configuration setup')
    parser_setup.set_defaults(func='setup')

    # Status command
    parser_status = subparsers.add_parser('status', help='Show configuration status')
    parser_status.set_defaults(func='status')

    # Update command
    parser_update = subparsers.add_parser('update', help='Update configuration')
    parser_update.add_argument('--field', help='Field to update')
    parser_update.add_argument('--value', help='New value')
    parser_update.set_defaults(func='update')

    # Clear command
    parser_clear = subparsers.add_parser('clear', help='Clear all configuration')
    parser_clear.set_defaults(func='clear')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    config = WeChatConfig()

    if args.command == 'setup':
        success = config.setup()
        return 0 if success else 1
    elif args.command == 'status':
        config.status()
        return 0
    elif args.command == 'update':
        success = config.update(args.field, args.value)
        return 0 if success else 1
    elif args.command == 'clear':
        config.clear()
        return 0


if __name__ == "__main__":
    sys.exit(main())
