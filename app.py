#!/usr/bin/env python3
"""
Flask app entry point for Railway
"""
from telegram_sniper import app

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
