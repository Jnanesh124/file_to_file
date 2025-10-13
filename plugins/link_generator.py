from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import ADMINS
from helper_func import encode, get_message_id

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('batch'))
async def batch(client: Client, message: Message):
    while True:
        try:
            first_message = await client.ask(text = "Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link\n\nor Send the First Message ID", chat_id = message.from_user.id, filters=(filters.forwarded | filters.text), timeout=60)
        except:
            return
        
        # Try to get message ID from forwarded message or link
        f_msg_id = await get_message_id(client, first_message)
        
        # If not found, try to parse as direct message ID
        if not f_msg_id and first_message.text:
            try:
                f_msg_id = int(first_message.text.strip())
                # Verify the message exists in DB channel
                try:
                    await client.get_messages(chat_id=client.db_channel.id, message_ids=f_msg_id)
                except:
                    f_msg_id = None
            except ValueError:
                f_msg_id = None
        
        if f_msg_id:
            break
        else:
            await first_message.reply("❌ Error\n\nPlease send:\n- Forwarded message from DB Channel\n- DB Channel post link\n- Or valid message ID", quote = True)
            continue

    while True:
        try:
            second_message = await client.ask(text = "Forward the Last Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link\n\nor Send the Last Message ID", chat_id = message.from_user.id, filters=(filters.forwarded | filters.text), timeout=60)
        except:
            return
        
        # Try to get message ID from forwarded message or link
        s_msg_id = await get_message_id(client, second_message)
        
        # If not found, try to parse as direct message ID
        if not s_msg_id and second_message.text:
            try:
                s_msg_id = int(second_message.text.strip())
                # Verify the message exists in DB channel
                try:
                    await client.get_messages(chat_id=client.db_channel.id, message_ids=s_msg_id)
                except:
                    s_msg_id = None
            except ValueError:
                s_msg_id = None
        
        if s_msg_id:
            break
        else:
            await second_message.reply("❌ Error\n\nPlease send:\n- Forwarded message from DB Channel\n- DB Channel post link\n- Or valid message ID", quote = True)
            continue


    # Create secure link with token
    from helper_func import create_file_link
    message_ids = [f_msg_id, s_msg_id]
    link, token = await create_file_link(client, message_ids)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<strong>🥵 DIRECT VIDEO 📂 👇\n\n{link}\n\n⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪\nHOW TO OPEN LINK 👇 TUTORIAL\nhttps://t.me/HOWTOOPENLINKFAST\n\nBuy vip for 🔞 direct Video  @Myhero2k\n\nBACKUP CHANNEL https://t.me/+JfPMTmCv95hjMGNl\n⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪</strong>", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    while True:
        try:
            channel_message = await client.ask(text = "Forward Message from the DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link\n\nor Send the Message ID", chat_id = message.from_user.id, filters=(filters.forwarded | filters.text), timeout=60)
        except:
            return
        
        # Try to get message ID from forwarded message or link
        msg_id = await get_message_id(client, channel_message)
        
        # If not found, try to parse as direct message ID
        if not msg_id and channel_message.text:
            try:
                msg_id = int(channel_message.text.strip())
                # Verify the message exists in DB channel
                try:
                    await client.get_messages(chat_id=client.db_channel.id, message_ids=msg_id)
                except:
                    msg_id = None
            except ValueError:
                msg_id = None
        
        if msg_id:
            break
        else:
            await channel_message.reply("❌ Error\n\nPlease send:\n- Forwarded message from DB Channel\n- DB Channel post link\n- Or valid message ID", quote = True)
            continue

    # Create secure link with token
    from helper_func import create_file_link
    link, token = await create_file_link(client, msg_id)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<strong>🥵 DIRECT VIDEO 📂 👇\n\n{link}\n\n⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪\nHOW TO OPEN LINK 👇 TUTORIAL\nhttps://t.me/HOWTOOPENLINKFAST\n\nBuy vip for 🔞 direct Video  @Myhero2k\n\nBACKUP CHANNEL https://t.me/+JfPMTmCv95hjMGNl\n⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪</strong>", quote=True, reply_markup=reply_markup)