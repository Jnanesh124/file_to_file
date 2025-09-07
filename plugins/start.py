import asyncio
import random
import string
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot import Bot
from config import *
from database.database import add_user, present_user, full_userbase, get_verify_status, update_verify_status, user_data, ban_user, unban_user, is_banned_user, get_banned_users, increment_file_clicks, get_total_link_clicks # Added necessary imports
from helper_func import is_subscribed, get_non_joined_channels, get_shortlink, decode, get_messages, get_exp_time

@Bot.on_message(filters.private & filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id

    # Check if user is banned
    if await is_banned_user(user_id):
        return await message.reply(
            "🚫 **You are banned from using this bot.**\n\n"
            "Contact support if you think this is a mistake."
        )

    if len(message.text.split()) <= 1:
        if not await present_user(user_id):
            await add_user(user_id)
            await message.reply_text(
                "Hello there! 👋\n\n"
                "I am your personal file storing bot. "
                "Send me any file, and I will store it for you.\n\n"
                "You can also manage your files and settings using the commands below.\n\n"
                "Use /help to see all available commands.",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("❓ Help", callback_data="help")
                    ]]
                )
            )
        else:
            await message.reply_text(
                "Hello again! 👋\n\n"
                "Welcome back! Use /help to see all available commands.",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("❓ Help", callback_data="help")
                    ]]
                )
            )
    else:
        # Handle the case where the start command includes arguments (e.g., referral links)
        # You might want to implement referral logic here
        pass

@Bot.on_message(filters.private & filters.command("help"))
async def help_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Check if user is banned
    if await is_banned_user(user_id):
        return await message.reply(
            "🚫 **You are banned from using this bot.**\n\n"
            "Contact support if you think this is a mistake."
        )

    help_text = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/total - Show your total file clicks\n"
        "/puser <user_id> - Make user premium (Admin only)\n"
        "/removepremium <user_id> - Remove premium status (Admin only)\n"
        "/premiumlist - List all premium users (Admin only)\n"
        "/ban <user_id> - Ban a user from accessing the bot (Admin only)\n"
        "/unban <user_id> - Unban a previously banned user (Admin only)\n"
        "/listban - List all banned users (Admin only)"
    )
    await message.reply_text(help_text)

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
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Check if user is banned
    from database.database import is_banned_user
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

                # Send to all admins
                for admin_id in ADMINS:
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
        # Handle offline time properly - check actual time elapsed since verification
        current_time = time.time()
        is_expired = False

        if verify_status['is_verified'] and verify_status['verified_time']:
            # Calculate actual time elapsed since verification (handles bot offline time)
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
                                # Increment file click count for each file
                                await increment_file_clicks(user_id)
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
                                # Increment file click count
                                await increment_file_clicks(user_id)
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

# ================== PREMIUM USER COMMANDS ================== #

# Add premium user
@Bot.on_message(filters.private & filters.command("puser"))
async def puser_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        _, user_id_str = message.text.split(" ", 1)
        user_id = int(user_id_str)

        # Update the user's status to premium in the database
        await update_verify_status(user_id, is_premium=True)
        await message.reply(f"User `{user_id}` has been successfully made a premium user.")

        # Optionally, notify the user they are now premium
        try:
            await client.send_message(
                user_id,
                "🎉 Congratulations! You have been granted premium access. You no longer need to verify."
            )
        except Exception as e:
            print(f"Failed to notify user {user_id} about premium status: {e}")

    except ValueError:
        await message.reply("Invalid user ID format. Please use `/puser <user_id>`.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# Remove premium user
@Bot.on_message(filters.private & filters.command("removepremium"))
async def removepremium_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        _, user_id_str = message.text.split(" ", 1)
        user_id = int(user_id_str)

        # Update the user's status to not premium in the database
        await update_verify_status(user_id, is_premium=False)
        await message.reply(f"User `{user_id}` has been successfully removed from premium users.")

        # Optionally, notify the user
        try:
            await client.send_message(
                user_id,
                "Your premium access has been revoked. You will now need to verify your account."
            )
        except Exception as e:
            print(f"Failed to notify user {user_id} about premium status removal: {e}")

    except ValueError:
        await message.reply("Invalid user ID format. Please use `/removepremium <user_id>`.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# List all premium users
@Bot.on_message(filters.private & filters.command("premiumlist"))
async def premiumlist_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        # Fetch all users and filter for premium ones
        all_users = await full_userbase() # Assuming full_userbase returns all user documents
        premium_users = [user['_id'] for user in all_users if user.get('is_premium', False)]

        if not premium_users:
            await message.reply("No premium users found.")
            return

        # Format the list of premium users
        premium_list_text = "✅ **Premium Users:**\n\n"
        for user_id in premium_users:
            premium_list_text += f"- `{user_id}`\n"

        # Telegram messages have a limit, so we might need to chunk this if there are many users.
        # For now, assuming it fits within a single message.
        await message.reply(premium_list_text)

    except Exception as e:
        await message.reply(f"An error occurred while fetching premium users: {e}")

# Ban a user
@Bot.on_message(filters.private & filters.command("ban"))
async def ban_user_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        _, user_id_str = message.text.split(" ", 1)
        user_id = int(user_id_str)

        await ban_user(user_id)
        await message.reply(f"User `{user_id}` has been successfully banned.")

        # Optionally, notify the user they are banned
        try:
            await client.send_message(
                user_id,
                "🚫 You have been banned from using this bot. Contact support if you believe this is an error."
            )
        except Exception as e:
            print(f"Failed to notify user {user_id} about ban: {e}")

    except ValueError:
        await message.reply("Invalid user ID format. Please use `/ban <user_id>`.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# Unban a user
@Bot.on_message(filters.private & filters.command("unban"))
async def unban_user_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        _, user_id_str = message.text.split(" ", 1)
        user_id = int(user_id_str)

        await unban_user(user_id)
        await message.reply(f"User `{user_id}` has been successfully unbanned.")

        # Optionally, notify the user they are unbanned
        try:
            await client.send_message(
                user_id,
                "✅ You have been unbanned. You can now use the bot again."
            )
        except Exception as e:
            print(f"Failed to notify user {user_id} about unban: {e}")

    except ValueError:
        await message.reply("Invalid user ID format. Please use `/unban <user_id>`.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

# List all banned users
@Bot.on_message(filters.private & filters.command("listban"))
async def listban_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        banned_users = await get_banned_users()

        if not banned_users:
            await message.reply("No users are currently banned.")
            return

        banned_list_text = "🚫 **Banned Users:**\n\n"
        for user_id in banned_users:
            banned_list_text += f"- `{user_id}`\n"

        await message.reply(banned_list_text)

    except Exception as e:
        await message.reply(f"An error occurred while fetching banned users: {e}")


# ================== TOTAL CLICKS COMMAND ================== #
@Bot.on_message(filters.private & filters.command("total"))
async def total_handler(client: Client, message: Message):
    user_id = message.from_user.id
    # Logic to count total clicks on stored links for the user
    # This will require a new function in database.py to fetch this count.
    # For now, let's assume such a function exists and returns a count.
    # Example:
    # total_clicks = await get_total_link_clicks(user_id)
    # await message.reply(f"Total clicks on your stored links: {total_clicks}")

    # Get total clicks for the user
    try:
        total_clicks = await get_total_link_clicks(user_id)
        await message.reply(f"Total clicks on your stored links: {total_clicks}")
    except ImportError:
        await message.reply("Sorry, the link click tracking feature is not fully implemented yet.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching total clicks: {e}")