#!/usr/bin/env python3
"""
Simple bot runner for PythonAnywhere
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_sniper import TelegramSniper

def main():
    """Run the bot with proper async handling"""
    try:
        bot = TelegramSniper()
        bot.public_url = "sirlin12.pythonanywhere.com"
        print("🚀 Bot starting...")
        print(f"Admin ID: {bot.config.get('admin_id', 'Not set')}")
        
        # Run with proper event loop
        bot.run_bot()
        
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
