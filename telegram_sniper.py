#!/usr/bin/env python3
# Unified Telegram Username Sniper Bot - Better than PHP version
# Code Developer Mohammed Qasim : @LLLLi : @HHHHR

import os
import json
import time
import asyncio
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telethon import TelegramClient
from telethon import functions
from telethon.errors import PhoneCodeExpiredError, PhoneCodeInvalidError, SessionPasswordNeededError
from telethon.errors.rpcerrorlist import UsernameNotOccupiedError, UsernameInvalidError, FloodWaitError
import logging
import requests
from pyrogram import Client
from pyrogram.errors import FloodWait, UsernameOccupied, UsernameInvalid
from pyrogram.raw.functions.contacts import ResolveUsername

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Fix encoding on Windows
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)

# Flask Web App للمصادقة
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('auth.html')

@app.route('/auth/<user_id>')
def auth_page(user_id):
    return render_template('auth.html', user_id=user_id)

@app.route('/submit_auth', methods=['POST'])
def submit_auth():
    try:
        data = request.json
        user_id = data.get('user_id')
        phone = data.get('phone')
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        code = data.get('code')
        
        if not all([user_id, phone, api_id, api_hash, code]):
            return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'})
        
        # قراءة phone_code_hash من الملف المؤقت
        temp_file = os.path.join("temp_auth", f"{user_id}_temp.json")
        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'انتهت صلاحية الجلسة. أعد طلب الكود'})
            
        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
        except:
            return jsonify({'success': False, 'error': 'خطأ في قراءة بيانات الجلسة'})
        
        # محاولة تسجيل الدخول
        async def verify_code():
            # تأخير عشوائي قبل التحقق
            await asyncio.sleep(__import__('random').uniform(3, 7))
            
            os.makedirs("temp_sessions", exist_ok=True)
            session_path = f"temp_sessions/{user_id}_{phone.replace('+', '')}"
            
            # نفس المعرفات المستخدمة في طلب الكود
            client = TelegramClient(
                session_path,
                int(api_id),
                api_hash,
                device_model="Samsung SM-G973F",
                system_version="Android 11",
                app_version="8.9.2",
                lang_code="ar",
                system_lang_code="ar",
                proxy=None,
                connection_retries=1,
                retry_delay=2
            )
            
            try:
                await client.connect()
                # تأخير قبل تسجيل الدخول لمحاكاة السلوك البشري
                await asyncio.sleep(__import__('random').uniform(2, 4))
                await client.sign_in(
                    phone=phone,
                    code=code,
                    phone_code_hash=temp_data['phone_code_hash']
                )
                
                # إنشاء session دائم
                os.makedirs("sessions", exist_ok=True)
                permanent_session = f"sessions/{user_id}_{phone.replace('+', '')}"
                
                # نسخ الجلسة للمجلد الدائم
                if os.path.exists(f"{session_path}.session"):
                    shutil.copy(f"{session_path}.session", f"{permanent_session}.session")
                
                await client.disconnect()
                return True, "تم تسجيل الدخول بنجاح"
                
            except PhoneCodeExpiredError:
                try:
                    await client.disconnect()
                except:
                    pass
                return False, "انتهت صلاحية الكود"
            except PhoneCodeInvalidError:
                try:
                    await client.disconnect()
                except:
                    pass
                return False, "كود التحقق غير صحيح"
            except SessionPasswordNeededError:
                try:
                    await client.disconnect()
                except:
                    pass
                return False, "يتطلب كلمة مرور إضافية (2FA)"
            except Exception as e:
                try:
                    await client.disconnect()
                except:
                    pass
                error_msg = str(e)
                if "expired" in error_msg.lower():
                    return False, "انتهت صلاحية الكود"
                elif "invalid" in error_msg.lower():
                    return False, "كود التحقق غير صحيح"
                else:
                    return False, f"خطأ في تسجيل الدخول: {error_msg}"
        
        # تشغيل العملية
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, message = loop.run_until_complete(verify_code())
        loop.close()
        
        if success:
            # حفظ البيانات الكاملة
            auth_data = {
                'user_id': user_id,
                'phone': phone,
                'api_id': int(api_id),
                'api_hash': api_hash,
                'code': code,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'session_path': f"sessions/{user_id}_{phone.replace('+', '')}"
            }
            
            final_file = os.path.join("temp_auth", f"{user_id}_auth.json")
            with open(final_file, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, ensure_ascii=False, indent=2)
            
            # حذف الملف المؤقت
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            return jsonify({'success': True, 'message': 'تم إضافة الحساب بنجاح!'})
        else:
            return jsonify({'success': False, 'error': message})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ غير متوقع: {str(e)}'})

