from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from lib.database import get_db
from models.models import EmailAddress, Message, ApiToken
from lib.utils.auth import verify_api_token
from lib.services.queue import publish_message
from config import settings

router = APIRouter()

def verify_worker_token(x_api_token: str = Header(...)):
    """Verify API token for worker/ingestion"""
    db = next(get_db())
    tokens = db.query(ApiToken).filter(
        ApiToken.scope.in_(['worker', 'admin']),
        ApiToken.is_active == True
    ).all()
    
    for token in tokens:
        if verify_api_token(x_api_token, token.token_hash):
            return True
    
    raise HTTPException(status_code=401, detail="Invalid API token")

class IngestRequest(BaseModel):
    recipient: str
    sender: str
    size: int

@router.post("/ingest")
async def ingest_email(
    request: IngestRequest,
    raw_email: UploadFile = File(...),
    _: bool = Depends(verify_worker_token)
):
    """
    Receive raw email from Postfix and enqueue for processing.
    Uses RabbitMQ for reliable message queuing.
    """
    recipient = request.recipient.lower().strip()
    
    try:
        email_data = await raw_email.read()
        
        db = next(get_db())
        email_address = db.query(EmailAddress).filter(
            EmailAddress.address == recipient,
            EmailAddress.is_active == True
        ).first()
        
        if not email_address:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        message = Message(
            email_address_id=email_address.id,
            from_address=request.sender,
            size_bytes=request.size,
            is_processed=False
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Track usage
        from lib.services.features import track_email_received
        size_mb = request.size / (1024 * 1024)
        track_email_received(db, email_address.organization_id, size_mb)
        
        publish_message({
            "message_id": message.id,
            "email_data": email_data.decode('utf-8', errors='replace')
        })
        
        return {"status": "queued", "message_id": message.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
