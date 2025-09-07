
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot import Bot
from config import ADMINS, IS_VERIFY, VERIFY_EXPIRE
from helper_func import get_verification_stats

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('count'))
async def count_command(client: Client, message: Message):
    """Show verification statistics in the same format as startup logs"""
    try:
        if not IS_VERIFY:
            await message.reply("🔓 **Verification is disabled**")
            return
        
        stats = await get_verification_stats()
        
        # Create the formatted message
        stats_msg = "=" * 50 + "\n"
        stats_msg += "📊 VERIFICATION STATISTICS (Last 24 Hours)\n"
        stats_msg += "=" * 50 + "\n"
        stats_msg += f"✅ Total Active Verified Users: {stats['total_verified']}\n"
        stats_msg += f"🆕 New Verifications (24h): {len(stats['verified_in_24h'])}\n\n"
        
        if stats['verified_in_24h']:
            stats_msg += "🔔 Recent Verifications:\n"
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
                    user_info = await client.get_users(user_id)
                    username = f"@{user_info.username}" if user_info.username else "No username"
                    first_name = user_info.first_name or "Unknown"
                    
                    stats_msg += f"  {i}. 👤 {first_name} ({username})\n"
                    stats_msg += f"     🆔 ID: {user_id}\n"
                    stats_msg += f"     ⏰ Verified: {verified_str}\n"
                    stats_msg += f"     ⏳ Expires in: {remaining_str}\n"
                except:
                    # If can't get user info, show basic details
                    stats_msg += f"  {i}. 🆔 User ID: {user_id}\n"
                    stats_msg += f"     ⏰ Verified: {verified_str}\n"
                    stats_msg += f"     ⏳ Expires in: {remaining_str}\n"
            
            if len(stats['verified_in_24h']) > 10:
                stats_msg += f"  ... and {len(stats['verified_in_24h']) - 10} more users\n"
        else:
            stats_msg += "📭 No new verifications in the last 24 hours\n"
        
        stats_msg += "=" * 50
        
        await message.reply(f"```\n{stats_msg}\n```")
        
    except Exception as e:
        await message.reply(f"❌ Error getting verification statistics: {str(e)}")
