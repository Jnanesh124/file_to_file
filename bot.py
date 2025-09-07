
from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNELS, CHANNEL_ID, PORT
import pyrogram.utils

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        if FORCE_SUB_CHANNELS:
            self.invitelinks = []
            try:
                for channel_id in FORCE_SUB_CHANNELS:
                    link = (await self.get_chat(channel_id)).invite_link
                    if not link:
                        await self.export_chat_invite_link(channel_id)
                        link = (await self.get_chat(channel_id)).invite_link
                    self.invitelinks.append(link)
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning("Bot can't Export Invite link from Force Sub Channels!")
                self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNELS value and Make sure Bot is Admin in all channels with Invite Users via Link Permission, Current Force Sub Channels: {FORCE_SUB_CHANNELS}")
                self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/ultroid_official for support")
                sys.exit()
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id=db_channel.id, text="Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(f"Error occurred: {e}")
            self.LOGGER(__name__).warning(f"CHANNEL_ID: {CHANNEL_ID}, DB Channel ID: {db_channel.id if 'db_channel' in locals() else 'N/A'}")
            self.LOGGER(__name__).warning(f"Make sure bot is Admin in DB Channel, and Double-check the CHANNEL_ID value.")
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/ultroid_official for support")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/ultroid_official")
        self.LOGGER(__name__).info(f""" \n\n       
(っ◔◡◔)っ ♥ ULTROIDOFFICIAL ♥
░╚════╝░░╚════╝░╚═════╝░╚══════╝
                                          """)
        
        # Show verification statistics on startup
        try:
            from helper_func import get_verification_stats
            from config import IS_VERIFY
            import time
            
            if IS_VERIFY:
                stats = await get_verification_stats()
                self.LOGGER(__name__).info("=" * 50)
                self.LOGGER(__name__).info("📊 VERIFICATION STATISTICS (Last 24 Hours)")
                self.LOGGER(__name__).info("=" * 50)
                self.LOGGER(__name__).info(f"✅ Total Active Verified Users: {stats['total_verified']}")
                self.LOGGER(__name__).info(f"🆕 New Verifications (24h): {len(stats['verified_in_24h'])}")
                
                if stats['verified_in_24h']:
                    self.LOGGER(__name__).info("\n🔔 Recent Verifications:")
                    for i, user_data in enumerate(stats['verified_in_24h'][:10], 1):  # Show max 10
                        user_id = user_data['user_id']
                        verified_time = user_data['verified_time']
                        remaining_time = user_data['remaining_time']
                        
                        # Format verified time
                        verified_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(verified_time))
                        
                        # Format remaining time
                        remaining_hours = int(remaining_time // 3600)
                        remaining_mins = int((remaining_time % 3600) // 60)
                        remaining_str = f"{remaining_hours}h {remaining_mins}m"
                        
                        try:
                            # Try to get user info
                            user_info = await self.get_users(user_id)
                            username = f"@{user_info.username}" if user_info.username else "No username"
                            first_name = user_info.first_name or "Unknown"
                            
                            self.LOGGER(__name__).info(
                                f"  {i}. 👤 {first_name} ({username})\n"
                                f"     🆔 ID: {user_id}\n"
                                f"     ⏰ Verified: {verified_str}\n"
                                f"     ⏳ Expires in: {remaining_str}"
                            )
                        except:
                            # If can't get user info, show basic details
                            self.LOGGER(__name__).info(
                                f"  {i}. 🆔 User ID: {user_id}\n"
                                f"     ⏰ Verified: {verified_str}\n"
                                f"     ⏳ Expires in: {remaining_str}"
                            )
                    
                    if len(stats['verified_in_24h']) > 10:
                        self.LOGGER(__name__).info(f"  ... and {len(stats['verified_in_24h']) - 10} more users")
                else:
                    self.LOGGER(__name__).info("📭 No new verifications in the last 24 hours")
                
                self.LOGGER(__name__).info("=" * 50)
            else:
                self.LOGGER(__name__).info("🔓 Verification is disabled")
                
        except Exception as e:
            self.LOGGER(__name__).warning(f"Could not load verification statistics: {e}")
        
        self.username = usr_bot_me.username
        #web-response
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")
