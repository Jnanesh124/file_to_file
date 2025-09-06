
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from bot import Bot
from config import *
from helper_func import encode

# Store messages for auto-deletion
pending_deletions = {}

async def schedule_auto_delete(client: Client, sent_message: Message, original_file_id: str = None):
    """Schedule a message for auto-deletion"""
    if not AUTO_DELETE:
        return
    
    message_id = sent_message.id
    chat_id = sent_message.chat.id
    
    # Store message info for deletion
    pending_deletions[f"{chat_id}_{message_id}"] = {
        'chat_id': chat_id,
        'message_id': message_id,
        'original_file_id': original_file_id,
        'delete_time': DELETE_AFTER
    }
    
    # Send notification about auto-deletion
    if NOTIFICATION:
        notification_msg = await sent_message.reply(
            NOTIFICATION,
            quote=True,
            disable_web_page_preview=True
        )
        
        # Schedule notification deletion too
        pending_deletions[f"{chat_id}_{notification_msg.id}"] = {
            'chat_id': chat_id,
            'message_id': notification_msg.id,
            'delete_time': DELETE_AFTER + 5  # Delete notification 5 seconds after main file
        }
    
    # Wait for deletion time
    await asyncio.sleep(DELETE_AFTER)
    
    # Delete the main message
    try:
        await client.delete_messages(chat_id, message_id)
        
        # Send deletion inform message with get again button if enabled
        if DELETE_INFORM and GET_AGAIN and original_file_id:
            buttons = []
            if original_file_id:
                buttons.append([InlineKeyboardButton("🔄 GET FILE AGAIN", callback_data=f"get_again_{original_file_id}")])
            
            await client.send_message(
                chat_id=chat_id,
                text=DELETE_INFORM,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
                disable_web_page_preview=True
            )
        elif DELETE_INFORM:
            await client.send_message(
                chat_id=chat_id,
                text=DELETE_INFORM,
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"Error deleting message: {e}")
    
    # Clean up from pending deletions
    key = f"{chat_id}_{message_id}"
    if key in pending_deletions:
        del pending_deletions[key]

# Callback handler for "GET FILE AGAIN" button
@Bot.on_callback_query(filters.regex(r"get_again_(.+)"))
async def get_file_again(client: Client, query):
    """Handle get file again requests"""
    try:
        file_id = query.matches[0].group(1)
        user_id = query.from_user.id
        
        # Check subscription status
        from plugins.start import is_user_subscribed
        if not await is_user_subscribed(client, query):
            return await query.answer("❌ Please join all channels first!", show_alert=True)
        
        # Check verification status if enabled
        if IS_VERIFY:
            from database.database import get_verify_status
            verify_status = await get_verify_status(user_id)
            if not verify_status['is_verified']:
                return await query.answer("❌ Please verify first by clicking /start", show_alert=True)
        
        await query.answer("🔄 Fetching file again...", show_alert=True)
        
        # Decode and send file again
        from helper_func import decode
        decoded = await decode(file_id)
        
        if decoded.startswith("get-"):
            parts = decoded.split("-")
            if len(parts) == 2:  # Single file
                _, msg_id = parts
                msg_id = abs(int(msg_id)) // abs(client.db_channel.id)
                
                try:
                    msg = await client.get_messages(client.db_channel.id, msg_id)
                    if msg:
                        sent_msg = await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)
                        # Schedule auto-delete for the new message
                        asyncio.create_task(schedule_auto_delete(client, sent_msg, file_id))
                except Exception as e:
                    await query.message.reply("❌ File not found or may have been deleted.")
        
        # Delete the get again message
        try:
            await query.message.delete()
        except:
            pass
            
    except Exception as e:
        await query.answer("❌ Error retrieving file", show_alert=True)
