
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid, UserDeactivated
from bot import Bot
from config import ADMINS
from database.database import full_userbase

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('broadcast'))
async def broadcast_handler(client: Client, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        
        for chat_id in query:
            try:
                # Ensure chat_id is an integer
                if not isinstance(chat_id, int):
                    try:
                        chat_id = int(chat_id)
                    except (ValueError, TypeError):
                        print(f"Skipping invalid chat_id: {chat_id}")
                        unsuccessful += 1
                        total += 1
                        continue
                
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                blocked += 1
            except PeerIdInvalid:
                unsuccessful += 1
            except UserDeactivated:
                deleted += 1
            except Exception as e:
                unsuccessful += 1
                print(f"Error broadcasting to {chat_id}: {e}")
            
            total += 1
            
            # Update progress every 50 users
            if total % 50 == 0:
                try:
                    await pls_wait.edit(
                        f"<i>Broadcasting Message.. \n\n"
                        f"Total Users: {len(query)}\n"
                        f"Processed: {total}\n"
                        f"Successful: {successful}\n"
                        f"Blocked: {blocked}\n"
                        f"Deleted: {deleted}\n"
                        f"Unsuccessful: {unsuccessful}</i>"
                    )
                except:
                    pass
            
            # Small delay to avoid flood
            await asyncio.sleep(0.1)
        
        await pls_wait.edit(
            f"<b>Broadcast Completed!</b>\n\n"
            f"Total Users: {len(query)}\n"
            f"Successful: {successful}\n"
            f"Blocked Users: {blocked}\n"
            f"Deleted Accounts: {deleted}\n"
            f"Unsuccessful: {unsuccessful}"
        )
    else:
        msg = await message.reply("Please reply to a message to broadcast it to all users.")
        await asyncio.sleep(8)
        await msg.delete()
