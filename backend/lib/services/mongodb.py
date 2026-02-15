from pymongo import MongoClient
from config import settings

# MongoDB client (singleton)
mongo_client = MongoClient(settings.mongodb_url)
mongo_db = mongo_client[settings.mongodb_database]

# Collections
email_content_collection = mongo_db.email_content
attachments_collection = mongo_db.attachments

def store_email_content(message_id: int, text_body: str = None, html_body: str = None, sanitised_html: str = None, raw_headers: str = None):
    """Store email content in MongoDB"""
    email_content_collection.update_one(
        {"message_id": message_id},
        {
            "$set": {
                "message_id": message_id,
                "text_body": text_body,
                "html_body": html_body,
                "sanitised_html": sanitised_html,
                "raw_headers": raw_headers
            }
        },
        upsert=True
    )

def get_email_content(message_id: int):
    """Retrieve email content from MongoDB"""
    return email_content_collection.find_one({"message_id": message_id})

def store_attachment(message_id: int, filename: str, content_type: str, data: bytes):
    """Store attachment in MongoDB"""
    return attachments_collection.insert_one({
        "message_id": message_id,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(data),
        "data": data
    })

def get_attachment(attachment_id: str):
    """Retrieve attachment from MongoDB"""
    from bson import ObjectId
    return attachments_collection.find_one({"_id": ObjectId(attachment_id)})

def get_attachments_for_message(message_id: int):
    """Get all attachments for a message"""
    return list(attachments_collection.find(
        {"message_id": message_id},
        {"data": 0}  # Exclude binary data from list
    ))

def delete_email_content(message_id: int):
    """Delete email content and attachments"""
    email_content_collection.delete_one({"message_id": message_id})
    attachments_collection.delete_many({"message_id": message_id})
