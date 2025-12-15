import email
import uuid
from datetime import datetime
from email.header import decode_header
from imapclient import IMAPClient
from sqlalchemy.orm import Session

from models import Ticket, EmailConfig, TicketStatus
from ai_processor import analyze_email


def decode_email_header(header_value):
    """Decode email header to string."""
    if header_value is None:
        return ""
    
    decoded_parts = []
    for part, charset in decode_header(header_value):
        if isinstance(part, bytes):
            charset = charset or 'utf-8'
            try:
                decoded_parts.append(part.decode(charset))
            except (UnicodeDecodeError, LookupError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    return ' '.join(decoded_parts)


def get_email_body(msg):
    """Extract plain text body from email message."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = payload.decode(charset)
                    except (UnicodeDecodeError, LookupError):
                        body = payload.decode('utf-8', errors='replace')
                break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            try:
                body = payload.decode(charset)
            except (UnicodeDecodeError, LookupError):
                body = payload.decode('utf-8', errors='replace')
    
    return body.strip()


def generate_ticket_id():
    """Generate a unique ticket ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    unique_part = str(uuid.uuid4())[:8].upper()
    return f"TKT-{timestamp}-{unique_part}"


def fetch_and_process_emails(db: Session, config: EmailConfig) -> dict:
    """Fetch unread emails from IMAP and create tickets."""
    results = {
        "processed": 0,
        "errors": [],
        "tickets_created": []
    }
    
    try:
        with IMAPClient(config.imap_server, port=config.imap_port, ssl=True) as client:
            client.login(config.imap_username, config.imap_password)
            client.select_folder('INBOX')
            
            messages = client.search(['UNSEEN'])
            
            for uid in messages:
                try:
                    raw_message = client.fetch([uid], ['RFC822'])
                    email_data = raw_message[uid][b'RFC822']
                    msg = email.message_from_bytes(email_data)
                    
                    from_header = msg.get('From', '')
                    sender_email = email.utils.parseaddr(from_header)[1]
                    sender_name = decode_email_header(email.utils.parseaddr(from_header)[0])
                    subject = decode_email_header(msg.get('Subject', 'No Subject'))
                    body = get_email_body(msg)
                    
                    date_header = msg.get('Date', '')
                    try:
                        received_at = email.utils.parsedate_to_datetime(date_header)
                    except Exception:
                        received_at = datetime.utcnow()
                    
                    ticket_id = generate_ticket_id()
                    
                    ticket = Ticket(
                        ticket_id=ticket_id,
                        sender_email=sender_email,
                        sender_name=sender_name,
                        email_subject=subject,
                        email_body=body,
                        received_at=received_at,
                        status=TicketStatus.NEW.value
                    )
                    
                    db.add(ticket)
                    db.commit()
                    db.refresh(ticket)
                    
                    ai_result = analyze_email(
                        ticket_id=ticket_id,
                        sender_email=sender_email,
                        subject=subject,
                        body=body,
                        received_at=received_at.isoformat()
                    )
                    
                    ticket.category = ai_result.get("category")
                    ticket.urgency = ai_result.get("urgency")
                    ticket.summary = ai_result.get("summary")
                    ticket.fix_steps = ai_result.get("fix_steps")
                    ticket.ai_response = ai_result.get("response")
                    ticket.confidence = ai_result.get("confidence")
                    ticket.escalation_required = ai_result.get("escalation_required", False)
                    ticket.status = TicketStatus.PENDING_APPROVAL.value
                    
                    db.commit()
                    
                    results["processed"] += 1
                    results["tickets_created"].append(ticket_id)
                    
                    client.add_flags([uid], ['\\Seen'])
                    
                except Exception as e:
                    results["errors"].append(f"Error processing message {uid}: {str(e)}")
                    continue
                    
    except Exception as e:
        results["errors"].append(f"IMAP connection error: {str(e)}")
    
    return results


def create_test_ticket(db: Session, sender_email: str, subject: str, body: str) -> Ticket:
    """Create a test ticket manually for testing purposes."""
    ticket_id = generate_ticket_id()
    received_at = datetime.utcnow()
    
    ticket = Ticket(
        ticket_id=ticket_id,
        sender_email=sender_email,
        sender_name="Test User",
        email_subject=subject,
        email_body=body,
        received_at=received_at,
        status=TicketStatus.NEW.value
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    ai_result = analyze_email(
        ticket_id=ticket_id,
        sender_email=sender_email,
        subject=subject,
        body=body,
        received_at=received_at.isoformat()
    )
    
    ticket.category = ai_result.get("category")
    ticket.urgency = ai_result.get("urgency")
    ticket.summary = ai_result.get("summary")
    ticket.fix_steps = ai_result.get("fix_steps")
    ticket.ai_response = ai_result.get("response")
    ticket.confidence = ai_result.get("confidence")
    ticket.escalation_required = ai_result.get("escalation_required", False)
    ticket.status = TicketStatus.PENDING_APPROVAL.value
    
    db.commit()
    db.refresh(ticket)
    
    return ticket
