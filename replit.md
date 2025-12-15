# InfinityWork Support Desk - AI Email Auto-Responder

## Overview
This is an AI-powered customer support email automation system for InfinityWork IT Solutions. The system fetches customer emails via IMAP, analyzes them using OpenAI, generates professional responses, and requires human approval before sending replies via SMTP.

## Architecture
```
┌────────────┐
│ IMAP Inbox │  ← Customer emails
└─────┬──────┘
      │
      ▼
┌────────────────────┐
│ Email Ingestor     │  (Python service)
│ - Fetch unread     │
│ - Normalize input  │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Ticket Store       │  (PostgreSQL)
│ - Ticket ID        │
│ - Raw email        │
│ - Status           │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ AI Processor       │  (OpenAI GPT-5)
│ - Uses MASTER PROMPT
│ - Produces JSON    │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Approval Service   │  (FastAPI Web UI)
│ - Human review     │
│ - Approve / Reject │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Mail Sender        │  (SMTP)
│ - Sends ONLY if    │
│   approved         │
└────────────────────┘
```

## Project Structure
```
/
├── main.py              # FastAPI application entry point
├── database.py          # SQLAlchemy database configuration
├── models.py            # Database models (Ticket, EmailConfig)
├── ai_processor.py      # OpenAI integration with MASTER PROMPT
├── email_ingestor.py    # IMAP email fetching service
├── mail_sender.py       # SMTP email sending service
├── templates/           # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── ticket_detail.html
│   ├── settings.html
│   └── test_ticket.html
├── static/              # Static assets
└── attached_assets/     # Reference files (MASTER PROMPT)
```

## Key Features
1. **Email Ingestion**: Fetches unread emails from configured IMAP server
2. **AI Analysis**: Uses OpenAI to classify issues, assess urgency, and generate responses
3. **Human Approval**: Web dashboard for reviewing and approving AI-generated responses
4. **Response Sending**: Sends approved responses via SMTP only after explicit approval
5. **Ticket Tracking**: Full ticket lifecycle management (new → analyzed → pending → approved/rejected → sent)

## Database Schema
- **tickets**: Stores all support tickets with email content, AI analysis, approval status
- **email_config**: Stores IMAP/SMTP configuration

## Ticket Statuses
- `new`: Just created, not yet analyzed
- `analyzed`: AI has processed the ticket
- `pending_approval`: Awaiting human approval
- `approved`: Approved for sending
- `rejected`: Response was rejected
- `sent`: Response has been sent to customer

## Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)
- `OPENAI_API_KEY`: OpenAI API key for AI processing
- `SESSION_SECRET`: Session encryption key

## Running the Application
```bash
python main.py
```
The application runs on port 5000.

## Usage
1. Go to **Settings** to configure IMAP/SMTP email servers
2. Click **Fetch New Emails** to import unread emails
3. Or use **Test Ticket** to create manual test tickets
4. Review tickets in the dashboard
5. **Approve** or **Reject** AI-generated responses
6. **Send** approved responses to customers

## AI Processing
The AI uses a strict MASTER PROMPT that:
- Classifies issues (Billing, Technical, Login/Access, Feature Request, General Inquiry, Other)
- Assesses urgency (Low, Medium, High)
- Generates safe troubleshooting steps
- Drafts professional responses
- Marks escalation requirements
- Returns structured JSON output

## Security
- Responses are NEVER auto-sent
- Human approval is mandatory
- AI never requests passwords or sensitive data
- Email passwords are stored in database (consider encrypting in production)
