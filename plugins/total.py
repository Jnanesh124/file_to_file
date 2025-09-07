import time
from pyrogram import Client, filters
from pyrogram.types import Message
from bot import Bot
from config import ADMINS
from database.database import user_data, present_user, add_user, update_verify_status, get_total_link_clicks

@Bot.on_message(filters.private & filters.command("total"))
async def total_handler(client: Client, message: Message):
    """Show total file clicks for the user"""
    user_id = message.from_user.id
    try:
        total_clicks = await get_total_link_clicks(user_id)
        await message.reply(f"📊 **Total file clicks:** {total_clicks}")
    except Exception as e:
        await message.reply(f"❌ An error occurred while fetching total clicks: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('puser'))
async def premium_user_command(client: Client, message: Message):
    """Make a user premium (bypass verification)"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/puser <user_id>`\n\n**Example:** `/puser 123456789`")
            return

        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return

        # Check if user exists in database, if not add them
        if not await present_user(user_id):
            await add_user(user_id)

        # Update user to premium status
        await update_verify_status(user_id, is_premium=True)

        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"

            success_msg = f"✅ **User made Premium successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Premium Status:** Active\n"
            success_msg += f"🚫 **Verification:** Bypassed"

        except Exception:
            success_msg = f"✅ **User made Premium successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Premium Status:** Active\n"
            success_msg += f"⚡ **Verification:** Bypassed"

        await message.reply(success_msg)

        # Notify the user about premium status
        try:
            notification_msg = (
                f"🎉 **Congratulations!**\n\n"
                f"✨ You have been granted **Premium Access**!\n\n"
                f"🚫 **No more verification needed**\n"
                f"⚡ **Direct file access**\n"
                f"👑 **Premium benefits activated**\n\n"
                f"Enjoy your premium experience!"
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ User made premium but couldn't notify them: {str(e)}")

    except Exception as e:
        await message.reply(f"❌ Error making user premium: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('removepremium'))
async def remove_premium_command(client: Client, message: Message):
    """Remove premium status from a user"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/removepremium <user_id>`\n\n**Example:** `/removepremium 123456789`")
            return

        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return

        # Check if user exists in database
        if not await present_user(user_id):
            await message.reply("❌ **User not found** in database.")
            return

        # Update user to remove premium status
        await update_verify_status(user_id, is_premium=False)

        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"

            success_msg = f"❌ **Premium status removed successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Premium Status:** Removed\n"
            success_msg += f"🔒 **Verification:** Required"

        except Exception:
            success_msg = f"❌ **Premium status removed successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Premium Status:** Removed\n"
            success_msg += f"⚡ **Verification:** Required"

        await message.reply(success_msg)

        # Notify the user about premium removal
        try:
            notification_msg = (
                f"⚠️ **Premium Access Removed**\n\n"
                f"❌ Your premium access has been removed.\n\n"
                f"🔒 **Verification is now required** to access files\n"
                f"📋 Use `/start` to verify again\n\n"
                f"Contact support if you think this is a mistake."
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ Premium removed but couldn't notify user: {str(e)}")

    except Exception as e:
        await message.reply(f"❌ Error removing premium status: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('premiumlist'))
async def premium_list_command(client: Client, message: Message):
    """Show list of all premium users"""
    try:
        premium_users = []

        # Find all premium users
        async for user in user_data.find({'is_premium': True}):
            user_id = int(user['_id'])  # Convert to int directly
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

        stats_msg = "=" * 50 + "\n"
        stats_msg += "👑 PREMIUM USERS LIST\n"
        stats_msg += "=" * 50 + "\n"
        stats_msg += f"📊 Total Premium Users: {len(premium_users)}\n\n"

        # Show premium users (max 20)
        for i, user_data_item in enumerate(premium_users[:20], 1):
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

                stats_msg += f"  {i}. 👤 {first_name} ({username})\n"
                stats_msg += f"     🆔 ID: {user_id}\n"
                stats_msg += f"     ⏰ Added: {added_str}\n\n"
            except:
                # If can't get user info, show basic details
                stats_msg += f"  {i}. 🆔 User ID: {user_id}\n"
                stats_msg += f"     ⏰ Added: {added_str}\n\n"

        if len(premium_users) > 20:
            stats_msg += f"  ... and {len(premium_users) - 20} more premium users\n"

        stats_msg += "=" * 50

        await message.reply(f"```\n{stats_msg}\n```")

    except Exception as e:
        await message.reply(f"❌ Error fetching premium users: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('ban'))
async def ban_user_command(client: Client, message: Message):
    """Ban a user from accessing the bot"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/ban <user_id>`\n\n**Example:** `/ban 123456789`")
            return

        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return

        # Check if user exists in database, if not add them
        if not await present_user(user_id):
            await add_user(user_id)

        # Ban the user
        from database.database import ban_user
        await ban_user(user_id)

        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"

            success_msg = f"🚫 **User banned successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Status:** Banned from bot access"

        except Exception:
            success_msg = f"🚫 **User banned successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"⚡ **Status:** Banned from bot access"

        await message.reply(success_msg)

        # Notify the user about the ban
        try:
            notification_msg = (
                f"🚫 **You have been banned**\n\n"
                f"❌ You are no longer allowed to use this bot.\n\n"
                f"📞 Contact support if you think this is a mistake."
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ User banned but couldn't notify them: {str(e)}")

    except Exception as e:
        await message.reply(f"❌ Error banning user: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('unban'))
async def unban_user_command(client: Client, message: Message):
    """Unban a user"""
    try:
        # Check if user provided a user ID
        if len(message.text.split()) < 2:
            await message.reply("❌ **Usage:** `/unban <user_id>`\n\n**Example:** `/unban 123456789`")
            return

        try:
            user_id = int(message.text.split()[1])
        except ValueError:
            await message.reply("❌ **Invalid user ID.** Please provide a valid numeric user ID.")
            return

        # Check if user exists in database
        if not await present_user(user_id):
            await message.reply("❌ **User not found** in database.")
            return

        # Unban the user
        from database.database import unban_user
        await unban_user(user_id)

        # Try to get user info for better display
        try:
            user_info = await client.get_users(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
            first_name = user_info.first_name or "Unknown"

            success_msg = f"✅ **User unbanned successfully!**\n\n"
            success_msg += f"👤 **Name:** {first_name}\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"👑 **Username:** {username}\n"
            success_msg += f"⚡ **Status:** Can access bot again"

        except Exception:
            success_msg = f"✅ **User unbanned successfully!**\n\n"
            success_msg += f"🆔 **User ID:** {user_id}\n"
            success_msg += f"⚡ **Status:** Can access bot again"

        await message.reply(success_msg)

        # Notify the user about the unban
        try:
            notification_msg = (
                f"✅ **You have been unbanned**\n\n"
                f"🎉 You can now use this bot again.\n\n"
                f"Use /start to begin using the bot."
            )
            await client.send_message(user_id, notification_msg)
        except Exception as e:
            await message.reply(f"✅ User unbanned but couldn't notify them: {str(e)}")

    except Exception as e:
        await message.reply(f"❌ Error unbanning user: {str(e)}")

@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('listban'))
async def list_banned_command(client: Client, message: Message):
    """Show list of all banned users"""
    try:
        from database.database import get_banned_users
        banned_users = await get_banned_users()

        if not banned_users:
            await message.reply("📭 **No banned users found.**")
            return

        # Sort by banned time (newest first)
        banned_users.sort(key=lambda x: x['banned_time'], reverse=True)

        stats_msg = "=" * 50 + "\n"
        stats_msg += "🚫 BANNED USERS LIST\n"
        stats_msg += "=" * 50 + "\n"
        stats_msg += f"📊 Total Banned Users: {len(banned_users)}\n\n"

        # Show banned users (max 20)
        for i, user_data_item in enumerate(banned_users[:20], 1):
            user_id = user_data_item['user_id']
            banned_time = user_data_item['banned_time']

            # Format banned time
            if banned_time:
                banned_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(banned_time))
            else:
                banned_str = "Unknown"

            try:
                # Try to get user info
                user_info = await client.get_users(user_id)
                username = f"@{user_info.username}" if user_info.username else "No username"
                first_name = user_info.first_name or "Unknown"

                stats_msg += f"  {i}. 👤 {first_name} ({username})\n"
                stats_msg += f"     🆔 ID: {user_id}\n"
                stats_msg += f"     ⏰ Banned: {banned_str}\n\n"
            except:
                # If can't get user info, show basic details
                stats_msg += f"  {i}. 🆔 User ID: {user_id}\n"
                stats_msg += f"     ⏰ Banned: {banned_str}\n\n"

        if len(banned_users) > 20:
            stats_msg += f"  ... and {len(banned_users) - 20} more banned users\n"

        stats_msg += "=" * 50

        await message.reply(f"```\n{stats_msg}\n```")

    except Exception as e:
        await message.reply(f"❌ Error fetching banned users: {str(e)}")
