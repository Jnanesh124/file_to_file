import asyncio
import random
import string
import time
import base64
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait, ChannelBanned, ChannelPrivate, ChatAdminRequired, PeerIdInvalid
from config import *
from database.database import add_user, present_user, full_userbase, get_verify_status, update_verify_status, user_data, ban_user, unban_user, is_banned_user, get_banned_users, increment_file_clicks, get_total_link_clicks, get_file_token, save_file_token

# ================== ENCODING/DECODING FUNCTIONS ================== #
async def encode(string):
    """Encode string to base64"""
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("ascii")

async def decode(base64_string):
    """Decode base64 string"""
    base64_bytes = base64_string.encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("ascii")

async def get_shortlink(url, api, link):
    """Get shortlink from URL shortener"""
    try:
        async with aiohttp.ClientSession() as session:
            # Build proper shortlink URL - don't include https:// in url parameter
            shortlink_url = f"https://{url}/api"
            params = {'api': api, 'url': link}
            async with session.get(shortlink_url, params=params, timeout=15) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        shortened = data.get('shortenedUrl') or data.get('shorturl') or data.get('short_url')
                        return shortened if shortened else link
                    except:
                        # If JSON parsing fails, try text response
                        text = await response.text()
                        return text if text and text.startswith('http') else link
                else:
                    print(f"Shortlink API returned status {response.status}")
                    return link
    except Exception as e:
        print(f"Shortlink error: {e}")
        return link

def get_exp_time(seconds):
    """Convert seconds to readable time format"""
    periods = [('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value > 0:
                result.append(f"{period_value} {period_name}{'s' if period_value > 1 else ''}")
    return ', '.join(result) if result else '0 seconds'

def get_readable_time(seconds):
    """Convert seconds to readable time format"""
    return get_exp_time(seconds)

async def get_file_ids_from_token(token):
    """Get file IDs from secure token"""
    file_ids = await get_file_token(token)
    return file_ids

async def is_subscribed(filter, client, update):
    """Check if user is subscribed to force sub channels"""
    if not FORCE_SUB_CHANNELS:
        return True
    
    user_id = update.from_user.id
    
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            error_msg = str(e)
            # Only return False if user is not a participant
            # Skip check if channel issue (deleted, bot removed, etc.)
            if "USER_NOT_PARTICIPANT" in error_msg:
                print(f"User {user_id} not subscribed to channel {channel_id}")
                return False
            else:
                print(f"Skipping channel {channel_id} check due to error: {e}")
                # Continue checking other channels instead of failing
                continue
    
    return True

async def get_non_joined_channels(client, user_id):
    """Get list of channels user hasn't joined"""
    non_joined = []
    
    for index, channel_id in enumerate(FORCE_SUB_CHANNELS):
        try:
            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                non_joined.append((index, channel_id))
        except Exception as e:
            error_msg = str(e)
            # Only add to non_joined if it's a USER_NOT_PARTICIPANT error
            # Skip if channel is deleted, banned, or bot was removed
            if "USER_NOT_PARTICIPANT" in error_msg:
                non_joined.append((index, channel_id))
                print(f"User {user_id} not in channel {channel_id}")
            else:
                print(f"Skipping channel {channel_id} due to error: {e}")
    
    return non_joined

async def get_verification_stats():
    """Get verification statistics"""
    current_time = time.time()
    verified_users = []
    
    async for user in user_data.find({'verify_status.is_verified': True}):
        user_id = int(user['_id'])
        verify_status = user.get('verify_status', {})
        verified_time = verify_status.get('verified_time', 0)
        
        if verified_time:
            time_elapsed = current_time - verified_time
            if time_elapsed < VERIFY_EXPIRE:
                remaining_time = VERIFY_EXPIRE - time_elapsed
                verified_users.append({
                    'user_id': user_id,
                    'verified_time': verified_time,
                    'remaining_time': remaining_time
                })
    
    # Get users verified in last 24 hours
    verified_in_24h = [u for u in verified_users if (current_time - u['verified_time']) < 86400]
    
    return {
        'total_verified': len(verified_users),
        'verified_in_24h': sorted(verified_in_24h, key=lambda x: x['verified_time'], reverse=True)
    }

async def get_message_id(client, message):
    """Extract message ID from forwarded message or link"""
    if message.forward_from_chat:
        # If it's a forwarded message from channel
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
    elif message.text:
        # Try to extract from link
        pattern = r"https://t\.me/(?:c/)?(\d+)/(\d+)"
        import re
        match = re.search(pattern, message.text)
        if match:
            channel_id = int(match.group(1))
            msg_id = int(match.group(2))
            # Check if it matches the DB channel
            if channel_id == abs(client.db_channel.id) or f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
    return None

async def create_file_link(client, message_ids):
    """Create a secure file link with token"""
    # Generate a unique token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # Save token with message IDs to database
    await save_file_token(token, message_ids)
    
    # Create the link
    bot_username = (await client.get_me()).username
    link = f"https://t.me/{bot_username}?start=file_{token}"
    
    return link, token

# Helper functions without Bot decorators
async def start_handler_impl(client: Client, message: Message):
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

# ================== START HANDLER IMPLEMENTATION ================== #
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
        
        # Add "Try Again" button
        buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")])

        # Only send markup if there are buttons
        if buttons:
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
        else:
            return await checking_msg.edit_text(
                text=FORCE_MSG.format(
                    first=query.from_user.first_name,
                    last=query.from_user.last_name,
                    username=f"@{query.from_user.username}" if query.from_user.username else None,
                    mention=query.from_user.mention,
                    id=user_id
                ),
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
async def premiumlist_handler(client: Client, message: Message):
    if message.chat.id not in ADMINS:
        return await message.reply("You are not authorized to use this command.")

    try:
        from database.database import user_data
        import time

        premium_users = []

        # Find all premium users from database
        async for user in user_data.find({'is_premium': True}):
            user_id = int(user['_id'])
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

        # Format the list of premium users
        premium_list_text = "👑 **Premium Users List:**\n\n"
        premium_list_text += f"📊 Total Premium Users: {len(premium_users)}\n\n"

        for i, user_data_item in enumerate(premium_users[:20], 1):  # Show max 20
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

                premium_list_text += f"  {i}. 👤 {first_name} ({username})\n"
                premium_list_text += f"     🆔 ID: `{user_id}`\n"
                premium_list_text += f"     ⏰ Added: {added_str}\n\n"
            except:
                # If can't get user info, show basic details
                premium_list_text += f"  {i}. 🆔 User ID: `{user_id}`\n"
                premium_list_text += f"     ⏰ Added: {added_str}\n\n"

        if len(premium_users) > 20:
            premium_list_text += f"  ... and {len(premium_users) - 20} more premium users\n"

        await message.reply(premium_list_text)

    except Exception as e:
        await message.reply(f"An error occurred while fetching premium users: {e}")

# Ban a user
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


