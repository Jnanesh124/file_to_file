
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot import Bot
from config import ADMINS
from database.database import user_data

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('total'))
async def total_command(client: Client, message: Message):
    """Show total number of users who clicked file links"""
    try:
        total_clicks = 0
        unique_users = set()
        
        # Count total clicks and unique users
        async for user in user_data.find():
            user_id = user.get('_id')
            click_count = user.get('file_clicks', 0)
            
            if click_count > 0:
                total_clicks += click_count
                unique_users.add(user_id)
        
        stats_msg = "=" * 40 + "\n"
        stats_msg += "📊 FILE LINK STATISTICS\n"
        stats_msg += "=" * 40 + "\n"
        stats_msg += f"🔗 Total File Link Clicks: {total_clicks}\n"
        stats_msg += f"👥 Unique Users Who Clicked: {len(unique_users)}\n"
        stats_msg += f"📈 Average Clicks per User: {total_clicks / len(unique_users) if unique_users else 0:.1f}\n"
        stats_msg += "=" * 40
        
        await message.reply(f"```\n{stats_msg}\n```")
        
    except Exception as e:
        await message.reply(f"❌ Error getting file statistics: {str(e)}")
