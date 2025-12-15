import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from sqlalchemy.orm import Session

from models import Ticket, EmailConfig, TicketStatus


async def send_email_async(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    body: str
) -> dict:
    """Send an email using SMTP asynchronously."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Re: {subject}"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        html_body = body.replace('\n', '<br>')
        html_part = MIMEText(f"<html><body>{html_body}</body></html>", 'html', 'utf-8')
        msg.attach(html_part)
        
        await aiosmtplib.send(
            msg,
            hostname=smtp_server,
            port=smtp_port,
            username=username,
            password=password,
            start_tls=True
        )
        
        return {"success": True, "message": "Email sent successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_approved_ticket_async(db: Session, ticket: Ticket, config: EmailConfig) -> dict:
    """Send the approved response for a ticket asynchronously."""
    if ticket.status != TicketStatus.APPROVED.value:
        return {"success": False, "error": "Ticket is not approved"}
    
    if not ticket.approved_response:
        return {"success": False, "error": "No approved response found"}
    
    result = await send_email_async(
        smtp_server=config.smtp_server,
        smtp_port=config.smtp_port,
        username=config.smtp_username,
        password=config.smtp_password,
        from_email=config.from_email,
        from_name=config.from_name,
        to_email=ticket.sender_email,
        subject=ticket.email_subject,
        body=ticket.approved_response
    )
    
    if result.get("success"):
        ticket.status = TicketStatus.SENT.value
        ticket.sent_at = datetime.utcnow()
        db.commit()
    
    return result


async def send_all_approved_tickets_async(db: Session, config: EmailConfig) -> dict:
    """Send responses for all approved tickets asynchronously."""
    results = {
        "sent": 0,
        "failed": 0,
        "errors": []
    }
    
    approved_tickets = db.query(Ticket).filter(
        Ticket.status == TicketStatus.APPROVED.value
    ).all()
    
    for ticket in approved_tickets:
        result = await send_approved_ticket_async(db, ticket, config)
        if result.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
            results["errors"].append({
                "ticket_id": ticket.ticket_id,
                "error": result.get("error")
            })
    
    return results
