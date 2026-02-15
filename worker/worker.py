#!/usr/bin/env python3
"""
Email processing worker.
Consumes from RabbitMQ, safely parses emails, sanitises content, stores in MongoDB.
"""
import sys
sys.path.insert(0, '../backend')

from lib.services.queue import consume_messages
from lib.services.mongodb import store_email_content, store_attachment
from models import SessionLocal
from models.models import Message, Attachment
from lib.utils.cache import cache_delete
import email
from email import policy
from email.parser import BytesParser
import bleach
from config import settings

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code']
ALLOWED_ATTRS = {'a': ['href', 'title']}

def sanitise_html(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

def process_email(job: dict):
    message_id = job['message_id']
    email_data = job['email_data']
    
    try:
        msg = BytesParser(policy=policy.default).parsebytes(email_data.encode('utf-8'))
        subject = msg.get('subject', '')
        message_id_header = msg.get('message-id', '')
        raw_headers = str(msg)
        text_body = None
        html_body = None
        sanitised_html = None
        has_attachments = False
        
        db = SessionLocal()
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    if 'attachment' in content_disposition:
                        has_attachments = True
                        filename = part.get_filename() or 'unnamed'
                        content = part.get_payload(decode=True)
                        
                        if content:
                            # Store in MongoDB
                            mongo_result = store_attachment(message_id, filename, content_type, content)
                            
                            # Store metadata in MySQL
                            attachment = Attachment(
                                message_id=message_id,
                                mongodb_id=str(mongo_result.inserted_id),
                                filename=filename,
                                content_type=content_type,
                                size_bytes=len(content)
                            )
                            db.add(attachment)
                    
                    elif content_type == 'text/plain' and not text_body:
                        text_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    
                    elif content_type == 'text/html' and not html_body:
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
            else:
                content_type = msg.get_content_type()
                if content_type == 'text/plain':
                    text_body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                elif content_type == 'text/html':
                    html_body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            
            if html_body:
                sanitised_html = sanitise_html(html_body)
            
            # Store email content in MongoDB
            store_email_content(message_id, text_body, html_body, sanitised_html, raw_headers)
            
            # Update message metadata in MySQL
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.message_id = message_id_header
                message.subject = subject
                message.has_attachments = has_attachments
                message.is_processed = True
                db.commit()
                
                # Invalidate policy cache
                from models.models import EmailAddress
                email_address = db.query(EmailAddress).filter(
                    EmailAddress.id == message.email_address_id
                ).first()
                if email_address:
                    cache_delete(f"policy:{email_address.address}")
            
            print(f"Processed message {message_id}", file=sys.stderr)
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error processing message {message_id}: {e}", file=sys.stderr)
        db = SessionLocal()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.is_processed = True
                db.commit()
        finally:
            db.close()

def main():
    print("Worker started, waiting for jobs...", file=sys.stderr)
    consume_messages(process_email)

if __name__ == '__main__':
    main()
