from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from bot import Bot
from helper_func import (
    start_handler_impl,
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
    total_handler
)

@Bot.on_message(filters.private & filters.command("start"))
async def start_handler(client: Client, message: Message):
    await start_handler_impl(client, message)

@Bot.on_message(filters.private & filters.command("help"))
async def help_handler(client: Client, message: Message):
    await help_command(client, message)

@Bot.on_callback_query(filters.regex("check_sub"))
async def check_sub_callback(client: Client, query: CallbackQuery):
    await recheck_subscription(client, query)

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