@app.route('/request_code', methods=['POST'])
def request_code():
    """طلب كود التحقق"""
    try:
        data = request.json
        user_id = data.get('user_id')
        phone = data.get('phone') 
        api_id = int(data.get('api_id'))
        api_hash = data.get('api_hash')
        
        if not all([user_id, phone, api_id, api_hash]):
            return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'})
        
        # دالة async لطلب الكود
        async def send_code():
            # تأخير عشوائي قبل البدء لتجنب الشك
            await asyncio.sleep(__import__('random').uniform(2, 5))
            
            os.makedirs("temp_sessions", exist_ok=True)
            session_path = f"temp_sessions/{user_id}_{phone.replace('+', '')}"
            
            # استخدام معرفات طبيعية أكثر لتجنب الاكتشاف
            client = TelegramClient(
                session_path,
                api_id,
                api_hash,
                device_model="Samsung SM-G973F",
                system_version="Android 11",
                app_version="8.9.2",
                lang_code="ar",
                system_lang_code="ar",
                proxy=None,
                connection_retries=1,
                retry_delay=2
            )
            
            try:
                await client.connect()
                # تأخير قصير قبل طلب الكود
                await asyncio.sleep(__import__('random').uniform(1, 3))
                result = await client.send_code_request(phone)
                
                # حفظ phone_code_hash مؤقتاً
                os.makedirs("temp_auth", exist_ok=True)
                temp_file = os.path.join("temp_auth", f"{user_id}_temp.json")
                temp_data = {
                    'phone_code_hash': result.phone_code_hash,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(temp_data, f, ensure_ascii=False, indent=2)
                
                await client.disconnect()
                return True, "تم إرسال كود التحقق بنجاح"
                
            except Exception as e:
                try:
                    await client.disconnect()
                except:
                    pass
                return False, f"خطأ في إرسال الكود: {str(e)}"
        
        # تشغيل العملية
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, message = loop.run_until_complete(send_code())
        loop.close()
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ غير متوقع: {str(e)}'})

def start_web_server():
    """تشغيل خادم الويب - للاستضافة المجانية"""
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


class TelegramSniper:
    def __init__(self):
        self.config = self.load_config()
        self.checkers = {}
        self.running_tasks = {}
        self.last_check_times = {}
        self.check_counts = {}
        # Global lists (legacy) kept for admin; per-user lists will be stored under data/<user_id>/
        self.list_names = ['user', 'channel']
        # Runtime maps for multi-user checking
        self.user_tasks: Dict[int, asyncio.Task] = {}
        self.user_status_msgs: Dict[int, int] = {}  # user_id -> message_id
        self.user_clients: Dict[int, Optional[TelegramClient]] = {}  # track active clients per user
        self.pending_auth = {}  # المستخدمين في انتظار التحقق
        self.pending_input = {}
        self.pending_replacement = {}
        self.public_url = None

    def load_config(self) -> Dict:
        """Load all configuration from files"""
        config = {
            'bot_token': self.read_file('token'),
            'admin_id': int(self.read_file('ID', '0')),
            'accounts': self.read_json('info.json'),
            'types': self.read_json('type.json'),
            'choices': self.read_json('choice.json'),
            'channel_name': self.read_file('channelName'),
            'channel_about': self.read_file('channelabout')
        }
        return config
    
    def read_file(self, filename: str, default: str = "") -> str:
        """Read content from file with fallback to environment variable"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return content
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
        
        # Fallback to environment variables for critical files
        env_map = {
            'token': 'BOT_TOKEN',
            'ID': 'ADMIN_ID'
        }
        env_var = env_map.get(filename)
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value
        return default
    
    def write_file(self, filename: str, content: str):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def append_file(self, filename: str, content: str):
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(content)
    
    def read_json(self, filename: str) -> Dict:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def write_json(self, filename: str, data: Dict):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ---------- Per-user storage helpers ----------
    def get_user_dir(self, user_id: int) -> str:
        path = os.path.join('data', str(user_id))
        os.makedirs(path, exist_ok=True)
        return path

    def user_file_path(self, user_id: int, name: str) -> str:
        return os.path.join(self.get_user_dir(user_id), name)

    def get_user_prefs(self, user_id: int) -> Dict:
        """Get user preferences"""
        data_dir = os.path.join(os.getcwd(), 'data', str(user_id))
        prefs_file = os.path.join(data_dir, 'prefs.json')
        
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # الإعدادات الافتراضية
        return {
            'running': False,
            'claim_mode': True,
            'mode': 'users',
            'replace_mode': False,
            'add_mode': False,
            'speed_delay': 5,  # التأخير بين العمليات بالثواني (زيادة للأمان)
            'accounts': []  # قائمة حسابات المستخدم
        }
    
    def set_user_prefs(self, user_id: int, prefs: Dict):
        path = self.user_file_path(user_id, 'prefs.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False)

    def get_user_list(self, user_id: int) -> List[str]:
        path = self.user_file_path(user_id, 'list.txt')
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip()]

    def write_user_list(self, user_id: int, usernames: List[str]):
        path = self.user_file_path(user_id, 'list.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(usernames))
    
    def add_user_list(self, user_id: int, usernames: List[str]):
        """Add usernames to user's list"""
        current_usernames = self.get_user_list(user_id)
        all_usernames = list(set(current_usernames + usernames))
        self.write_user_list(user_id, all_usernames)

    def save_claimed_username(self, user_id: int, username: str):
        """Save claimed username to user's claimed list"""
        path = self.user_file_path(user_id, 'claimed.txt')
        claimed_usernames = self.get_claimed_usernames(user_id)
        if username not in claimed_usernames:
            claimed_usernames.append(username)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(claimed_usernames))
    
    def get_claimed_usernames(self, user_id: int) -> List[str]:
        """Get list of claimed usernames for user"""
        path = self.user_file_path(user_id, 'claimed.txt')
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    
    def get_user_accounts(self, user_id: int) -> List[Dict]:
        """Get user's Telegram accounts"""
        prefs = self.get_user_prefs(user_id)
        return prefs.get('accounts', [])
    
    def add_user_account(self, user_id: int, account: Dict) -> bool:
        """Add account to user"""
        prefs = self.get_user_prefs(user_id)
        if 'accounts' not in prefs:
            prefs['accounts'] = []
        
        # Check if account already exists
        for existing in prefs['accounts']:
            if existing.get('phone') == account.get('phone'):
                return False
        
        prefs['accounts'].append(account)
        self.set_user_prefs(user_id, prefs)
        return True
    
    def get_user_session_path(self, user_id: int, phone: str) -> str:
        """Get session file path for user account"""
        user_dir = self.get_user_dir(user_id)
        # Return BASE session path WITHOUT extension; Telethon appends .session automatically
        return os.path.join(user_dir, f"session_{phone.replace('+', '')}")
    
    def update_user_account(self, user_id: int, phone: str, updates: Dict):
        """Update specific user account"""
        prefs = self.get_user_prefs(user_id)
        accounts = prefs.get('accounts', [])
        for account in accounts:
            if account['phone'] == phone:
                account.update(updates)
                break
        self.set_user_prefs(user_id, prefs)
    
    async def _cancellable_sleep(self, user_id: int, seconds: float):
        """Sleep in short intervals so stop/cancel signals are respected quickly."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.get_running_loop()
        end = loop.time() + max(0.0, seconds)
        while True:
            now = loop.time()
            if now >= end:
                return
            # stop early if user pressed stop
            prefs = self.get_user_prefs(user_id)
            if not prefs.get('running', True):
                return
            try:
                await asyncio.sleep(min(0.25, end - now))
            except asyncio.CancelledError:
                # propagate immediate cancellation
                raise
    def get_user_channels(self, user_id: int) -> List[str]:
        """Get list of channels for user"""
        path = self.user_file_path(user_id, 'channels.txt')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            return []
    
    def write_user_channels(self, user_id: int, channels: List[str]):
        """Write list of channels for user"""
        path = self.user_file_path(user_id, 'channels.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(channels))
    
    def add_user_channels(self, user_id: int, channels: List[str]):
        """Add channels to user's list"""
        current = self.get_user_channels(user_id)
        new_items = [c for c in channels if c not in current]
        if new_items:
            all_items = current + new_items
            self.write_user_channels(user_id, all_items)

    # ---------- Admin notification helper ----------
    def send_notification(self, text: str):
        """Send notification to admin"""
        url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendMessage"
        data = {
            'chat_id': self.config['admin_id'],
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        try:
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_usernames(self, list_name: str) -> List[str]:
        """Return list of usernames stored in file with the same name as the list."""
        content = self.read_file(list_name)
        return [u.strip() for u in content.split('\n') if u.strip()]
    
    def remove_username(self, list_name: str, username: str):
        """Remove username from the corresponding list file once successfully claimed."""
        usernames = self.get_usernames(list_name)
        if username in usernames:
            usernames.remove(username)
            self.write_file(list_name, '\n'.join(usernames))
    
    async def create_checker_client(self, list_name: str) -> Optional[Client]:
        """Create Pyrogram client for specific list"""
        page_map = {
            'user': 'page1',
            'channel': 'page1'
        }
        
        page_key = page_map.get(list_name)
        if not page_key:
            return None
        
        account_info = self.config['accounts'].get(page_key, {})
        phone = account_info.get('phone', '')
        
        if not phone:
            logger.error(f"No phone number for {list_name}")
            return None
        
        client = Client(
            f"session_{list_name}",
            api_id=22820557,
            api_hash="7dbc90a4eff73013f784b093eab378ff",
            phone_number=phone
        )
        
        return client
    
    async def check_username(self, client: TelegramClient, username: str, operation_type: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check if username is available using Telethon"""
        try:
            # If entity resolves, the username exists (occupied)
            await client.get_entity(username)
            return False, "محتل"
        except UsernameNotOccupiedError:
            return True, "متاح"
        except UsernameInvalidError:
            return False, "غير صالح"
        except FloodWaitError as e:
            wait_seconds = getattr(e, 'seconds', 60)
            logger.warning(f"FloodWait for {wait_seconds}s on check_username @{username}")
            # Respect stop signal if provided
            total = min(wait_seconds, 300)
            if user_id is not None and hasattr(self, '_cancellable_sleep'):
                await self._cancellable_sleep(user_id, total)
            else:
                await asyncio.sleep(total)  # fallback
            return False, f"FLOOD_WAIT_{wait_seconds}"
        except asyncio.CancelledError:
            # Propagate cancellation so the scan loop exits immediately
            raise
        except Exception as e:
            return False, f"خطأ: {str(e)[:50]}..."
    
    async def claim_username(self, client: TelegramClient, username: str, operation_type: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Attempt to claim available username using Telethon"""
        try:
            if operation_type == 'a':  # Account username
                await client(functions.account.UpdateUsernameRequest(username=username))
                return True, "USERNAME_SET"
            elif operation_type in ['c', 'ch']:
                # Create a new channel, then assign the username to it
                title = self.config.get('channel_name') or f"Channel {username}"
                about = self.config.get('channel_about') or "Auto-created channel"
                res = await client(functions.channels.CreateChannelRequest(title=title, about=about, megagroup=False))
                channel = res.chats[0] if getattr(res, 'chats', None) else None
                if channel:
                    await client(functions.channels.UpdateUsernameRequest(channel=channel, username=username))
                    return True, "CHANNEL_CREATED"
                return False, "CHANNEL_CREATE_FAILED"
            elif operation_type in ['b', 'bot']:
                return False, "BOT_CREATION_MANUAL"
            else:
                return False, "UNSUPPORTED_OPERATION"
        except FloodWaitError as e:
            wait_seconds = getattr(e, 'seconds', 60)
            logger.warning(f"FloodWait for {wait_seconds}s on claim_username @{username}")
            # Respect stop signal if provided
            total = min(wait_seconds, 300)
            if user_id is not None and hasattr(self, '_cancellable_sleep'):
                await self._cancellable_sleep(user_id, total)
            else:
                await asyncio.sleep(total)  # fallback
            return False, f"CLAIM_ERROR: FLOOD_WAIT_{wait_seconds}"
        except asyncio.CancelledError:
            # Propagate cancellation so the scan loop exits immediately
            raise
        except Exception as e:
            return False, f"CLAIM_ERROR: {str(e)}"
    
    async def process_list(self, list_name: str):
        """Process username checking for a specific list"""
        logger.info(f"Starting checker for list: {list_name}")
        
        client = await self.create_checker_client(list_name)
        if not client:
            logger.error(f"Failed to create client for {list_name}")
            return
        
        try:
            await client.start()
            logger.info(f"Client started for {list_name}")
            
            # Get operation type
            operation_type = self.config['types'].get(list_name, 'c')
            
            while list_name in self.running_tasks:
                usernames = self.get_usernames(list_name)
                
                if not usernames:
                    await asyncio.sleep(30)
                    continue
                
                for username in usernames:
                    if list_name not in self.running_tasks:
                        break
                        
                    try:
                        # Update monitoring info
                        self.last_check_times[list_name] = datetime.now().strftime('%H:%M:%S')
                        if list_name not in self.check_counts:
                            self.check_counts[list_name] = 0
                        self.check_counts[list_name] += 1
                        
                        # Check availability
                        is_available, status = await self.check_username(client, username, operation_type)
                        
                        # Log actual Telegram response
                        logger.info(f"📋 @{username} → {status}")
                        
                        if is_available:
                            # Try to claim first
                            claimed, claim_status = await self.claim_username(client, username, operation_type)
                            if claimed:
                                # Success: notify and remove from list
                                account_info = self.config['accounts'].get('page1', {})
                                account_name = account_info.get('first_name', 'Unknown')
                                
                                message = (f"🎉 *تم الحصول على اسم المستخدم!*\n"
                                          f"├ الاسم: @{username}\n"
                                          f"├ القائمة: {list_name}\n"
                                          f"├ النوع: {operation_type}\n"
                                          f"├ الحساب: {account_name}\n"
                                          f"└ الوقت: {datetime.now().strftime('%H:%M:%S')}")
                                self.send_notification(message)
                                self.remove_username(list_name, username)
                                log_entry = f"{datetime.now()} - SUCCESS: @{username} claimed on {list_name}\n"
                                self.append_file("success.log", log_entry)
                                logger.info(f"SUCCESS: @{username} claimed on {list_name}")
                            else:
                                # Claim failed → treat as occupied, skip notification
                                logger.info(f"FAILED_CLAIM @{username}: {claim_status}")
                            
                        elif is_available and status == "PURCHASE_AVAILABLE":
                            # Purchase notification
                            message = (f"💰 *متاح للشراء*\n"
                                      f"الاسم: @{username}\n"
                                      f"القائمة: {list_name}")
                            self.send_notification(message)
                            
                        elif "FLOOD_WAIT" in status:
                            wait_time = int(status.split('_')[2]) if '_' in status else 60
                            logger.warning(f"Flood wait {wait_time}s for {list_name}")
                            await asyncio.sleep(wait_time)
                        
                        await asyncio.sleep(1.5)                       
                    except Exception as e:
                        logger.error(f"Error processing @{username} on {list_name}: {e}")
                        await asyncio.sleep(5)
                
                await asyncio.sleep(10)  # Cycle delay
                
        except Exception as e:
            error_msg = f"❌ Critical error in {list_name}: {str(e)}"
            self.send_notification(error_msg)
            logger.error(error_msg)
        
        finally:
            await client.stop()
            logger.info(f"Client stopped for {list_name}")

    async def user_settings_command(self, upd, context: ContextTypes.DEFAULT_TYPE):
        """Send settings inline keyboard to the user. Accepts Update or CallbackQuery."""
        # Determine user and messaging context
        if hasattr(upd, 'from_user'):  # CallbackQuery
            user_id = upd.from_user.id
            send_fn = lambda text, rm: upd.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=rm)
        else:  # Message / Update
            user_id = upd.effective_user.id
            send_fn = lambda text, rm: upd.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=rm)

        prefs = self.get_user_prefs(user_id)
        mode = prefs.get('mode', 'users')
        running = prefs.get('running', False)
        keyboard = [
            [InlineKeyboardButton("👤 فحص يوزرات", callback_data="mode_users"),
             InlineKeyboardButton("📺 فحص قنوات", callback_data="mode_channels")],
            [InlineKeyboardButton("➕ إضافة أسماء", callback_data="add_names")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        text = (
            f"⚙️ *الإعدادات الحالية*\n"
            f"وضع الفحص: {'يوزرات' if mode=='users' else 'قنوات'}\n"
            f"الحالة: {'قيد العمل' if running else 'متوقف'}\n\n"
            f"اختر خياراً:"
        )
        try:
            await send_fn(text, InlineKeyboardMarkup(keyboard))
        except Exception as exc:
            if "not modified" in str(exc).lower() and hasattr(upd, 'answer'):
                await upd.answer("الإعدادات لم تتغير", show_alert=False)
            else:
                logger.error(f"Error sending settings: {exc}")

    async def show_user_accounts(self, user_id, update, context):
        """عرض حسابات المستخدم مع إمكانية الإدارة"""
        accounts = self.get_user_accounts(user_id)
        
        if not accounts:
            keyboard = [
                [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ]
            text = (
                "👤 *حساباتي*\n\n"
                "❌ لا توجد حسابات مضافة بعد.\n\n"
                "🔹 أضف حساب تليجرام لبدء الاستخدام\n"
                "🔹 يمكنك إضافة عدة حسابات للتوزيع الذكي"
            )
        else:
            keyboard = []
            text = "👤 *حساباتي*\n\n"
            
            for i, acc in enumerate(accounts):
                status = "🟢" if acc.get('active', True) else "🔴"
                phone = acc.get('phone', 'غير معروف')
                text += f"{status} {phone}\n"
                
                toggle_text = "إلغاء تفعيل" if acc.get('active', True) else "تفعيل"
                keyboard.append([InlineKeyboardButton(f"{toggle_text} {phone}", callback_data=f"toggle_account_{i}")])
            
            keyboard.extend([
                [InlineKeyboardButton("➕ إضافة حساب جديد", callback_data="add_account")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تحديد طريقة الإرسال
        if hasattr(update, 'edit_message_text'):  # CallbackQuery
            try:
                await update.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            except Exception as e:
                if "not modified" not in str(e).lower():
                    logger.error(f"Error editing accounts message: {e}")
        elif hasattr(update, 'message') and update.message:  # Update with message
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            logger.error("Invalid update object passed to show_user_accounts")

    async def handle_auth_flow(self, update, context, user_id, message_text):
        """معالجة عملية إضافة حساب جديد"""
        # تحقق من ملفات temp_auth بدلاً من الذاكرة فقط
        auth_file = os.path.join("temp_auth", f"{user_id}_auth.json")
        if user_id not in self.pending_auth:
            if not os.path.exists(auth_file):
                return
            # قراءة البيانات من الملف إذا لم تكن في الذاكرة
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    self.pending_auth[user_id] = json.load(f)
            except:
                return
                
        auth_data = self.pending_auth[user_id]
        step = auth_data.get('step', '')
        
        if step == 'phone':
            # التحقق من صحة رقم الهاتف
            if not message_text.startswith('+') or len(message_text) < 10:
                await update.message.reply_text(
                    "❌ رقم هاتف غير صحيح!\n\n"
                    "🔹 يجب أن يبدأ بـ + ورمز البلد\n"
                    "🔹 مثال: +966512345678"
                )
                return
            
            auth_data['phone'] = message_text
            auth_data['step'] = 'api_id'
            await update.message.reply_text(
                "📱 *خطوة 2 من 4*\n\n"
                "🔹 الآن أرسل الـ API ID الخاص بك\n"
                "🔹 احصل عليه من my.telegram.org\n"
                "🔹 مثال: 1234567"
            )
            
        elif step == 'api_id':
            # التحقق من صحة API ID
            try:
                api_id = int(message_text)
                auth_data['api_id'] = api_id
                auth_data['step'] = 'api_hash'
                await update.message.reply_text(
                    "🔑 *خطوة 3 من 4*\n\n"
                    "🔹 الآن أرسل الـ API Hash الخاص بك\n"
                    "🔹 مثال: 1a2b3c4d5e6f7g8h9i0j"
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ API ID يجب أن يكون رقماً!\n"
                    "🔹 مثال: 1234567"
                )
                
        elif step == 'api_hash':
            auth_data['api_hash'] = message_text
            
            # Show web authentication URL
            public_url = self.get_public_url()
            web_url = f"https://{public_url}/auth/{user_id}"
            
            await update.message.reply_text(
                "🌐 *أكمل عملية المصادقة عبر الويب:*\n\n"
                f"🔗 **الرابط:** {web_url}\n\n"
                "📋 **الخطوات:**\n"
                "1️⃣ اضغط على الرابط أعلاه\n"
                "2️⃣ أدخل البيانات المطلوبة\n"
                "3️⃣ أدخل كود التحقق\n"
                "4️⃣ اضغط 'تحقق من الحالة' أدناه\n\n"
                "⚠️ **تنبيه:** أكمل العملية خلال 3 دقائق",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 فتح الرابط", url=web_url)],
                    [InlineKeyboardButton("📋 نسخ الرابط", callback_data="copy_url")],
                    [InlineKeyboardButton("🔍 تحقق من الحالة", callback_data="check_web_auth")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_auth")]
                ])
            )
            
            # Change step to web_pending
            auth_data['step'] = 'web_pending'
            auth_data['web_url'] = web_url
            auth_data['timestamp'] = datetime.now().isoformat()
        
        # Save auth data (pending) - keep separate from final auth file
        os.makedirs("temp_auth", exist_ok=True)
        auth_file = os.path.join("temp_auth", f"{user_id}_pending.json")
        with open(auth_file, 'w', encoding='utf-8') as f:
            json.dump(auth_data, f, ensure_ascii=False, indent=2)

    async def handle_username_input(self, update, context, user_id, message_text):
        """معالجة إضافة يوزرات جديدة"""
        text = message_text.strip()
        import re
        usernames = re.findall(r'(?:https?://t\.me/)?@?([a-zA-Z0-9_]{5,32})', text)
        
        if not usernames:
            await update.message.reply_text("❌ لا توجد يوزرات صحيحة في الرسالة")
            return
            
        prefs = self.get_user_prefs(user_id)
        mode = prefs.get('mode', 'users')
        
        if mode == 'channels':
            current_items = self.get_user_channels(user_id)
            self.add_user_channels(user_id, usernames)
            item_type = "قنوات"
        else:
            current_items = self.get_user_list(user_id)
            self.add_user_list(user_id, usernames)
            item_type = "يوزرات"
            
        await update.message.reply_text(
            f"✅ تم إضافة {len(usernames)} {item_type}\n"
            f"📊 الإجمالي الآن: {len(current_items) + len(usernames)}"
        )
        
        # إلغاء وضع الإضافة
        prefs['add_mode'] = False
        self.set_user_prefs(user_id, prefs)
        
        # تم تعطيل البدء التلقائي للفحص بناءً على طلب المستخدم

    async def handle_username_replacement(self, update, context, user_id, message_text):
        """معالجة استبدال اليوزرات"""
        text = message_text.strip()
        import re
        usernames = re.findall(r'(?:https?://t\.me/)?@?([a-zA-Z0-9_]{5,32})', text)
        
        if not usernames:
            await update.message.reply_text("❌ لا توجد يوزرات صحيحة في الرسالة")
            return
            
        prefs = self.get_user_prefs(user_id)
        mode = prefs.get('mode', 'users')
        
        if mode == 'channels':
            self.write_user_channels(user_id, usernames)
            item_type = "قنوات"
        else:
            self.write_user_list(user_id, usernames)
            item_type = "يوزرات"
            
        await update.message.reply_text(
            f"🔄 تم استبدال القائمة بـ {len(usernames)} {item_type}"
        )
        
        # إلغاء وضع الاستبدال
        prefs['replace_mode'] = False
        self.set_user_prefs(user_id, prefs)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # التحقق من وجود حسابات للمستخدم
        user_accounts = self.get_user_accounts(user_id)
        if not user_accounts and user_id != self.config['admin_id']:
            keyboard = [
                [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔐 *مرحباً بك في بوت صيد الأسماء!*\n\n"
                "❌ يجب إضافة حساب تليجرام واحد على الأقل لاستخدام البوت.\n\n"
                "🔹 سنحتاج API ID و API Hash الخاص بك\n"
                "🔹 يمكنك الحصول عليهما من my.telegram.org\n\n"
                "📱 اضغط الزر أدناه لبدء إضافة حسابك:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("🔍 فحص", callback_data="scan_menu")],
            [InlineKeyboardButton("👥 قوائم اليوزرات", callback_data="user_lists"),
             InlineKeyboardButton("🏆 اليوزرات المحجوزة", callback_data="claimed_usernames")],
            [InlineKeyboardButton("👤 حساباتي", callback_data="user_accounts"),
             InlineKeyboardButton("📊 الحالة", callback_data="status")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="user_settings"),
             InlineKeyboardButton("⏹️ إيقاف الكل", callback_data="stop_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 *بوت صيد أسماء المستخدمين*\n"
            f"├ إصدار بايثون\n"
            f"├ دعم متعدد الحسابات\n"
            f"├ معالجة ذكية للأخطاء\n"
            f"└ إشعارات فورية\n\n"
            f"اختر خياراً:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data

        # ---------- User callbacks ----------
        if data in ["mode_users", "mode_channels", "add_names", "add_usernames", "add_channels", "back_settings"]:
            prefs = self.get_user_prefs(user_id)
            if data == "mode_users":
                prefs['mode'] = 'users'
            elif data == "mode_channels":
                prefs['mode'] = 'channels'
            elif data == "add_names":
                sub_kb = [
                    [InlineKeyboardButton("👤 إضافة يوزرات", callback_data="add_usernames"),
                     InlineKeyboardButton("📺 إضافة قنوات", callback_data="add_channels")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_settings")]
                ]
                try:
                    await query.edit_message_text(
                        "📥 *إضافة أو استبدال الأسماء*\n\nاختَر النوع ثم أرسل الأسماء أو ملف txt.\nللاستبدال الكامل أضف `!` في بداية الرسالة:",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(sub_kb)
                    )
                except Exception as exc:
                    if "not modified" in str(exc).lower():
                        pass
                    else:
                        logger.error(f"Error editing add_names submenu: {exc}")
                return
            elif data == "add_usernames":
                # Set mode to users and enable add_mode so next text message is processed
                prefs['mode'] = 'users'
                prefs['add_mode'] = True
                prefs['replace_mode'] = False  # ensure other mode disabled
                self.set_user_prefs(user_id, prefs)
                await query.message.reply_text(
                    "📥 *أرسل الآن اليوزرات.*\nضع كل يوزر في سطر أو أرسل ملف txt.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            elif data == "add_channels":
                # Set mode to channels and enable add_mode so next text message is processed
                prefs['mode'] = 'channels'
                prefs['add_mode'] = True
                prefs['replace_mode'] = False
                self.set_user_prefs(user_id, prefs)
                await query.message.reply_text(
                    "📥 *أرسل الآن روابط القنوات أو معرفاتها.*\nضع كل قناة في سطر أو أرسل ملف txt.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            elif data == "replace_usernames":
                prefs['mode'] = 'users'
                prefs['replace_mode'] = True
                self.set_user_prefs(user_id, prefs)
                await query.message.reply_text("♻️ *استبدال قائمة اليوزرات*\n\nأرسل اليوزرات الجديدة. ستحل محل القائمة الحالية بالكامل.", parse_mode=ParseMode.MARKDOWN)
                return
            elif data == "replace_channels":
                prefs['mode'] = 'channels'
                prefs['replace_mode'] = True
                self.set_user_prefs(user_id, prefs)
                await query.message.reply_text("♻️ *استبدال قائمة القنوات*\n\nأرسل القنوات الجديدة. ستحل محل القائمة الحالية بالكامل.", parse_mode=ParseMode.MARKDOWN)
                return
            elif data == "back_settings":
                # Return to settings menu
                await self.user_settings_command(update.callback_query, context)
                return

        # ---------- Admin-only actions control ----------
        admin_only = {
            "scan_menu",
            "scan_usernames_menu",
            "scan_channels_menu",
            "start_usernames_claim",
            "start_channels_notify"
        }
        if data in admin_only and user_id != self.config['admin_id']:
            await query.answer("هذه الميزة للمشرف فقط", show_alert=True)
            return
        
        if data == "scan_menu":
            keyboard = [
                [InlineKeyboardButton("👤 فحص يوزرات", callback_data="scan_usernames_menu"),
                 InlineKeyboardButton("📺 فحص قنوات", callback_data="scan_channels_menu")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔍 *قائمة الفحص*\n\n"
                "اختر نوع الفحص:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        elif data == "scan_usernames_menu":
            keyboard = [
                [InlineKeyboardButton("🎯 حجز يوزرات", callback_data="start_usernames_claim"),
                 InlineKeyboardButton("🔔 إشعار يوزرات", callback_data="start_usernames_notify")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="scan_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👤 *فحص اليوزرات*\n\n"
                "🎯 **حجز:** محاولة حجز اليوزرات المتاحة\n"
                "🔔 **إشعار:** إرسال إشعارات عند العثور على يوزرات متاحة",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        elif data == "scan_channels_menu":
            keyboard = [
                [InlineKeyboardButton("🎯 حجز قنوات", callback_data="start_channels_claim"),
                 InlineKeyboardButton("🔔 إشعار قنوات", callback_data="start_channels_notify")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="scan_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📺 *فحص القنوات*\n\n"
                "🎯 **حجز:** محاولة حجز القنوات المتاحة\n"
                "🔔 **إشعار:** إرسال إشعارات عند العثور على قنوات متاحة",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        elif data == "start_usernames_claim":
            logger.info(f"button_handler: user_id={user_id} → start_usernames_claim pressed")
            active_users = await self.start_all_checkers(update, context, claim_mode=True, scan_type='users')
            await query.edit_message_text(
                "🎯 *تم تشغيل حجز اليوزرات!*\n"
                f"المستخدمون النشطون: {active_users}\n"
                f"🔍 بدأ فحص وحجز اليوزرات!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        elif data == "start_usernames_notify":
            logger.info(f"button_handler: user_id={user_id} → start_usernames_notify pressed")
            active_users = await self.start_all_checkers(update, context, claim_mode=False, scan_type='users')
            await query.edit_message_text(
                "🔔 *تم تشغيل إشعارات اليوزرات!*\n"
                f"المستخدمون النشطون: {active_users}\n"
                f"🔍 بدأ فحص اليوزرات مع إشعارات فقط!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        elif data == "start_channels_notify":
            logger.info(f"button_handler: user_id={user_id} → start_channels_notify pressed")
            active_users = await self.start_all_checkers(update, context, claim_mode=False, scan_type='channels')
            await query.edit_message_text(
                "🔔 *تم تشغيل إشعارات القنوات!*\n"
                f"المستخدمون النشطون: {active_users}\n"
                f"🔍 بدأ فحص القنوات مع إشعارات فقط!",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "user_lists":
            prefs = self.get_user_prefs(user_id)
            mode = prefs.get('mode', 'users')
            
            if mode == 'channels':
                items = self.get_user_channels(user_id)
                list_type = "القنوات"
                empty_msg = "❌ لا توجد قنوات في قائمتك"
            else:
                items = self.get_user_list(user_id)
                list_type = "اليوزرات"
                empty_msg = "❌ لا توجد يوزرات في قائمتك"
            
            if not items:
                text = f"👥 *قائمة {list_type}*\n\n{empty_msg}"
            else:
                text = f"👥 *قائمة {list_type}* ({len(items)})\n\n"
                for i, item in enumerate(items[:20], 1):  # عرض أول 20 فقط
                    text += f"{i}. @{item}\n"
                if len(items) > 20:
                    text += f"\n... و {len(items) - 20} أخرى"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "claimed_usernames":
            claimed = self.get_claimed_usernames(user_id)
            
            if not claimed:
                text = "🏆 *اليوزرات المحجوزة*\n\n❌ لم تحجز أي يوزرات بعد"
            else:
                text = f"🏆 *اليوزرات المحجوزة* ({len(claimed)})\n\n"
                for i, username in enumerate(claimed[:20], 1):  # عرض أول 20 فقط
                    text += f"{i}. @{username}\n"
                if len(claimed) > 20:
                    text += f"\n... و {len(claimed) - 20} أخرى"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "stop_all":
            logger.info(f"button_handler: user_id={user_id} → stop_all pressed")
            await self.stop_all_checkers()
            await query.edit_message_text(
                "🔴 *تم إيقاف جميع الفاحصات!*",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "check_web_auth":
            # Verify whether the user has completed the web authentication flow
            await self.check_auth_status(query, context, user_id)
            return
        elif data == "status":
            status_text = self.get_status_text(user_id)
            await query.edit_message_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "user_accounts":
            # عرض حسابات المستخدم
            await self.show_user_accounts(user_id, query, context)
            return
        
        elif data == "user_settings":
            # عرض إعدادات المستخدم (السرعة والوضع)
            await self.user_settings_command(query, context)
            return
        
        elif data == "add_account":
            # إضافة حساب جديد عبر Web App
            web_url = f"https://{self.get_public_url()}/auth/{user_id}"
            keyboard = [
                [InlineKeyboardButton("🌐 افتح صفحة إضافة الحساب", url=web_url)],
                [InlineKeyboardButton("🔄 تحقق من الحالة", callback_data="check_web_auth")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="user_settings")]
            ]
            
            await query.edit_message_text(
                "🌐 *إضافة حساب تليجرام*\n\n"
                "✅ **خطوات الإضافة:**\n"
                "🔹 اضغط زر \"افتح صفحة إضافة الحساب\"\n"
                "🔹 أدخل رقمك و API بياناتك\n" 
                "🔹 اطلب كود التحقق\n"
                "🔹 أدخل الكود\n"
                "🔹 ارجع هنا واضغط \"تحقق من الحالة\"\n\n"
                "🔒 **أمان كامل** - لا مراقبة من تليجرام!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        
        elif data.startswith("toggle_account_"):
            account_index = int(data.replace("toggle_account_", ""))
            accounts = self.get_user_accounts(user_id)
            
            if 0 <= account_index < len(accounts):
                accounts[account_index]['active'] = not accounts[account_index].get('active', True)
                
                # حفظ التغييرات
                prefs = self.get_user_prefs(user_id)
                prefs['accounts'] = accounts
                self.set_user_prefs(user_id, prefs)
                
                # إعادة عرض قائمة الحسابات
                await self.show_user_accounts(user_id, query, context)
            return
        
        elif data.startswith("set_speed_"):
            speed_str = data.replace("set_speed_", "")
            speed = float(speed_str)
            prefs = self.get_user_prefs(user_id)
            prefs['speed_delay'] = speed
            self.set_user_prefs(user_id, prefs)
            await query.answer(f"✅ تم تعيين السرعة إلى {speed} ثانية", show_alert=True)
            await self.show_speed_settings(user_id, update, context)
            return
        
        elif data == "back_main":
            keyboard = [
                [InlineKeyboardButton("🔍 فحص", callback_data="scan_menu")],
                [InlineKeyboardButton("👥 قوائم اليوزرات", callback_data="user_lists"),
                 InlineKeyboardButton("🏆 اليوزرات المحجوزة", callback_data="claimed_usernames")],
                [InlineKeyboardButton("👤 حساباتي", callback_data="user_accounts"),
                 InlineKeyboardButton("📊 الحالة", callback_data="status")],
                [InlineKeyboardButton("⚙️ الإعدادات", callback_data="user_settings"),
                 InlineKeyboardButton("⏹️ إيقاف الكل", callback_data="stop_all")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    f"🤖 *بوت صيد أسماء المستخدمين*\n"
                    f"├ إصدار بايثون\n"
                    f"├ دعم متعدد الحسابات\n"
                    f"├ معالجة ذكية للأخطاء\n"
                    f"└ إشعارات فورية\n\n"
                    f"اختر خياراً:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "not modified" in str(e).lower():
                    await query.answer("القائمة الرئيسية", show_alert=False)
                else:
                    logger.error(f"Error editing main message: {e}")
    
    async def get_user_client(self, user_id: int, account: Dict):
        """Create Telegram client for user account"""
        try:
            from telethon import TelegramClient
            session_path = self.get_user_session_path(user_id, account['phone'])
            
            # استخدام معرفات طبيعية للفحص
            client = TelegramClient(
                session_path,
                account['api_id'],
                account['api_hash'],
                device_model="Samsung SM-G973F",
                system_version="Android 11",
                app_version="8.9.2",
                lang_code="ar",
                system_lang_code="ar",
                proxy=None,
                connection_retries=1,
                retry_delay=2
            )
            return client
        except Exception as e:
            logger.error(f"Error creating client for user {user_id}: {e}")
            return None
    
    async def start_all_checkers(self, update, context, claim_mode=True, scan_type='users'):
        """Start checking for all users with active accounts"""
        query = update.callback_query if hasattr(update, 'callback_query') else update
        user_id = query.from_user.id if hasattr(query, 'from_user') else update.effective_user.id
        logger.info(f"start_all_checkers: user_id={user_id}, claim_mode={claim_mode}, scan_type={scan_type}")
        
        # Stop any existing task for this user (gracefully)
        if user_id in self.user_tasks:
            # Signal running flag off first to let loop exit quickly
            try:
                prefs_tmp = self.get_user_prefs(user_id)
                prefs_tmp['running'] = False
                self.set_user_prefs(user_id, prefs_tmp)
            except Exception:
                pass
            # Disconnect active client (break any pending network ops)
            client = self.user_clients.get(user_id)
            if client:
                try:
                    await asyncio.wait_for(client.disconnect(), timeout=3)
                except Exception:
                    pass
            # Cancel and await a short time for clean exit
            task = self.user_tasks.get(user_id)
            if task:
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            logger.info(f"start_all_checkers: previous task for user_id={user_id} cancelled and cleaned up")
            
        # Check if user has active accounts
        user_accounts = self.get_user_accounts(user_id)
        active_accounts = [acc for acc in user_accounts if acc.get('active', True)]
        
        if not active_accounts:
            logger.warning(f"start_all_checkers: user_id={user_id} has no active accounts")
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(
                    "❌ *لا توجد حسابات نشطة!*\n\n"
                    "🔹 أضف حساب تليجرام واحد على الأقل\n"
                    "🔹 تأكد من تفعيل الحساب في قائمة \"حساباتي\"",
                    parse_mode=ParseMode.MARKDOWN
                )
            return 0
            
        # Set user preferences
        prefs = self.get_user_prefs(user_id)
        prefs['running'] = True
        prefs['claim_mode'] = claim_mode
        prefs['mode'] = scan_type
        self.set_user_prefs(user_id, prefs)
        logger.info(f"start_all_checkers: prefs set and starting scan for user_id={user_id}")
        
        # Start scanning task (delegates task creation to start_user_scan)
        await self.start_user_scan(user_id, context)
        logger.info(f"start_all_checkers: scan task scheduled for user_id={user_id}")
        return 1  # Return number of active users
    
    async def show_speed_settings(self, user_id, update, context):
        """عرض إعدادات السرعة"""
        prefs = self.get_user_prefs(user_id)
        current_speed = prefs.get('speed_delay', 1.0)
        
        keyboard = [
            [InlineKeyboardButton("⚖️ متوسط (3.0s)", callback_data="set_speed_3.0"),
         InlineKeyboardButton("🐌 بطيء (5.0s)", callback_data="set_speed_5.0")],
        [InlineKeyboardButton("🛡️ آمن (8.0s)", callback_data="set_speed_8.0"),
         InlineKeyboardButton("🐢 آمن جداً (15.0s)", callback_data="set_speed_15.0")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="user_settings")]
        ]
        
        text = (
            f"⚡ *إعدادات السرعة*\n\n"
            f"السرعة الحالية: {current_speed}s\n\n"
            f"⚠️ **تحذير**: السرعات العالية قد تؤدي لحظر مؤقت\n"
            f"🔹 يُنصح بـ 1.0s أو أكثر للاستخدام الآمن\n\n"
            f"اختر السرعة المناسبة:"
        )
        
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def stop_all_checkers(self):
        """إيقاف جميع الفاحصات"""
        logger.info("stop_all_checkers: requested")
        # إيقاف مهام فاحصات المستخدمين
        for user_id, task in list(self.user_tasks.items()):
            # تحديث إعدادات المستخدم وإيقاف العميل أولاً
            try:
                prefs = self.get_user_prefs(user_id)
                prefs['running'] = False
                self.set_user_prefs(user_id, prefs)
            except Exception:
                pass
            client = self.user_clients.get(user_id)
            if client:
                try:
                    await asyncio.wait_for(client.disconnect(), timeout=3)
                except Exception:
                    pass
            # إلغاء وانتظار مدة محدودة لإيقاف المهمة
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            logger.info(f"stop_all_checkers: stopped task for user_id={user_id}")
        
        self.user_tasks.clear()
        self.user_clients.clear()
        logger.info("Stopped all user checkers")
    
    async def start_user_scan(self, user_id: int, context):
        """Start scanning for a specific user using their own accounts"""
        logger.info(f"start_user_scan: scheduling scan task for user_id={user_id}")
        async def scan_user_task():
            prefs = self.get_user_prefs(user_id)
            user_accounts = self.get_user_accounts(user_id)
            
            # Filter active accounts
            active_accounts = [acc for acc in user_accounts if acc.get('active', True)]
            
            if not active_accounts:
                await context.bot.send_message(user_id, "❌ لا توجد حسابات نشطة. يرجى إضافة حساب أو تفعيل حساب موجود")
                return
                
            # Smart load balancing - rotate between accounts
            current_account_index = 0
            
            client = await self.get_user_client(user_id, active_accounts[current_account_index])
            if not client:
                return
            try:
                await asyncio.wait_for(client.start(), timeout=10)
            except Exception as e:
                logger.error(f"start_user_scan: failed to start client for user_id={user_id}: {e}")
                try:
                    await context.bot.send_message(user_id, f"❌ فشل بدء الفحص: {e}")
                except Exception:
                    pass
                return
            # Track active client to allow external stop
            self.user_clients[user_id] = client
            msg = await context.bot.send_message(user_id, "🔍 بدء الفحص ...")
            self.user_status_msgs[user_id] = msg.message_id
            try:
                logger.info(f"scan_user_task: client started, entering loop for user_id={user_id}")
                while True:
                    prefs = self.get_user_prefs(user_id)
                    if not prefs.get('running', True):
                        logger.info(f"scan_user_task: running flag set to False, exiting for user_id={user_id}")
                        break
                    # تحديد نوع القائمة حسب وضع المستخدم
                    user_mode = prefs.get('mode', 'users')
                    if user_mode == 'channels':
                        usernames = self.get_user_channels(user_id)
                    else:
                        usernames = self.get_user_list(user_id)
                        
                    if not usernames:
                        await self._cancellable_sleep(user_id, 5)
                        continue
                    total = len(usernames)
                    for idx, username in enumerate(usernames, 1):
                        # تحقق من إشارة التوقف بسرعة داخل الحلقة
                        prefs = self.get_user_prefs(user_id)
                        if not prefs.get('running', True):
                            break
                        percent = int(idx/total*100)
                        # عرض حالة الفحص
                        checking_text = f"🔍 {idx}/{total} • {percent}%\nجاري فحص: @{username}..."
                        try:
                            await context.bot.edit_message_text(checking_text, chat_id=user_id, message_id=msg.message_id)
                        except Exception:
                            pass
                        
                        op_type = 'c' if user_mode == 'channels' else 'a'
                        try:
                            is_available, status = await asyncio.wait_for(
                                self.check_username(client, username, op_type, user_id=user_id), timeout=15
                            )
                        except asyncio.TimeoutError:
                            is_available, status = False, "TIMEOUT"
                        
                        # عرض النتيجة
                        result_text = f"🔍 {idx}/{total} • {percent}%\n@{username} → {status}"
                        try:
                            await context.bot.edit_message_text(result_text, chat_id=user_id, message_id=msg.message_id)
                        except Exception:
                            pass
                        if is_available:
                            claim_mode = prefs.get('claim_mode', True)
                            if claim_mode:
                                # تحقق سريع من إشارة الإيقاف قبل محاولة الحجز
                                prefs = self.get_user_prefs(user_id)
                                if not prefs.get('running', True):
                                    break
                                # وضع الحجز - محاولة حجز اليوزر
                                op_type = 'c' if user_mode == 'channels' else 'a'
                                try:
                                    claimed, _ = await asyncio.wait_for(
                                        self.claim_username(client, username, op_type, user_id=user_id), timeout=30
                                    )
                                except asyncio.TimeoutError:
                                    claimed = False
                                if claimed:
                                    account_name = active_accounts[current_account_index]['first_name']
                                    await context.bot.send_message(user_id, 
                                        f"🎉 تم حجز @{username} بنجاح!\n"
                                        f"👤 باستخدام حساب: {account_name}")
                                    # حفظ في قائمة اليوزرات المحجوزة
                                    self.save_claimed_username(user_id, username)
                                    # حذف من القائمة المناسبة
                                    if user_mode == 'channels':
                                        current = self.get_user_channels(user_id)
                                        if username in current:
                                            current.remove(username)
                                            self.write_user_channels(user_id, current)
                                    else:
                                        current = self.get_user_list(user_id)
                                        if username in current:
                                            current.remove(username)
                                            self.write_user_list(user_id, current)
                                            
                                    # التبديل إلى حساب آخر بعد الحجز لتجنب الحظر
                                    current_account_index = (current_account_index + 1) % len(active_accounts)
                                    try:
                                        await asyncio.wait_for(client.stop(), timeout=5)
                                    except Exception:
                                        pass
                                    # تحقّق سريع من إشارة الإيقاف قبل بدء عميل جديد
                                    prefs = self.get_user_prefs(user_id)
                                    if not prefs.get('running', True):
                                        break
                                    client = await self.get_user_client(user_id, active_accounts[current_account_index])
                                    try:
                                        await asyncio.wait_for(client.start(), timeout=10)
                                    except Exception as e:
                                        logger.error(f"scan_user_task: failed to rotate/start client for user_id={user_id}: {e}")
                                        try:
                                            await context.bot.send_message(user_id, f"❌ فشل تبديل الحساب/بدء الجلسة: {e}")
                                        except Exception:
                                            pass
                                        break
                                    # Update tracked client
                                    self.user_clients[user_id] = client
                            else:
                                # وضع الإشعار - إرسال إشعار فقط
                                type_text = 'قناة' if user_mode == 'channels' else 'يوزر'
                                await context.bot.send_message(user_id, f"🔔 {type_text} متاح: @{username}")
                        # استخدام سرعة المستخدم مع تأخير عشوائي إضافي للأمان
                        base_delay = prefs.get('speed_delay', 5)
                        random_delay = __import__('random').uniform(1, 3)  # تأخير عشوائي 1-3 ثانية
                        total_delay = base_delay + random_delay
                        await self._cancellable_sleep(user_id, total_delay)
            except asyncio.CancelledError:
                pass
            finally:
                try:
                    await asyncio.wait_for(client.stop(), timeout=5)
                except Exception:
                    pass
                logger.info(f"scan_user_task: client stopped and task finishing for user_id={user_id}")
                # Update UI message to reflect stop
                try:
                    await context.bot.edit_message_text("⏹️ تم إيقاف الفحص.", chat_id=user_id, message_id=msg.message_id)
                except Exception:
                    pass
                self.user_clients.pop(user_id, None)
                self.user_tasks.pop(user_id, None)
        # create task
        task = asyncio.create_task(scan_user_task())
        self.user_tasks[user_id] = task

    def get_public_url(self):
        """Get public URL for the web app"""
        if self.public_url:
            return self.public_url
        
        # Railway environment variable or default
        railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
        if railway_url:
            self.public_url = railway_url
            return railway_url
            
        # Default Railway URL
        self.public_url = "rr-production.up.railway.app"
        return self.public_url

    def get_status_text(self, user_id: int) -> str:
        """بناء نص حالة المستخدم"""
        prefs = self.get_user_prefs(user_id)
        running = prefs.get('running', False)
        mode = prefs.get('mode', 'users')
        accounts = self.get_user_accounts(user_id)
        total_accounts = len(accounts)
        active_accounts = len([a for a in accounts if a.get('active', True)])
        users_count = len(self.get_user_list(user_id))
        channels_count = len(self.get_user_channels(user_id))
        task_running = user_id in self.user_tasks
        status_line = "قيد العمل" if running and task_running else "متوقف"
        lines = []
        lines.append("📊 *حالة الفحص*")
        if total_accounts == 0:
            lines.append("❌ لا توجد حسابات مضافة بعد.")
            lines.append("أضف حساب من قائمة \"حساباتي\" للبدء.")
        else:
            lines.append(f"👤 الحسابات النشطة: {active_accounts}/{total_accounts}")
            lines.append(f"🧭 وضع الفحص: {'يوزرات' if mode=='users' else 'قنوات'}")
            lines.append(f"🔌 الحالة: {status_line}")
        lines.append("")
        lines.append(f"📥 عدد اليوزرات في قائمتك: {users_count}")
        lines.append(f"📺 عدد القنوات في قائمتك: {channels_count}")
        return "\n".join(lines)

    async def check_auth_status(self, query, context, user_id: int):
        """التحقق من إتمام المصادقة عبر الويب وإضافة الحساب"""
        try:
            auth_dir = "temp_auth"
            os.makedirs(auth_dir, exist_ok=True)
            final_file = os.path.join(auth_dir, f"{user_id}_auth.json")
            temp_file = os.path.join(auth_dir, f"{user_id}_temp.json")
            if os.path.exists(final_file):
                with open(final_file, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                phone = auth_data.get('phone')
                api_id = int(auth_data.get('api_id'))
                api_hash = auth_data.get('api_hash')
                session_base = auth_data.get('session_path')  # without .session
                src_session = f"{session_base}.session" if session_base else None
                # Copy session to user-specific path
                dest_session_base = self.get_user_session_path(user_id, phone)
                dest_session = f"{dest_session_base}.session"
                os.makedirs(os.path.dirname(dest_session), exist_ok=True)
                if src_session and os.path.exists(src_session):
                    try:
                        shutil.copy(src_session, dest_session)
                    except Exception as e:
                        logger.warning(f"Failed copying session file: {e}")
                # Build account dict
                account = {
                    'phone': phone,
                    'api_id': api_id,
                    'api_hash': api_hash,
                    'active': True,
                    'first_name': phone
                }
                # Try to fetch first_name
                try:
                    # استخدام معرفات طبيعية للتحقق
                    client = TelegramClient(
                        dest_session_base,
                        api_id,
                        api_hash,
                        device_model="Samsung SM-G973F",
                        system_version="Android 11",
                        app_version="8.9.2",
                        lang_code="ar",
                        system_lang_code="ar",
                        proxy=None,
                        connection_retries=1,
                        retry_delay=2
                    )
                    await client.connect()
                    me = await client.get_me()
                    if me and getattr(me, 'first_name', None):
                        account['first_name'] = me.first_name
                finally:
                    try:
                        await client.disconnect()
                    except:
                        pass
                self.add_user_account(user_id, account)
                # Cleanup temp files
                try:
                    os.remove(final_file)
                except:
                    pass
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                # Confirm to user
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("👤 حساباتي", callback_data="user_accounts")],
                    [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]
                ])
                await query.edit_message_text(
                    "✅ تم إضافة الحساب بنجاح!\nيمكنك إدارة حساباتك من قائمة \"حساباتي\".",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb
                )
                return
            elif os.path.exists(temp_file):
                public_url = self.get_public_url()
                web_url = f"https://{public_url}/auth/{user_id}"
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 فتح صفحة الويب", url=web_url)],
                    [InlineKeyboardButton("🔄 تحقق من الحالة", callback_data="check_web_auth")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="user_settings")]
                ])
                await query.edit_message_text(
                    "⌛ عملية المصادقة قيد الانتظار.\n"
                    "أدخل الكود في الصفحة ثم اضغط \"تحقق من الحالة\".",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb
                )
                return
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="user_settings")]
                ])
                await query.edit_message_text(
                    "ℹ️ لا توجد عملية مصادقة جارية.\nابدأ إضافة حساب جديد.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb
                )
                return
        except Exception as e:
            logger.error(f"check_auth_status error: {e}")
            await query.edit_message_text(f"❌ خطأ أثناء التحقق: {e}")
            return

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إظهار الحالة عبر الأمر /status"""
        user_id = update.effective_user.id
        status_text = self.get_status_text(user_id)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]])
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages from users"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Handle authentication flow
        if user_id in self.pending_auth:
            await self.handle_auth_flow(update, context, user_id, message_text)
            return
        
        # Handle username input
        if user_id in self.pending_input:
            await self.handle_username_input(update, context, user_id, message_text)
            return
        
        # Handle username replacement
        if user_id in self.pending_replacement:
            await self.handle_username_replacement(update, context, user_id, message_text)
            return
        
        prefs = self.get_user_prefs(user_id)
        
        if prefs.get('add_mode'):
            # Adding usernames
            await self.handle_username_input(update, context, user_id, message_text)
        elif prefs.get('replace_mode'):
            # Replacing usernames  
            await self.handle_username_replacement(update, context, user_id, message_text)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for adding usernames"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # تحقق من وضع إضافة الحسابات أولاً
        if user_id in self.pending_auth:
            await self.handle_auth_flow(update, context, user_id, text)
            return
            
        prefs = self.get_user_prefs(user_id)
        
        # تحقق من وضع الإدخال (إضافة أو استبدال يوزرات)
        if prefs.get('add_mode') or prefs.get('replace_mode'):
            # فحص وضع الاستبدال من الإعدادات أو من العلامة !
            replace_mode = prefs.get('replace_mode', False) or text.startswith('!')
            if text.startswith('!'):
                text = text[1:].strip()
                
            # محاوَلة استخراج معرفات من النص المرسل (يوزرات أو قنوات)
            import re
            usernames = re.findall(r'(?:https?://t\.me/)?@?([a-zA-Z0-9_]{5,32})', text)

            if not usernames:
                await update.message.reply_text("❌ لا توجد يوزرات صحيحة في الرسالة")
                return

            # تحديد نوع القائمة (يوزرات أو قنوات)
            user_mode = prefs.get('mode', 'users')
            
            if user_mode == 'channels':
                current_items = self.get_user_channels(user_id)
            else:
                current_items = self.get_user_list(user_id)

            if replace_mode:
                # إلغاء وضع الاستبدال بعد الاستخدام
                prefs['replace_mode'] = False
                self.set_user_prefs(user_id, prefs)
                # استبدال كامل
                all_items = list(dict.fromkeys(usernames))  # unique keep order
                added_count = len(all_items)
                
                if user_mode == 'channels':
                    self.write_user_channels(user_id, all_items)
                    item_type = "قناة"
                else:
                    self.write_user_list(user_id, all_items)
                    item_type = "اسم"
                
                await update.message.reply_text(
                    f"♻️ تم استبدال القائمة بنجاح بعدد {added_count} {item_type}."
                )
            else:
                # إضافة عادية
                new_items = [u for u in usernames if u not in current_items]
                if not new_items:
                    await update.message.reply_text("ℹ️ جميع الأسماء موجودة بالفعل في قائمتك")
                    return
                all_items = current_items + new_items
                
                if user_mode == 'channels':
                    self.write_user_channels(user_id, all_items)
                    item_type = "قنوات"
                else:
                    self.write_user_list(user_id, all_items)
                    item_type = "أسماء"
                
                await update.message.reply_text(
                    f"✅ تم إضافة {len(new_items)} {item_type} لقائمتك\n"
                    f"الإجمالي الآن: {len(all_items)}"
                )
                
                # إلغاء وضع الإضافة
                prefs['add_mode'] = False
                self.set_user_prefs(user_id, prefs)
                
                # تم تعطيل البدء التلقائي للفحص بناءً على طلب المستخدم

    async def document_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle .txt files containing usernames or channel links."""
        user_id = update.effective_user.id
        # download file
        file = await context.bot.get_file(update.message.document.file_id)
        path = await file.download_to_drive()
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f if l.strip()]
        import re
        text = '\n'.join(lines)
        usernames = re.findall(r'(?:https?://t\.me/)?@?([a-zA-Z0-9_]{5,32})', text)
        if not usernames:
            await update.message.reply_text("⚠️ لم يتم العثور على أي معرفات صالحة داخل الملف")
            return
        prefs = self.get_user_prefs(user_id)
        current_usernames = self.get_user_list(user_id)
        new_usernames = [u for u in usernames if u not in current_usernames]
        if new_usernames:
            all_usernames = current_usernames + new_usernames
            self.write_user_list(user_id, all_usernames)
            await update.message.reply_text(
                f"✅ تم إضافة {len(new_usernames)} اسم من الملف\nالإجمالي الآن: {len(all_usernames)} اسم"
            )
            # تم تعطيل البدء التلقائي للفحص بناءً على طلب المستخدم

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        from telegram.error import BadRequest
        err = context.error
        # Ignore harmless "message is not modified" errors
        if isinstance(err, BadRequest) and 'message is not modified' in str(err).lower():
            return
        logger.error(f"Unhandled error: {err}")

    def run_bot(self):
        """Start the Telegram bot"""
        application = Application.builder().token(self.config['bot_token']).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), self.document_handler))

        # Global error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("🚀 بوت صيد أسماء المستخدمين بدأ!")
        logger.info(f"Admin ID: {self.config['admin_id']}")
        
        # Send startup notification
        self.send_notification(
            "🚀 *البوت بدأ بنجاح!*\n"
            f"الوقت: {datetime.now().strftime('%H:%M:%S')}\n"
            f"جاهز لصيد الأسماء!"
        )
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def create_default_configs():
    """Create default configuration files if they don't exist"""
    configs = {
        'info.json': {
            'page1': {'first_name': 'Account1', 'phone': '+1234567890'},
            'page2': {'first_name': 'Account2', 'phone': '+1234567891'}
        },
        'type.json': {
            'user': 'a',  # account usernames
            'channel': 'c'  # channel usernames
        },
        'choice.json': {}
    }
    
    files = {
        'token': 'YOUR_BOT_TOKEN_HERE',
        'ID': '123456789',
        'channelName': 'Auto Channel',
        'channelabout': 'Auto-created channel',
        'user': 'testuser\nsamplename',
        'channel': ''
    }
    
    # Create JSON configs
    for filename, content in configs.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print(f"Created {filename}")
    
    # Create text files
    for filename, content in files.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

if __name__ == "__main__":
    # Create default configs if needed
    create_default_configs()
    
    # Start bot only (Web app runs separately on PythonAnywhere)
    try:
        bot = TelegramSniper()
        bot.public_url = "rr-production.up.railway.app"  # Railway hosting
        print("🚀 بوت صيد أسماء المستخدمين بدأ!")
        print(f"Admin ID: {bot.config.get('admin_id', 'Not set')}")
        bot.run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
