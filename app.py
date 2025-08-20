#!/usr/bin/env python3
"""
Flask app entry point for Railway
"""
import os
from telegram_sniper import app

if __name__ == "__main__":
    # Use PORT provided by Railway or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 as required by Railway
    app.run(host='0.0.0.0', port=port, debug=False)
