#(©)Codexbotz
#rymme
# https://www.youtube.com/@ultroidofficial


from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
import asyncio
from config import ADMINS
from helper_func import decode
from database.database import get_verify_status, update_verify_status, present_user, add_user, is_premium_user, increment_file_clicks, is_banned_user, ban_user, unban_user, get_banned_users


routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("ultroid_official")

# Bot handlers moved to start.py to avoid circular import


# Channel post handler and other functions moved to appropriate files