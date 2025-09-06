import asyncio
import random
import string
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot import Bot
from config import *
from database.database import *
from database.database import present_user, add_user
from helper_func import *

# ================== HELPER WRAPPERS ================== #
async def is_user_subscribed(client: Client, update):
    """Wrapper to allow Message or CallbackQuery for subscription check"""
    if isinstance(update, Message):
        return await is_subscribed(None, client, update)
    elif isinstance(update, CallbackQuery):
        return await is_subscribed(None, client, update.message)
    return False

async def get_user_non_joined_channels(client: Client, update):
    """Wrapper to allow Message or CallbackQuery for non-joined channels"""
    user_id = update.from_user.id if hasattr(update, "from_user") else None
    return await get_non_joined_channels(client, user_id)

# ================== START HANDLER ================== #
@Bot.on_message(filters.private & filters.command("start"))
async def start_handler(client: Client, message: Message):
    id = message.from_user.id
    
    # Add user to database if not present
    if not await present_user(id):
        await add_user(id)

    # ================== FORCE SUB CHECK ================== #
    if not await is_user_subscribed(client, message):
        checking_msg = await message.reply("🔄 **Checking your membership status...**\n\nPlease wait while I verify your subscription...")
        await asyncio.sleep(2)

        non_joined_channels = await get_user_non_joined_channels(client, message)
        buttons = []

        if hasattr(client, 'invitelinks') and client.invitelinks and non_joined_channels:
            for channel_index, channel_id in non_joined_channels:
                if channel_index < len(client.invitelinks):
                    buttons.append([InlineKeyboardButton(f"Join Channel {channel_index+1}", url=client.invitelinks[channel_index])])

        buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")])

        await checking_msg.delete()
        return await message.reply(
            FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    # ================== TOKEN VERIFICATION AFTER SUB ================== #
    if IS_VERIFY:
        verify_status = await get_verify_status(id)

        # Case 1: User clicked a verify link (/start verify_token)
        if "verify_" in message.text:
            checking_msg = await message.reply("🔄 **Checking your token...**\n\nPlease wait while I validate your verification token.")
            await asyncio.sleep(2)
            await checking_msg.delete()

            _, token = message.text.split("_", 1)

            if verify_status['verify_token'] != token:
                return await message.reply("❌ Your token is invalid or expired.\n\nClick /start again to get a new one.")

            await update_verify_status(id, is_verified=True, verified_time=time.time())
            return await message.reply("✅ Your token was successfully verified!\n\nValid for: 24 hours.", protect_content=False, quote=True)

        # Case 2: User is not verified yet (clicked plain /start)
        if not verify_status['is_verified']:
            checking_msg = await message.reply("🔄 **Checking your token...**\n\nPlease wait while I validate your verification token.")
            await asyncio.sleep(2)
            await checking_msg.delete()

            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await update_verify_status(id, verify_token=token, link="")
            link = await get_shortlink(
                SHORTLINK_URL,
                SHORTLINK_API,
                f'https://telegram.dog/{client.username}?start=verify_{token}'
            )
            btn = [
                [InlineKeyboardButton("Click here to Verify ✅", url=link)],
                [InlineKeyboardButton("How to use the bot", url=TUT_VID)]
            ]
            return await message.reply(
                f"⚠️ You need to verify before using the bot.\n\n"
                f"Your token has expired or is missing.\n"
                f"Click below to refresh your token.\n\n"
                f"⏳ Token Timeout: {get_exp_time(VERIFY_EXPIRE)}",
                reply_markup=InlineKeyboardMarkup(btn),
                protect_content=False,
                quote=True
            )

    # ================== HANDLE FILE REQUESTS ================== #
    if len(message.text) > 7:  # More than just "/start"
        file_id = message.text.split(" ", 1)[1]
        
        # Check if it's a file ID (not a verify token)
        if not file_id.startswith("verify_"):
            try:
                from helper_func import decode, get_messages
                
                # Decode the file ID
                decoded = await decode(file_id)
                
                # Handle batch files (get-123-456 format)
                if decoded.startswith("get-"):
                    parts = decoded.split("-")
                    if len(parts) == 3:  # Batch: get-start_id-end_id
                        _, start_id, end_id = parts
                        start_msg_id = abs(int(start_id)) // abs(client.db_channel.id)
                        end_msg_id = abs(int(end_id)) // abs(client.db_channel.id)
                        
                        # Get range of messages
                        msg_ids = list(range(start_msg_id, end_msg_id + 1))
                        messages = await get_messages(client, msg_ids)
                        
                        for msg in messages:
                            if msg:
                                sent_msg = await msg.copy(chat_id=message.from_user.id, protect_content=PROTECT_CONTENT)
                                
                                # Schedule auto-delete if enabled
                                if AUTO_DELETE:
                                    from plugins.auto_delete import schedule_auto_delete
                                    asyncio.create_task(schedule_auto_delete(client, sent_msg, file_id))
                                
                                await asyncio.sleep(0.5)  # Avoid flood
                        return
                    
                    elif len(parts) == 2:  # Single file: get-msg_id
                        _, msg_id = parts
                        msg_id = abs(int(msg_id)) // abs(client.db_channel.id)
                        
                        try:
                            # Get single message from database channel
                            msg = await client.get_messages(client.db_channel.id, msg_id)
                            if msg:
                                sent_msg = await msg.copy(chat_id=message.from_user.id, protect_content=PROTECT_CONTENT)
                                
                                # Schedule auto-delete if enabled
                                if AUTO_DELETE:
                                    from plugins.auto_delete import schedule_auto_delete
                                    asyncio.create_task(schedule_auto_delete(client, sent_msg, file_id))
                                return
                        except Exception:
                            pass
                
                return await message.reply("❌ File not found or may have been deleted.")
                    
            except Exception as e:
                return await message.reply("❌ Invalid file link or file not found.")
    
    # ================== NORMAL START (already verified) ================== #
    return await message.reply("✅ Welcome back! You are already verified and subscribed.")


# ================== CALLBACK HANDLER FOR TRY AGAIN ================== #
@Bot.on_callback_query(filters.regex("check_sub"))
async def recheck_subscription(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    # Answer the callback query first
    await query.answer("🔄 Checking membership status...")

    checking_msg = await query.message.edit_text("🔄 **Re-checking your membership...**\n\nPlease wait...")
    await asyncio.sleep(2)

    if not await is_user_subscribed(client, query):
        non_joined_channels = await get_user_non_joined_channels(client, query)
        buttons = []

        if hasattr(client, 'invitelinks') and client.invitelinks and non_joined_channels:
            for channel_index, channel_id in non_joined_channels:
                if channel_index < len(client.invitelinks):
                    buttons.append([InlineKeyboardButton(f"Join Channel {channel_index+1}", url=client.invitelinks[channel_index])])

        buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")])

        return await checking_msg.edit_text(
            text=FORCE_MSG.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name,
                username=None if not query.from_user.username else '@' + query.from_user.username,
                mention=query.from_user.mention,
                id=query.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    # User is now subscribed, show success message
    await checking_msg.edit_text("✅ **Membership verified!**\n\nYou have successfully joined all required channels.")
    
    # Wait a moment then show the start message
    await asyncio.sleep(2)
    await checking_msg.edit_text("✅ Welcome! You are now verified and subscribed.\n\nYou can now use the bot normally.")
