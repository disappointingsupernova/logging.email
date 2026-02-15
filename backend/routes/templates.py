from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from lib.utils.auth_helpers import get_current_admin
from lib.database import get_db
from lib.services.audit import log_audit
from models.models import User, EmailTemplate
from sqlalchemy import desc

router = APIRouter()

class TemplateCreate(BaseModel):
    name: str
    email_type: str = None
    subject_template: str
    body_text_template: str = None
    body_html_template: str = None

class TemplateUpdate(BaseModel):
    subject_template: str = None
    body_text_template: str = None
    body_html_template: str = None
    is_active: bool = None

@router.get("/admin/templates")
def list_templates(admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """List all email templates"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    templates = db.query(EmailTemplate).order_by(desc(EmailTemplate.created_at)).all()
    
    log_audit(
        user_id=admin.id,
        action="admin_list_templates",
        resource_type="email_template",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"templates": [{
        "id": t.id,
        "name": t.name,
        "email_type": t.email_type,
        "subject_template": t.subject_template,
        "is_active": t.is_active,
        "created_at": t.created_at
    } for t in templates]}

@router.get("/admin/templates/{template_id}")
def get_template(template_id: int, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Get template details"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    log_audit(
        user_id=admin.id,
        action="admin_view_template",
        resource_type="email_template",
        resource_id=str(template_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "id": template.id,
        "name": template.name,
        "email_type": template.email_type,
        "subject_template": template.subject_template,
        "body_text_template": template.body_text_template,
        "body_html_template": template.body_html_template,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }

@router.post("/admin/templates")
def create_template(data: TemplateCreate, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Create email template"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    existing = db.query(EmailTemplate).filter(EmailTemplate.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")
    
    template = EmailTemplate(
        name=data.name,
        email_type=data.email_type,
        subject_template=data.subject_template,
        body_text_template=data.body_text_template,
        body_html_template=data.body_html_template
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    log_audit(
        user_id=admin.id,
        action="admin_create_template",
        resource_type="email_template",
        resource_id=str(template.id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"name": data.name, "email_type": data.email_type}
    )
    
    return {"id": template.id, "name": template.name}

@router.patch("/admin/templates/{template_id}")
def update_template(template_id: int, data: TemplateUpdate, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Update email template"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if data.subject_template is not None:
        template.subject_template = data.subject_template
    if data.body_text_template is not None:
        template.body_text_template = data.body_text_template
    if data.body_html_template is not None:
        template.body_html_template = data.body_html_template
    if data.is_active is not None:
        template.is_active = data.is_active
    
    db.commit()
    
    log_audit(
        user_id=admin.id,
        action="admin_update_template",
        resource_type="email_template",
        resource_id=str(template_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"status": "updated"}

@router.delete("/admin/templates/{template_id}")
def delete_template(template_id: int, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Delete email template"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    log_audit(
        user_id=admin.id,
        action="admin_delete_template",
        resource_type="email_template",
        resource_id=str(template_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"name": template.name}
    )
    
    return {"status": "deleted"}
