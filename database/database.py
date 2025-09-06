import motor.motor_asyncio
from config import DB_URI, DB_NAME
import asyncio

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

user_data = database['users']

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }

async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)
    return

async def db_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def db_update_verify_status(user_id, verify):
    await user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] async for doc in user_docs]
    return user_ids

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})
    return

# File storage functions
files_data = database['files']

async def save_file(file_id, caption=None):
    """Save file to database and return the message ID"""
    file_doc = {
        'file_id': file_id,
        'caption': caption
    }
    result = await files_data.insert_one(file_doc)
    return str(result.inserted_id)

async def get_file(message_id):
    """Get file from database using message ID"""
    try:
        # Try to find by ObjectId first
        from bson import ObjectId
        if ObjectId.is_valid(message_id):
            file_doc = await files_data.find_one({'_id': ObjectId(message_id)})
            if file_doc:
                return file_doc
    except:
        pass

    # If not found by ObjectId, try as string
    file_doc = await files_data.find_one({'_id': message_id})
    return file_doc

# Broadcast functions
async def get_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def get_all_users():
    """Get all users from database"""
    users = []
    async for user in user_data.find({}):
        users.append(user)
    return users

async def delete_user(user_id):
    """Delete user from database"""
    await user_data.delete_one({'_id': user_id})

async def send_broadcast(message, bot):
    """Send broadcast message to all users who have started the bot"""
    users = await get_all_users()
    for user in users:
        user_id = user['_id']
        if await present_user(user_id):  # Check if user has started the bot
            try:
                await bot.send_message(user_id, message)
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")