
from bot import Bot
from pyrogram.types import Message
from pyrogram import filters
from config import ADMINS, BOT_STATS_TEXT, USER_REPLY_TEXT,ADMINS
from datetime import datetime
from helper_func import get_readable_time
from database.database import add_user, present_user, full_userbase

@Bot.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    now = datetime.now()
    delta = now - bot.uptime
    time = get_readable_time(delta.seconds)
    await message.reply(BOT_STATS_TEXT.format(uptime=time))

@Bot.on_message(filters.command('users') & filters.user(ADMINS))
async def users_stats(bot: Bot, message: Message):
    try:
        users = await full_userbase()
        total_users = len(users)
        await message.reply(f"📊 **Bot Statistics:**\n\n👥 Total Users: {total_users}")
    except Exception as e:
        await message.reply(f"❌ Error getting user statistics: {str(e)}")

@Bot.on_message(filters.command('verifystats') & filters.user(ADMINS))
async def verify_stats(bot: Bot, message: Message):
    """Show verification statistics"""
    try:
        from database.database import user_data
        from config import VERIFY_EXPIRE
        import time
        
        current_time = time.time()
        verified_users = []
        expired_users = []
        never_verified = []
        
        async for user in user_data.find():
            user_id = user.get('_id')
            verify_status = user.get('verify_status', {})
            
            if verify_status.get('is_verified'):
                verified_time = verify_status.get('verified_time', 0)
                if (current_time - verified_time) <= VERIFY_EXPIRE:
                    verified_users.append(user_id)
                else:
                    expired_users.append(user_id)
            else:
                never_verified.append(user_id)
        
        stats_msg = (
            f"🔐 **Verification Statistics:**\n\n"
            f"✅ **Currently Verified:** {len(verified_users)}\n"
            f"⏰ **Expired Verification:** {len(expired_users)}\n"
            f"❌ **Never Verified:** {len(never_verified)}\n\n"
            f"📊 **Total Users:** {len(verified_users) + len(expired_users) + len(never_verified)}"
        )
        
        await message.reply(stats_msg)
    except Exception as e:
        await message.reply(f"❌ Error getting verification statistics: {str(e)}")

@Bot.on_message(filters.command('recentverify') & filters.user(ADMINS))
async def recent_verifications(bot: Bot, message: Message):
    """Show recent verifications (last 24 hours)"""
    try:
        from database.database import user_data
        import time
        
        current_time = time.time()
        recent_threshold = current_time - 86400  # 24 hours ago
        recent_verifications = []
        
        async for user in user_data.find():
            user_id = user.get('_id')
            verify_status = user.get('verify_status', {})
            verified_time = verify_status.get('verified_time', 0)
            
            if verify_status.get('is_verified') and verified_time > recent_threshold:
                recent_verifications.append({
                    'user_id': user_id,
                    'verified_time': verified_time
                })
        
        # Sort by verification time (newest first)
        recent_verifications.sort(key=lambda x: x['verified_time'], reverse=True)
        
        if recent_verifications:
            msg = "🔔 **Recent Verifications (Last 24h):**\n\n"
            for i, verification in enumerate(recent_verifications[:10]):  # Show only top 10
                verify_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(verification['verified_time']))
                msg += f"{i+1}. User ID: `{verification['user_id']}`\n   ⏰ {verify_time_str}\n\n"
            
            if len(recent_verifications) > 10:
                msg += f"... and {len(recent_verifications) - 10} more"
        else:
            msg = "📭 No recent verifications in the last 24 hours."
            
        await message.reply(msg)
    except Exception as e:
        await message.reply(f"❌ Error getting recent verifications: {str(e)}")


@Bot.on_message(filters.private & filters.incoming)
async def useless(_,message: Message):
    id = message.from_user.id
    owner_id = ADMINS  # Fetch the owner's ID from config

    # Check if the user is the owner
    if id == owner_id:
        # Owner-specific actions
        # You can add any additional actions specific to the owner here
        await message.reply("You are the owner! Additional actions can be added here.")

    else:
        if not await present_user(id):
            try:
                await add_user(id)
            except:
                pass
    if USER_REPLY_TEXT:
        await message.reply(USER_REPLY_TEXT)
