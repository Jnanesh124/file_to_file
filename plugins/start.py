import asyncio
import random
import string
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot import Bot
from config import *
from database.database import present_user, add_user, get_verify_status, update_verify_status
from helper_func import is_subscribed, get_non_joined_channels, get_shortlink, decode, get_messages, get_exp_time

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
    user_id = message.from_user.id

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

        await checking_msg.delete()
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
        if not verify_status['is_verified'] or (current_time - verify_status['verified_time']) > VERIFY_EXPIRE:
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
                [InlineKeyboardButton("How to use the bot", url=TUT_VID)]
            ]

            return await message.reply(
                f"⚠️ You need to verify before using the bot.\n"
                f"Your token has expired or is missing.\nClick below to refresh your token.\n\n"
                f"⏳ Token Timeout: {get_exp_time(VERIFY_EXPIRE)}",
                reply_markup=InlineKeyboardMarkup(btn)
            )

    # ====== HANDLE FILE REQUESTS ====== #
    if len(message.text) > 7:
        file_id = message.text.split(" ", 1)[1]

        if not file_id.startswith("verify_"):
            try:
                decoded = await decode(file_id)

                # Batch files: get-start-end
                if decoded.startswith("get-"):
                    parts = decoded.split("-")
                    if len(parts) == 3:
                        _, start_id, end_id = parts
                        start_msg_id = abs(int(start_id)) // abs(client.db_channel.id)
                        end_msg_id = abs(int(end_id)) // abs(client.db_channel.id)

                        msg_ids = list(range(start_msg_id, end_msg_id + 1))
                        messages = await get_messages(client, msg_ids)

                        for msg in messages:
                            if msg:
                                sent_msg = await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)
                                if AUTO_DELETE:
                                    from plugins.auto_delete import schedule_auto_delete
                                    asyncio.create_task(schedule_auto_delete(client, sent_msg, file_id))
                                await asyncio.sleep(0.5)
                        return

                    elif len(parts) == 2:  # Single file: get-msg_id
                        _, msg_id = parts
                        msg_id = abs(int(msg_id)) // abs(client.db_channel.id)
                        try:
                            msg = await client.get_messages(client.db_channel.id, msg_id)
                            if msg:
                                sent_msg = await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)
                                if AUTO_DELETE:
                                    from plugins.auto_delete import schedule_auto_delete
                                    asyncio.create_task(schedule_auto_delete(client, sent_msg, file_id))
                                return
                        except Exception:
                            pass

                return await message.reply("❌ File not found or may have been deleted.")

            except Exception:
                return await message.reply("❌ Invalid file link or file not found.")

    # ====== NORMAL START MESSAGE ====== #
    await message.reply(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=f"@{message.from_user.username}" if message.from_user.username else None,
            mention=message.from_user.mention,
            id=user_id
        )
    )

# ================== CALLBACK HANDLER FOR TRY AGAIN ================== #
@Bot.on_callback_query(filters.regex("check_sub"))
async def recheck_subscription(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await query.answer("🔄 Checking membership status...")

    checking_msg = await query.message.edit_text("🔄 **Re-checking your membership...**\nPlease wait...")
    await asyncio.sleep(1)

    if not await is_user_subscribed(client, query):
        non_joined_channels = await get_user_non_joined_channels(client, query)
        buttons = []

        if hasattr(client, 'invitelinks') and client.invitelinks and non_joined_channels:
            for index, channel_id in non_joined_channels:
                if index < len(client.invitelinks):
                    buttons.append([InlineKeyboardButton(f"Join Channel {index+1}", url=client.invitelinks[index])])

        return await checking_msg.edit_text(
            text=FORCE_MSG.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name,
                username=f"@{query.from_user.username}" if query.from_user.username else None,
                mention=query.from_user.mention,
                id=user_id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    # Auto-run start after successful subscription check
    await checking_msg.delete()
    # Simulate /start again for auto start
    class MsgWrapper:
        from_user = query.from_user
        text = "/start"
    await start_handler(client, MsgWrapper())