
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from bot import Bot
from config import ADMINS
from database.database import get_all_users

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('broadcast'))
async def broadcast_handler(client: Client, message: Message):
    """Broadcast message to all users who have started the bot"""
    
    # Check if there's a message to broadcast
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply(
            "**Usage:**\n"
            "Reply to a message with `/broadcast` or\n"
            "Use `/broadcast <your message>`"
        )
    
    # Get the broadcast message
    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
    else:
        broadcast_text = message.text.split(' ', 1)[1]
        broadcast_msg = await message.reply(broadcast_text)
    
    # Get all users from database
    users = await get_all_users()
    if not users:
        return await message.reply("❌ No users found in database!")
    
    # Start broadcast
    status_msg = await message.reply("🔄 **Broadcasting started...**")
    
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0
    
    for user in users:
        try:
            user_id = user.get('id') or user.get('user_id')
            if not user_id:
                continue
                
            if message.reply_to_message:
                await broadcast_msg.copy(chat_id=user_id)
            else:
                await client.send_message(chat_id=user_id, text=broadcast_text)
            
            successful += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                if message.reply_to_message:
                    await broadcast_msg.copy(chat_id=user_id)
                else:
                    await client.send_message(chat_id=user_id, text=broadcast_text)
                successful += 1
            except:
                unsuccessful += 1
                
        except InputUserDeactivated:
            deleted += 1
            # Remove deleted account from database
            try:
                from database.database import delete_user
                await delete_user(user_id)
            except:
                pass
                
        except UserIsBlocked:
            blocked += 1
            
        except PeerIdInvalid:
            # User hasn't started the bot yet, skip silently
            unsuccessful += 1
            
        except Exception as e:
            unsuccessful += 1
            print(f"Error broadcasting to {user_id}: {e}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.1)
    
    # Update status with final results
    await status_msg.edit(
        f"✅ **Broadcast Completed!**\n\n"
        f"📊 **Results:**\n"
        f"• ✅ Successful: `{successful}`\n"
        f"• 🚫 Blocked: `{blocked}`\n" 
        f"• 🗑 Deleted: `{deleted}`\n"
        f"• ❌ Failed: `{unsuccessful}`\n"
        f"• 📋 Total: `{len(users)}`"
    )

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('users'))
async def users_stats(client: Client, message: Message):
    """Get user statistics"""
    users = await get_all_users()
    if not users:
        return await message.reply("❌ No users found in database!")
    
    await message.reply(f"👥 **Total Users:** `{len(users)}`")
