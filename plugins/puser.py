
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot import Bot
from config import ADMINS
from database.database import user_data, present_user, add_user

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('puser'))
async def premium_user_command(client: Client, message: Message):
    """Make a user premium (bypass verification)"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/puser <user_id>`\n\n**Example:** `/puser 123456789`")
            return
        
        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return
        
        # Check if user exists in database, if not add them
        if not await present_user(user_id):
            await add_user(user_id)
        
        # Update user to premium status
        await user_data.update_one(
            {'_id': user_id},
            {'$set': {'is_premium': True, 'premium_added_time': time.time()}}
        )
        
        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"
            
            success_msg = f"✅ **User made Premium successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Premium Status:** Active\n"
            success_msg += f"🚫 **Verification:** Bypassed"
            
        except Exception:
            success_msg = f"✅ **User made Premium successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Premium Status:** Active\n"
            success_msg += f"⚡ **Verification:** Bypassed"
        
        await message.reply(success_msg)
        
        # Notify the user about premium status
        try:
            notification_msg = (
                f"🎉 **Congratulations!**\n\n"
                f"✨ You have been granted **Premium Access**!\n\n"
                f"🚫 **No more verification needed**\n"
                f"⚡ **Direct file access**\n"
                f"👑 **Premium benefits activated**\n\n"
                f"Enjoy your premium experience!"
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ User made premium but couldn't notify them: {str(e)}")
        
    except Exception as e:
        await message.reply(f"❌ Error making user premium: {str(e)}")
