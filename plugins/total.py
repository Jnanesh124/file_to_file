

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

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('removepremium'))
async def remove_premium_command(client: Client, message: Message):
    """Remove premium status from a user"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/removepremium <user_id>`\n\n**Example:** `/removepremium 123456789`")
            return
        
        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return
        
        # Check if user exists in database
        if not await present_user(user_id):
            await message.reply("❌ **User not found** in database.")
            return
        
        # Update user to remove premium status
        await user_data.update_one(
            {'_id': user_id},
            {'$set': {'is_premium': False, 'premium_removed_time': time.time()}}
        )
        
        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"
            
            success_msg = f"❌ **Premium status removed successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Premium Status:** Removed\n"
            success_msg += f"🔒 **Verification:** Required"
            
        except Exception:
            success_msg = f"❌ **Premium status removed successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Premium Status:** Removed\n"
            success_msg += f"⚡ **Verification:** Required"
        
        await message.reply(success_msg)
        
        # Notify the user about premium removal
        try:
            notification_msg = (
                f"⚠️ **Premium Access Removed**\n\n"
                f"❌ Your premium access has been removed.\n\n"
                f"🔒 **Verification is now required** to access files\n"
                f"📋 Use `/start` to verify again\n\n"
                f"Contact support if you think this is a mistake."
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ Premium removed but couldn't notify user: {str(e)}")
        
    except Exception as e:
        await message.reply(f"❌ Error removing premium status: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('premiumlist'))
async def premium_list_command(client: Client, message: Message):
    """Show list of all premium users"""
    try:
        premium_users = []
        
        # Find all premium users
        async for user in user_data.find({'is_premium': True}):
            user_id = user.get('_id')
            premium_added_time = user.get('premium_added_time', 0)
            premium_users.append({
                'user_id': user_id,
                'added_time': premium_added_time
            })
        
        if not premium_users:
            await message.reply("📭 **No premium users found.**")
            return
        
        # Sort by added time (newest first)
        premium_users.sort(key=lambda x: x['added_time'], reverse=True)
        
        stats_msg = "=" * 50 + "\n"
        stats_msg += "👑 PREMIUM USERS LIST\n"
        stats_msg += "=" * 50 + "\n"
        stats_msg += f"📊 Total Premium Users: {len(premium_users)}\n\n"
        
        # Show premium users (max 20)
        for i, user_data_item in enumerate(premium_users[:20], 1):
            user_id = user_data_item['user_id']
            added_time = user_data_item['added_time']
            
            # Format added time
            if added_time:
                added_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(added_time))
            else:
                added_str = "Unknown"
            
            try:
                # Try to get user info
                user_info = await client.get_users(user_id)
                username = f"@{user_info.username}" if user_info.username else "No username"
                first_name = user_info.first_name or "Unknown"
                
                stats_msg += f"  {i}. 👤 {first_name} ({username})\n"
                stats_msg += f"     🆔 ID: {user_id}\n"
                stats_msg += f"     ⏰ Added: {added_str}\n\n"
            except:
                # If can't get user info, show basic details
                stats_msg += f"  {i}. 🆔 User ID: {user_id}\n"
                stats_msg += f"     ⏰ Added: {added_str}\n\n"
        
        if len(premium_users) > 20:
            stats_msg += f"  ... and {len(premium_users) - 20} more premium users\n"
        
        stats_msg += "=" * 50
        
        await message.reply(f"```\n{stats_msg}\n```")
        
    except Exception as e:
        await message.reply(f"❌ Error getting premium users list: {str(e)}")
