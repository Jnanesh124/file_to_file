
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, ChannelBanned, ChannelPrivate, ChatAdminRequired, PeerIdInvalid
from bot import Bot
import asyncio
import time
import random
import string
from config import *
from database.database import (
    add_user, present_user, get_verify_status, update_verify_status, 
    user_data, is_banned_user, increment_file_clicks
)
from helper_func import (
    help_command,
    is_user_subscribed,
    get_user_non_joined_channels,
    recheck_subscription,
    puser_handler,
    removepremium_handler,
    premiumlist_handler,
    ban_user_handler,
    unban_user_handler,
    listban_handler,
    total_handler,
    decode,
    get_shortlink,
    get_exp_time
)

@Bot.on_callback_query(filters.regex("check_sub"))
async def check_subscription_callback(client: Client, query: CallbackQuery):
    """Handle Try Again button click - directly auto-start bot"""
    try:
        await query.answer("🔄 Starting bot...")
    except:
        pass

    # Delete the subscription message
    try:
        await query.message.delete()
    except:
        pass
    
    # Auto-trigger /start command
    class FakeMessage:
        def __init__(self, original_query):
            self.from_user = original_query.from_user
            self.chat = original_query.message.chat
            self.text = "/start"
            self.message_id = original_query.message.message_id
            
        async def reply(self, *args, **kwargs):
            return await client.send_message(self.chat.id, *args, **kwargs)
        
        async def reply_text(self, *args, **kwargs):
            return await client.send_message(self.chat.id, *args, **kwargs)
    
    fake_msg = FakeMessage(query)
    await start_handler(client, fake_msg)

