#(©)Codexbotz
#rymme
# https://www.youtube.com/@ultroidofficial


from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
import asyncio
from bot import Bot
from config import ADMINS
from helper_func import decode
from database.database import get_verify_status, update_verify_status, present_user, add_user, is_premium_user, increment_file_clicks, is_banned_user, ban_user, unban_user, get_banned_users


routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("ultroid_official")

@Bot.on_message(filters.private & filters.command("start"))
async def route(client: Client, message: Message):
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
        "/upload - Upload a file\n"
        "/list - List all your uploaded files\n"
        "/delete <file_id> - Delete a file by its ID\n"
        "/rename <file_id> <new_name> - Rename a file\n"
        "/premium - Show premium features\n"
        "/ban <user_id> - Bans a user from accessing the bot\n"
        "/unban <user_id> - Unbans a previously banned user\n"
        "/listban - Lists all banned users with their ban timestamps\n"
        "/premiumlist - Lists all premium users"
    )
    await message.reply_text(help_text)

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("ban"))
async def ban_command(client: Client, message: Message):
    user_id_to_ban = None
    try:
        user_id_to_ban = int(message.text.split()[1])
    except IndexError:
        return await message.reply("Please provide a user ID to ban.")
    except ValueError:
        return await message.reply("Invalid user ID. Please provide a valid integer.")

    await ban_user(user_id_to_ban)
    await message.reply(f"User {user_id_to_ban} has been banned successfully.")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("unban"))
async def unban_command(client: Client, message: Message):
    user_id_to_unban = None
    try:
        user_id_to_unban = int(message.text.split()[1])
    except IndexError:
        return await message.reply("Please provide a user ID to unban.")
    except ValueError:
        return await message.reply("Invalid user ID. Please provide a valid integer.")

    await unban_user(user_id_to_unban)
    await message.reply(f"User {user_id_to_unban} has been unbanned successfully.")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("listban"))
async def listban_command(client: Client, message: Message):
    banned_users = await get_banned_users()
    if not banned_users:
        return await message.reply("No users are currently banned.")

    ban_list_text = "Banned Users:\n\n"
    for user_id, ban_timestamp in banned_users:
        ban_list_text += f"- User ID: {user_id}, Banned at: {ban_timestamp}\n"

    await message.reply(ban_list_text)

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("premiumlist"))
async def premium_list_command(client: Client, message: Message):
    premium_users = await get_premium_users()  # Assuming you have a function get_premium_users()
    if not premium_users:
        return await message.reply("No users are currently premium.")

    premium_list_text = "Premium Users:\n\n"
    for user_id, premium_timestamp in premium_users:
        premium_list_text += f"- User ID: {user_id}, Premium since: {premium_timestamp}\n"

    await message.reply(premium_list_text)


async def channel_post_handler(client: Client, update):
    user_id = update.from_user.id

    # Check if user is banned
    if await is_banned_user(user_id):
        return

    if update.document:
        await increment_file_clicks(user_id, update.document.file_id)
    elif update.photo:
        await increment_file_clicks(user_id, update.photo.file_id)
    elif update.video:
        await increment_file_clicks(user_id, update.video.file_id)
    elif update.audio:
        await increment_file_clicks(user_id, update.audio.file_id)
    elif update.voice:
        await increment_file_clicks(user_id, update.voice.file_id)
    elif update.sticker:
        await increment_file_clicks(user_id, update.sticker.file_id)
    elif update.animation:
        await increment_file_clicks(user_id, update.animation.file_id)
    elif update.new_chat_members:
        pass
    elif update.left_chat_member:
        pass
    elif update.successful_payment:
        pass
    elif update.text:
        await message.reply_text("Please send a file directly.")

# Placeholder for get_premium_users function, replace with your actual implementation
async def get_premium_users():
    # This is a placeholder. You should have a database function to fetch premium users.
    # Example: return await database.get_all_premium_users()
    return []