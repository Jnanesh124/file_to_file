# https://www.youtube.com/channel/UC7tAa4hho37iNv731_6RIOg
from pymongo import MongoClient
import asyncio
import base64
import logging
import os
import random
import re
import string
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from datetime import datetime, timedelta
from bot import Bot
from config import *
from helper_func import subscribed, encode, decode, get_messages, get_shortlink, get_verify_status, update_verify_status, get_exp_time, get_non_joined_channels
from database.database import add_user, del_user, full_userbase, present_user
from shortzy import Shortzy

client = MongoClient(DB_URI)  # Replace with your MongoDB URI
db = client[DB_NAME]  # Database name
phdlust = db["phdlust"]  # Collection for users
phdlust_tasks = db["phdlust_tasks"] 

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to add a delete task to the database
async def add_delete_task(chat_id, message_id, delete_at):
    phdlust_tasks.insert_one({
        "chat_id": chat_id,
        "message_id": message_id,
        "delete_at": delete_at
    })

# Function to delete the notification after a set delay
async def delete_notification(client, chat_id, notification_id, delay):
    await asyncio.sleep(delay)
    try:
        # Delete the notification message
        await client.delete_messages(chat_id=chat_id, message_ids=notification_id)
    except Exception as e:
        print(f"Error deleting notification {notification_id} in chat {chat_id}: {e}")
        
async def schedule_auto_delete(client, chat_id, message_id, delay):
    delete_at = datetime.now() + timedelta(seconds=int(delay))
    await add_delete_task(chat_id, message_id, delete_at)
    
    # Run deletion in the background to prevent blocking
    async def delete_message():
        await asyncio.sleep(int(delay))
        try:
            # Delete the original message
            await client.delete_messages(chat_id=chat_id, message_ids=message_id)
            phdlust_tasks.delete_one({"chat_id": chat_id, "message_id": message_id})  # Remove from DB
            
            # Send a notification about the deletion
            notification_text = DELETE_INFORM
            notification_msg = await client.send_message(chat_id, notification_text)
            
            # Schedule deletion of the notification after 60 seconds
            asyncio.create_task(delete_notification(client, chat_id, notification_msg.id, 40))
        
        except Exception as e:
            print(f"Error deleting message {message_id} in chat {chat_id}: {e}")

    asyncio.create_task(delete_message())  


async def delete_notification_after_delay(client, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        # Delete the notification message
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as e:
        print(f"Error deleting notification {message_id} in chat {chat_id}: {e}")


@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    UBAN = BAN  # Fetch the owner's ID from config
    
    # Schedule the initial message for deletion after 10 minutes
    #await schedule_auto_delete(client, message.chat.id, message.id, delay=600)

    # Check if the user is the owner
    if id == UBAN:
        sent_message = await message.reply("You are the U-BAN! Additional actions can be added here.")

    else:
        if not await present_user(id):
            try:
                await add_user(id)
            except:
                pass

        verify_status = await get_verify_status(id)
        if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
            await update_verify_status(id, is_verified=False)

        if "verify_" in message.text and IS_VERIFY:
            # Send token verification checking message
            token_checking_msg = await message.reply("🔄 **Verifying your token...**\n\nPlease wait while I validate your verification token.")
            
            # Wait for 2 seconds to simulate token checking
            await asyncio.sleep(2)
            
            _, token = message.text.split("_", 1)
            
            # Get fresh verify status
            verify_status = await get_verify_status(id)
            
            if verify_status['verify_token'] != token:
                await token_checking_msg.delete()
                return await message.reply("Your token is invalid or Expired. Try again by clicking /start")
            
            await update_verify_status(id, is_verified=True, verified_time=time.time())
            
            # Delete the checking message
            await token_checking_msg.delete()
            
            reply_markup = None
            await message.reply(f"Your token successfully verified and valid for: 24 Hour", reply_markup=reply_markup, protect_content=False, quote=True)

        elif len(message.text) > 7 and (not IS_VERIFY or verify_status['is_verified']):
            try:
                base64_string = message.text.split(" ", 1)[1]
            except:
                return
            _string = await decode(base64_string)
            argument = _string.split("-")
            if len(argument) == 3:
                try:
                    start = int(int(argument[1]) / abs(client.db_channel.id))
                    end = int(int(argument[2]) / abs(client.db_channel.id))
                except:
                    return
                if start <= end:
                    ids = range(start, end+1)
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
            temp_msg = await message.reply("Please wait...")
            try:
                messages = await get_messages(client, ids)
            except:
                await message.reply_text("Something went wrong..!")
                return
            await temp_msg.delete()
            
            phdlusts = []
            messages = await get_messages(client, ids)
            for msg in messages:
                if bool(CUSTOM_CAPTION) & bool(msg.document):
                    caption = CUSTOM_CAPTION.format(previouscaption = "" if not msg.caption else msg.caption.html, filename = msg.document.file_name)
                else:
                    caption = "" if not msg.caption else msg.caption.html

                if DISABLE_CHANNEL_BUTTON:
                    reply_markup = msg.reply_markup
                else:
                    reply_markup = None
                
                try:
                    messages = await get_messages(client, ids)
                    phdlust = await msg.copy(chat_id=message.from_user.id, caption=caption, reply_markup=reply_markup , protect_content=PROTECT_CONTENT)
                    phdlusts.append(phdlust)
                    if AUTO_DELETE == True:
                        #await message.reply_text(f"The message will be automatically deleted in {delete_after} seconds.")
                        asyncio.create_task(schedule_auto_delete(client, phdlust.chat.id, phdlust.id, delay=DELETE_AFTER))
                    await asyncio.sleep(0.2)      
                    #asyncio.sleep(0.2)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    phdlust = await msg.copy(chat_id=message.from_user.id, caption=caption, reply_markup=reply_markup , protect_content=PROTECT_CONTENT)
                    phdlusts.append(phdlust)     

            # Notify user to get file again if messages are auto-deleted
            if GET_AGAIN == True:
                get_file_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("GET FILE AGAIN", url=f"https://t.me/{client.username}?start={message.text.split()[1]}")]
                ])
                await message.reply(GET_INFORM, reply_markup=get_file_markup)

            if AUTO_DELETE == True:
                delete_notification = await message.reply(NOTIFICATION)
                asyncio.create_task(delete_notification_after_delay(client, delete_notification.chat.id, delete_notification.id, delay=NOTIFICATION_TIME))
                
        elif not IS_VERIFY or verify_status['is_verified']:
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("About Me", callback_data="about"),
                  InlineKeyboardButton("Close", callback_data="close")]]
            )
            await message.reply_text(
                text=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                quote=True
            )

        else:
            if IS_VERIFY:
                verify_status = await get_verify_status(id)
                if not verify_status['is_verified']:
                    short_url = f"adrinolinks.in"
                    # TUT_VID = f"https://t.me/ultroid_official/18"
                    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    await update_verify_status(id, verify_token=token, link="")
                    link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API,f'https://telegram.dog/{client.username}?start=verify_{token}')
                    btn = [
                        [InlineKeyboardButton("Click here", url=link)],
                        [InlineKeyboardButton('How to use the bot', url=TUT_VID)]
                    ]
                    await message.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 Hour after passing the ad.", reply_markup=InlineKeyboardMarkup(btn), protect_content=False, quote=True)
                    return
            
            # If verification is disabled or user is verified, show start message
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("About Me", callback_data="about"),
                  InlineKeyboardButton("Close", callback_data="close")]]
            )
            await message.reply_text(
                text=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                quote=True
            )


        
