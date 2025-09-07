
import motor.motor_asyncio
import time
from config import DB_URI, DB_NAME

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
        },
        'is_premium': False,
        'premium_added_time': 0,
        'file_clicks': 0
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
    """Get all user IDs from database (users who have started the bot)"""
    try:
        user_docs = user_data.find()
        user_ids = []
        async for doc in user_docs:
            if '_id' in doc:
                # Ensure we only add integer user IDs, not ObjectId
                user_id = doc['_id']
                if isinstance(user_id, int):
                    user_ids.append(user_id)
                elif hasattr(user_id, '__int__'):
                    try:
                        user_ids.append(int(user_id))
                    except (ValueError, TypeError):
                        print(f"Skipping invalid user ID: {user_id}")
                        continue
        return user_ids
    except Exception as e:
        print(f"Error getting userbase: {e}")
        return []

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})
    return

async def get_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link="", is_premium=None):
    current = await get_verify_status(user_id)
    current['verify_token'] = verify_token
    current['is_verified'] = is_verified
    current['verified_time'] = verified_time
    current['link'] = link
    
    update_data = {'verify_status': current}
    if is_premium is not None:
        update_data['is_premium'] = is_premium
        if is_premium:
            update_data['premium_added_time'] = time.time()
    
    await user_data.update_one({'_id': user_id}, {'$set': update_data})

async def is_premium_user(user_id):
    """Check if user is premium"""
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('is_premium', False)
    return False

async def increment_file_clicks(user_id):
    """Increment file click count for user"""
    await user_data.update_one(
        {'_id': user_id},
        {'$inc': {'file_clicks': 1}},
        upsert=True
    )

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

async def get_total_link_clicks(user_id):
    """Get total file clicks for a user"""
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('file_clicks', 0)
    return 0
