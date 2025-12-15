from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class TicketStatus(str, enum.Enum):
    NEW = "new"
    ANALYZED = "analyzed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"

class TicketCategory(str, enum.Enum):
    BILLING = "Billing"
    TECHNICAL = "Technical"
    LOGIN_ACCESS = "Login / Access"
    FEATURE_REQUEST = "Feature Request"
    GENERAL_INQUIRY = "General Inquiry"
    OTHER = "Other"

class TicketUrgency(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)
    
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=True)
    email_subject = Column(String(500), nullable=False)
    email_body = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False)
    
    status = Column(String(50), default=TicketStatus.NEW.value, nullable=False)
    
    category = Column(String(50), nullable=True)
    urgency = Column(String(20), nullable=True)
    summary = Column(Text, nullable=True)
    fix_steps = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=True)
    escalation_required = Column(Boolean, default=False)
    
    approved_response = Column(Text, nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "email_subject": self.email_subject,
            "email_body": self.email_body,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "status": self.status,
            "category": self.category,
            "urgency": self.urgency,
            "summary": self.summary,
            "fix_steps": self.fix_steps,
            "ai_response": self.ai_response,
            "confidence": self.confidence,
            "escalation_required": self.escalation_required,
            "approved_response": self.approved_response,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_reason": self.rejected_reason,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class EmailConfig(Base):
    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True, index=True)
    imap_server = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993)
    imap_username = Column(String(255), nullable=False)
    imap_password = Column(String(255), nullable=False)
    smtp_server = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String(255), nullable=False)
    smtp_password = Column(String(255), nullable=False)
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), default="InfinityWork Support Team")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SchedulerConfig(Base):
    __tablename__ = "scheduler_config"

    id = Column(Integer, primary_key=True, index=True)
    auto_fetch_enabled = Column(Boolean, default=False)
    fetch_interval_minutes = Column(Integer, default=5)
    last_fetch_at = Column(DateTime(timezone=True), nullable=True)
    last_fetch_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
