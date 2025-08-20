#!/usr/bin/env python3
"""
Railway single service - runs both bot and web server
"""
import os
import threading
import time
from telegram_sniper import app, TelegramSniper

def run_flask():
    """Run Flask web server"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_bot():
    """Run Telegram bot"""
    time.sleep(3)  # Wait for Flask to start
    try:
        bot = TelegramSniper()
        # Get Railway domain from environment or use default
        railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'rr-production.up.railway.app')
        bot.public_url = railway_url
        print("Bot started - بوت صيد أسماء المستخدمين بدأ!")
        print(f"Admin ID: {bot.config.get('admin_id', 'Not set')}")
        print(f"Web URL: https://{railway_url}")
        bot.run_bot()
    except Exception as e:
        print(f"Bot error: {e}")

if __name__ == "__main__":
    print("Starting Railway service - Bot + Web Server")
    
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot in main thread
    run_bot()
