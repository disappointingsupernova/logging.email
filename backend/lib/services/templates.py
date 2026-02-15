from jinja2 import Template, TemplateError
from sqlalchemy.orm import Session
from models.models import EmailTemplate
import logging

logger = logging.getLogger(__name__)

DEFAULT_TEXT_TEMPLATE = """
{{ subject }}

{{ body }}

---
logging.email
"""

DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ subject }}</h1>
        </div>
        <div class="content">
            {{ body }}
        </div>
        <div class="footer">
            <p>logging.email - Email Logging Platform</p>
        </div>
    </div>
</body>
</html>
"""

def get_template(db: Session, email_type: str = None, template_id: int = None) -> EmailTemplate:
    """Get email template by type or ID, fallback to default"""
    
    if template_id:
        template = db.query(EmailTemplate).filter(
            EmailTemplate.id == template_id,
            EmailTemplate.is_active == True
        ).first()
        if template:
            return template
    
    if email_type:
        template = db.query(EmailTemplate).filter(
            EmailTemplate.email_type == email_type,
            EmailTemplate.is_active == True
        ).first()
        if template:
            return template
    
    # Get default template
    template = db.query(EmailTemplate).filter(
        EmailTemplate.email_type == None,
        EmailTemplate.is_active == True
    ).first()
    
    return template

def render_template(template_str: str, data: dict) -> str:
    """Render Jinja2 template with data"""
    try:
        template = Template(template_str)
        return template.render(**data)
    except TemplateError as e:
        logger.error(f"Template rendering error: {e}")
        return template_str

def render_email(db: Session, email_type: str, data: dict, template_id: int = None) -> dict:
    """Render email subject and body from template"""
    
    template = get_template(db, email_type, template_id)
    
    if not template:
        # Use hardcoded defaults if no template found
        subject = data.get('subject', 'Notification')
        body_text = render_template(DEFAULT_TEXT_TEMPLATE, data)
        body_html = render_template(DEFAULT_HTML_TEMPLATE, data)
    else:
        subject = render_template(template.subject_template, data)
        body_text = render_template(template.body_text_template, data) if template.body_text_template else None
        body_html = render_template(template.body_html_template, data) if template.body_html_template else None
    
    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html
    }

def create_default_templates(db: Session):
    """Create default email templates"""
    
    templates = [
        {
            "name": "default",
            "email_type": None,
            "subject_template": "{{ subject }}",
            "body_text_template": DEFAULT_TEXT_TEMPLATE,
            "body_html_template": DEFAULT_HTML_TEMPLATE
        },
        {
            "name": "notification",
            "email_type": "notification",
            "subject_template": "{{ subject }}",
            "body_text_template": "{{ message }}\n\n---\nlogging.email",
            "body_html_template": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>{{ subject }}</h2>
        <p>{{ message }}</p>
        <hr>
        <p style="color: #666; font-size: 12px;">logging.email</p>
    </div>
</body>
</html>
"""
        },
        {
            "name": "alert",
            "email_type": "alert",
            "subject_template": "🚨 Alert: {{ alert_type }}",
            "body_text_template": "ALERT: {{ alert_type }}\n\n{{ message }}\n\nTime: {{ timestamp }}",
            "body_html_template": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 2px solid #e74c3c;">
        <h2 style="color: #e74c3c;">🚨 Alert: {{ alert_type }}</h2>
        <p>{{ message }}</p>
        <p><strong>Time:</strong> {{ timestamp }}</p>
    </div>
</body>
</html>
"""
        }
    ]
    
    for tpl in templates:
        existing = db.query(EmailTemplate).filter(EmailTemplate.name == tpl["name"]).first()
        if not existing:
            db.add(EmailTemplate(**tpl))
    
    db.commit()