@Bot.on_message(filters.private & filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Check if user is banned
    if await is_banned_user(user_id):
        return await message.reply(
            "🚫 **You are banned from using this bot.**\n\n"
            "Contact support if you think this is a mistake."
        )

    # Add user to DB if not present
    if not await present_user(user_id):
        await add_user(user_id)

    # ====== FORCE SUBSCRIPTION CHECK ====== #
    if not await is_user_subscribed(client, message):
        checking_msg = await message.reply("🔄 **Checking your membership status...**")
        await asyncio.sleep(1)

        non_joined_channels = await get_user_non_joined_channels(client, message)
        buttons = []

        if hasattr(client, 'invitelinks') and client.invitelinks and non_joined_channels:
            for index, channel_id in non_joined_channels:
                if index < len(client.invitelinks):
                    buttons.append([InlineKeyboardButton(f"Join Channel {index+1}", url=client.invitelinks[index])])
        
        # Add "Try Again" button
        buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{BOT_USERNAME}?start=restart")])

        await checking_msg.delete()
        
        # Only send markup if there are buttons
        if buttons:
            return await message.reply(
                FORCE_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=f"@{message.from_user.username}" if message.from_user.username else None,
                    mention=message.from_user.mention,
                    id=user_id
                ),
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
        else:
            return await message.reply(
                FORCE_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=f"@{message.from_user.username}" if message.from_user.username else None,
                    mention=message.from_user.mention,
                    id=user_id
                ),
                disable_web_page_preview=True
            )

    # ====== VERIFICATION CHECK ====== #
    if IS_VERIFY:
        verify_status = await get_verify_status(user_id)

        # Case 1: User clicked /start verify_token
        if "verify_" in message.text:
            checking_msg = await message.reply("🔄 **Checking your token...**")
            await asyncio.sleep(1)
            await checking_msg.delete()

            _, token = message.text.split("_", 1)

            if verify_status['verify_token'] != token:
                return await message.reply("❌ Your token is invalid or expired.\nClick /start again to get a new one.")

            await update_verify_status(user_id, is_verified=True, verified_time=time.time())
            await message.reply("✅ Your token was successfully verified!\nValid for 24 hours.")

            # Send notification to admin about successful verification
            try:
                admin_msg = (
                    f"🔔 **New User Verified Successfully!**\n\n"
                    f"👤 **User:** {message.from_user.first_name}"
                    f"{' ' + message.from_user.last_name if message.from_user.last_name else ''}\n"
                    f"🆔 **User ID:** `{user_id}`\n"
                    f"📧 **Username:** @{message.from_user.username if message.from_user.username else 'None'}\n"
                    f"⏰ **Verified At:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
                    f"⏳ **Valid Until:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + VERIFY_EXPIRE))}"
                )

                # Send to unique admins only (remove duplicates)
                unique_admins = list(set(ADMINS))
                for admin_id in unique_admins:
                    try:
                        await client.send_message(admin_id, admin_msg)
                    except Exception as e:
                        print(f"Failed to send verification notification to admin {admin_id}: {e}")

                print(f"✅ User {user_id} ({message.from_user.first_name}) verified successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                print(f"Error sending admin notification: {e}")

            # Continue to normal start message after successful verification
            await message.reply(
                START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=f"@{message.from_user.username}" if message.from_user.username else None,
                    mention=message.from_user.mention,
                    id=user_id
                )
            )
            return

        # Case 2: Check if user is verified (with expiry check)
        current_time = time.time()
        is_expired = False

        if verify_status['is_verified'] and verify_status['verified_time']:
            time_elapsed = current_time - verify_status['verified_time']
            is_expired = time_elapsed > VERIFY_EXPIRE

            if is_expired:
                print(f"⏰ User {user_id} verification expired. Elapsed: {int(time_elapsed/3600)}h {int((time_elapsed%3600)/60)}m")

        # Check if user is premium
        user_doc = await user_data.find_one({'_id': user_id})
        is_premium = user_doc.get('is_premium', False) if user_doc else False

        # If user is not premium, check verification status
        if not is_premium:
            if not verify_status['is_verified'] or is_expired:
                checking_msg = await message.reply("🔄 **Checking your token...**")
                await asyncio.sleep(1)
                await checking_msg.delete()

                token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                await update_verify_status(user_id, verify_token=token, link="")
                link = await get_shortlink(
                    SHORTLINK_URL,
                    SHORTLINK_API,
                    f'https://telegram.dog/{client.username}?start=verify_{token}'
                )

                btn = [
                    [InlineKeyboardButton("Click here to Verify ✅", url=link)],
                    [InlineKeyboardButton("How to use this bot?", url=TUT_VID)]
                ]

                return await message.reply(
                    f"⚠️ You need to verify before using the bot.\n"
                    f"Your token has expired or is missing.\nClick below to refresh your token.\n\n"
                    f"⏳ Token Timeout: {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn)
                )

    # ====== HANDLE FILE REQUESTS ====== #
    if len(message.text) > 7:
        try:
            token = message.text.split(" ", 1)[1]
        except:
            return

        # Check if it's a secure token (starts with 'file_')
        if token.startswith('file_'):
            # Extract the actual token (remove 'file_' prefix)
            actual_token = token.replace('file_', '', 1)
            
            from helper_func import get_file_ids_from_token
            message_ids = await get_file_ids_from_token(actual_token)

            if not message_ids:
                return await message.reply("Invalid or expired link!")

            # Handle both single and batch files
            if isinstance(message_ids, list):
                if len(message_ids) == 2:
                    start, end = message_ids[0], message_ids[1]
                    if start <= end:
                        ids = range(start, end + 1)
                    else:
                        ids = []
                        i = start
                        while True:
                            ids.append(i)
                            i -= 1
                            if i < end:
                                break
                else:
                    ids = message_ids
            else:
                ids = [message_ids]
        else:
            # Legacy base64 system
            try:
                decoded_string = await decode(token)
                argument = decoded_string.split("-")

                if len(argument) == 3:
                    try:
                        start = int(int(argument[1]) / abs(client.db_channel.id))
                        end = int(int(argument[2]) / abs(client.db_channel.id))
                    except:
                        return

                    if start <= end:
                        ids = range(start, end + 1)
                    else:
                        ids = []
                        i = start
                        while True:
                            ids.append(i)
                            i -= 1
                            if i < end:
                                break
                elif len(argument) == 2:
                    try:
                        ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                    except:
                        return
            except:
                return

        # Process message IDs
        if 'ids' in locals():
            files_sent = 0
            files_skipped = 0
            
            for msg_id in ids:
                if msg_id is None: 
                    continue
                try:
                    msg = await client.get_messages(chat_id=client.db_channel.id, message_ids=msg_id)
                    print(f"📥 Retrieved message for user {user_id}, msg_id: {msg_id}, msg exists: {msg is not None}, empty: {msg.empty if msg else 'N/A'}")

                except ChannelBanned:
                    print(f"❌ Channel banned - user {user_id}, msg_id: {msg_id}")
                    await message.reply_text(
                        "❌ **Database Channel Banned**\n\n"
                        "The database channel has been banned by Telegram.\n"
                        f"Support: @{SUPPORT_GROUP if SUPPORT_GROUP else OWNER}"
                    )
                    return
                except ChannelPrivate:
                    print(f"❌ Channel private - user {user_id}, msg_id: {msg_id}")
                    await message.reply_text(
                        "❌ **Database Channel Private/Inaccessible**\n\n"
                        f"Support: @{SUPPORT_GROUP if SUPPORT_GROUP else OWNER}"
                    )
                    return
                except ChatAdminRequired:
                    print(f"❌ Admin required - user {user_id}, msg_id: {msg_id}")
                    await message.reply_text(
                        "❌ **Bot Permission Issue**\n\n"
                        f"Support: @{SUPPORT_GROUP if SUPPORT_GROUP else OWNER}"
                    )
                    return
                except FloodWait as e:
                    print(f"❌ Flood wait for user {user_id}, msg_id: {msg_id}: {e}")
                    await message.reply_text(f"Telegram is busy. Please try again in {e.value} seconds.")
                    return
                except PeerIdInvalid:
                    print(f"❌ Peer ID Invalid for user {user_id}, msg_id: {msg_id}")
                    await message.reply_text("❌ Bot error: Missing channel access. Please contact the admin.")
                    return
                except Exception as e:
                    print(f"❌ Error fetching message - user {user_id}, msg_id: {msg_id}, error: {e}")
                    await message.reply_text(
                        "❌ **Error Accessing File**\n\n"
                        f"Support: @{SUPPORT_GROUP if SUPPORT_GROUP else OWNER}"
                    )
                    return

                if not msg or msg.empty:
                    print(f"⚠️ EMPTY MESSAGE DETECTED - user {user_id}, msg_id: {msg_id}")
                    files_skipped += 1
                    continue

                try:
                    print(f"📤 Attempting to copy message to user {user_id}")
                    sent_msg = await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)

                    if sent_msg:
                        print(f"✅ Message copied successfully to user {user_id}")
                        files_sent += 1
                        await increment_file_clicks(user_id)
                        if AUTO_DELETE:
                            from plugins.auto_delete import schedule_auto_delete
                            asyncio.create_task(schedule_auto_delete(client, sent_msg, token, show_notification=False))
                        await asyncio.sleep(0.5)
                    else:
                        files_skipped += 1
                        continue
                except Exception as copy_error:
                    print(f"❌ Copy error: {copy_error}")
                    files_skipped += 1
                    continue
            
            if files_sent > 0 and files_skipped > 0:
                status_msg = f"✅ Sent {files_sent} file(s) successfully.\n⚠️ {files_skipped} file(s) were deleted from database channel.\n\n"
                if AUTO_DELETE and NOTIFICATION:
                    status_msg += NOTIFICATION
                await message.reply_text(status_msg, disable_web_page_preview=True)
            elif files_sent > 0 and files_skipped == 0:
                if AUTO_DELETE and NOTIFICATION:
                    await message.reply_text(NOTIFICATION, disable_web_page_preview=True)
            elif files_sent == 0 and files_skipped > 0:
                await message.reply_text(
                    f"❌ **Database channel issue detected**\n\n"
                    f"All {files_skipped} file(s) were deleted.\n\n"
                    f"Support: @{SUPPORT_GROUP if SUPPORT_GROUP else OWNER}"
                )
            
            del ids
            return
        else:
            return await message.reply_text("❌ File not found or may have been deleted.")

    # Normal start message
    await message.reply(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=f"@{message.from_user.username}" if message.from_user.username else None,
            mention=message.from_user.mention,
            id=user_id
        )
    )

@Bot.on_message(filters.private & filters.command("help"))
async def help_handler(client: Client, message: Message):
    await help_command(client, message)

@Bot.on_message(filters.private & filters.command("puser"))
async def puser_cmd(client: Client, message: Message):
    await puser_handler(client, message)

@Bot.on_message(filters.private & filters.command("removepremium"))
async def removepremium_cmd(client: Client, message: Message):
    await removepremium_handler(client, message)

@Bot.on_message(filters.private & filters.command("premiumlist"))
async def premiumlist_cmd(client: Client, message: Message):
    await premiumlist_handler(client, message)

@Bot.on_message(filters.private & filters.command("ban"))
async def ban_cmd(client: Client, message: Message):
    await ban_user_handler(client, message)

@Bot.on_message(filters.private & filters.command("unban"))
async def unban_cmd(client: Client, message: Message):
    await unban_user_handler(client, message)

@Bot.on_message(filters.private & filters.command("listban"))
async def listban_cmd(client: Client, message: Message):
    await listban_handler(client, message)

@Bot.on_message(filters.private & filters.command("total"))
async def total_cmd(client: Client, message: Message):
    await total_handler(client, message)


