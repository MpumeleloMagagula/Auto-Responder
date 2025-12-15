import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from database import engine, get_db, Base
from models import Ticket, EmailConfig, TicketStatus
from email_ingestor import fetch_and_process_emails, create_test_ticket
from mail_sender import send_approved_ticket_async, send_all_approved_tickets_async
from ai_processor import analyze_email

Base.metadata.create_all(bind=engine)

app = FastAPI(title="InfinityWork Support Desk")

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    
    stats = {
        "total": len(tickets),
        "pending": len([t for t in tickets if t.status == TicketStatus.PENDING_APPROVAL.value]),
        "approved": len([t for t in tickets if t.status == TicketStatus.APPROVED.value]),
        "sent": len([t for t in tickets if t.status == TicketStatus.SENT.value]),
        "rejected": len([t for t in tickets if t.status == TicketStatus.REJECTED.value]),
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "tickets": tickets,
        "stats": stats
    })


@app.get("/ticket/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(request: Request, ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return templates.TemplateResponse("ticket_detail.html", {
        "request": request,
        "ticket": ticket
    })


@app.post("/ticket/{ticket_id}/approve")
async def approve_ticket(
    ticket_id: str,
    response_text: str = Form(...),
    approved_by: str = Form(default="Admin"),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = TicketStatus.APPROVED.value
    ticket.approved_response = response_text
    ticket.approved_by = approved_by
    ticket.approved_at = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)


@app.post("/ticket/{ticket_id}/reject")
async def reject_ticket(
    ticket_id: str,
    rejection_reason: str = Form(default=""),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = TicketStatus.REJECTED.value
    ticket.rejected_reason = rejection_reason
    db.commit()
    
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)


@app.post("/ticket/{ticket_id}/send")
async def send_ticket_response(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status != TicketStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Ticket must be approved before sending")
    
    config = db.query(EmailConfig).filter(EmailConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Email configuration not found")
    
    result = await send_approved_ticket_async(db, ticket, config)
    
    if result.get("success"):
        return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    config = db.query(EmailConfig).filter(EmailConfig.is_active == True).first()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config
    })


@app.post("/settings/email")
async def save_email_settings(
    imap_server: str = Form(...),
    imap_port: int = Form(default=993),
    imap_username: str = Form(...),
    imap_password: str = Form(...),
    smtp_server: str = Form(...),
    smtp_port: int = Form(default=587),
    smtp_username: str = Form(...),
    smtp_password: str = Form(...),
    from_email: str = Form(...),
    from_name: str = Form(default="InfinityWork Support Team"),
    db: Session = Depends(get_db)
):
    existing = db.query(EmailConfig).filter(EmailConfig.is_active == True).first()
    
    if existing:
        existing.imap_server = imap_server
        existing.imap_port = imap_port
        existing.imap_username = imap_username
        existing.imap_password = imap_password
        existing.smtp_server = smtp_server
        existing.smtp_port = smtp_port
        existing.smtp_username = smtp_username
        existing.smtp_password = smtp_password
        existing.from_email = from_email
        existing.from_name = from_name
    else:
        config = EmailConfig(
            imap_server=imap_server,
            imap_port=imap_port,
            imap_username=imap_username,
            imap_password=imap_password,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            from_name=from_name
        )
        db.add(config)
    
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/fetch-emails")
async def fetch_emails(db: Session = Depends(get_db)):
    config = db.query(EmailConfig).filter(EmailConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Email configuration not found. Please configure email settings first.")
    
    result = fetch_and_process_emails(db, config)
    return result


@app.get("/test-ticket", response_class=HTMLResponse)
async def test_ticket_page(request: Request):
    return templates.TemplateResponse("test_ticket.html", {"request": request})


@app.post("/test-ticket")
async def create_test_ticket_endpoint(
    sender_email: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    db: Session = Depends(get_db)
):
    ticket = create_test_ticket(db, sender_email, subject, body)
    return RedirectResponse(url=f"/ticket/{ticket.ticket_id}", status_code=303)


@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return [t.to_dict() for t in tickets]


@app.get("/api/ticket/{ticket_id}")
async def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