#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##

    
    
@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    # Send checking membership message
    checking_msg = await message.reply("🔄 **Checking your membership status...**\n\nPlease wait while I verify your subscription to all required channels.")
    
    # Wait for 3 seconds to simulate checking
    await asyncio.sleep(3)
    
    # Get non-joined channels only
    non_joined_channels = await get_non_joined_channels(client, message.from_user.id)
    
    buttons = []
    
    # Add buttons only for non-joined channels
    if hasattr(client, 'invitelinks') and client.invitelinks and non_joined_channels:
        for channel_index, channel_id in non_joined_channels:
            if channel_index < len(client.invitelinks):
                buttons.append([InlineKeyboardButton(f"Join Channel {channel_index+1}", url=client.invitelinks[channel_index])])
    
    try:
        buttons.append(
            [
                InlineKeyboardButton(
                    text = 'Try Again',
                    url = f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ]
        )
    except IndexError:
        pass

    # Delete the checking message
    await checking_msg.delete()
    
    await message.reply(
        text = FORCE_MSG.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
        reply_markup = InlineKeyboardMarkup(buttons),
        quote = True,
        disable_web_page_preview = True
    )

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total_users = len(query)
        current_user = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply(f"<i>🔄 Starting broadcast...</i>\n\n<b>Total Users:</b> <code>{total_users}</code>\n<b>Progress:</b> <code>0/{total_users}</code>")
        
        for chat_id in query:
            current_user += 1
            
            # Update live status every 10 users or on last user
            if current_user % 10 == 0 or current_user == total_users:
                remaining = total_users - current_user
                try:
                    await pls_wait.edit(f"""<b>🔄 Broadcasting in progress...</b>

<b>📊 Live Statistics:</b>
• <b>Total Users:</b> <code>{total_users}</code>
• <b>Completed:</b> <code>{current_user}/{total_users}</code>
• <b>Remaining:</b> <code>{remaining}</code>

<b>📈 Results so far:</b>
• <b>✅ Successful:</b> <code>{successful}</code>
• <b>🚫 Blocked:</b> <code>{blocked}</code>
• <b>❌ Deleted:</b> <code>{deleted}</code>
• <b>⚠️ Failed:</b> <code>{unsuccessful}</code>

<b>Progress:</b> <code>{((current_user/total_users)*100):.1f}%</code>""")
                except:
                    pass  # Continue even if edit fails
            
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                try:
                    await broadcast_msg.copy(chat_id)
                    successful += 1
                except Exception:
                    unsuccessful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception as error:
                unsuccessful += 1
                print(f"Broadcast failed for {chat_id}: {str(error)}")
        
        # Final status report
        status = f"""<b>✅ Broadcast Completed!</b>

<b>📊 Final Results:</b>
• <b>Total Users:</b> <code>{total_users}</code>
• <b>✅ Successful:</b> <code>{successful}</code>
• <b>🚫 Blocked Users:</b> <code>{blocked}</code>
• <b>❌ Deleted Accounts:</b> <code>{deleted}</code>
• <b>⚠️ Failed Attempts:</b> <code>{unsuccessful}</code>

<b>📈 Success Rate:</b> <code>{((successful/total_users)*100):.1f}%</code>

<b>🗑️ Cleanup:</b>
• <code>{blocked + deleted}</code> inactive users removed from database

<b>⚠️ Failed Reasons:</b>
• User blocked bot: <code>{blocked}</code>
• Account deleted: <code>{deleted}</code>
• Other errors: <code>{unsuccessful}</code>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
