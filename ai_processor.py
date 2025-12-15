import os
import json
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user

MASTER_PROMPT = """# AI SUPPORT DESK AUTO-RESPONDER

## ROLE & IDENTITY
You are an **AI Support Desk Auto-Responder** for **InfinityWork IT Solutions (Pty) Ltd**.

You act as:
- A senior technical support engineer
- A professional customer service agent
- A business-aware automation assistant

You NEVER send messages directly to customers.
All responses require **explicit human approval**.

---

## PRIMARY OBJECTIVE
Your job is to:
1. Analyze incoming support messages
2. Understand intent and context
3. Classify the issue
4. Prepare safe troubleshooting steps
5. Draft a professional response
6. Mark the response as **PENDING approval**

You do NOT:
- Auto-send replies
- Guess missing information
- Promise outcomes
- Act without approval

---

## EXECUTION STEPS

### STEP 1 — ISSUE UNDERSTANDING
Identify the core problem and user intent.

### STEP 2 — CLASSIFICATION
Choose ONE:
- Billing
- Technical
- Login / Access
- Feature Request
- General Inquiry
- Other

### STEP 3 — URGENCY
- Low
- Medium
- High

### STEP 4 — SUMMARY
Write a clear 1–2 sentence summary.

### STEP 5 — TROUBLESHOOTING
Provide 3–5 **safe**, realistic steps.
Number each step.
Never request credentials or sensitive data.

If information is missing, request clarification.

### STEP 6 — DRAFT RESPONSE
Write a formal email draft.

Opening:
"Good day,"

Closing:
"InfinityWork Support Team"

---

## OUTPUT FORMAT (STRICT)
Return ONLY valid JSON with these exact fields:

{
  "category": "Billing | Technical | Login / Access | Feature Request | General Inquiry | Other",
  "urgency": "Low | Medium | High",
  "summary": "1–2 sentence issue summary",
  "fix_steps": "1. Step one...\\n2. Step two...\\n3. Step three...",
  "response": "Good day,\\n\\n<Professional response body>\\n\\nInfinityWork Support Team",
  "confidence": "Low | Medium | High",
  "escalation_required": false,
  "approval_status": "PENDING"
}

---

## SECURITY RULES
You must NEVER:
- Request passwords, OTPs, tokens
- Claim system access
- Disable security controls
- Fabricate policies or actions

---

## FINAL RULES
- JSON only
- No markdown in output
- No auto-sending
- Always assume human review
"""


def analyze_email(ticket_id: str, sender_email: str, subject: str, body: str, received_at: str) -> dict:
    """Analyze an email using OpenAI and return structured response."""
    
    if not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key not configured",
            "category": "Other",
            "urgency": "Medium",
            "summary": "Unable to analyze - API key missing",
            "fix_steps": "1. Configure OpenAI API key\n2. Retry analysis",
            "response": "Good day,\n\nThank you for contacting InfinityWork Support. We are currently experiencing technical difficulties with our automated system. A support agent will review your message shortly.\n\nInfinityWork Support Team",
            "confidence": "Low",
            "escalation_required": True,
            "approval_status": "PENDING"
        }
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    user_message = f"""Please analyze this support email and provide a structured response.

TICKET ID: {ticket_id}
SENDER EMAIL: {sender_email}
TIMESTAMP: {received_at}
SUBJECT: {subject}

EMAIL BODY:
{body}

Analyze this email and respond with the required JSON format."""

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": MASTER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=2048,
        )
        
        result = json.loads(response.choices[0].message.content)
        
        required_fields = ["category", "urgency", "summary", "fix_steps", "response", "confidence", "escalation_required", "approval_status"]
        for field in required_fields:
            if field not in result:
                if field == "escalation_required":
                    result[field] = False
                elif field == "approval_status":
                    result[field] = "PENDING"
                else:
                    result[field] = "Unknown"
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse AI response: {str(e)}",
            "category": "Other",
            "urgency": "Medium",
            "summary": "AI analysis failed - manual review required",
            "fix_steps": "1. Review email manually\n2. Classify the issue\n3. Draft appropriate response",
            "response": "Good day,\n\nThank you for contacting InfinityWork Support. Your message has been received and will be reviewed by our support team shortly.\n\nInfinityWork Support Team",
            "confidence": "Low",
            "escalation_required": True,
            "approval_status": "PENDING"
        }
    except Exception as e:
        return {
            "error": f"AI processing error: {str(e)}",
            "category": "Other",
            "urgency": "Medium",
            "summary": f"Error during analysis: {str(e)}",
            "fix_steps": "1. Check OpenAI API status\n2. Verify API key\n3. Retry analysis",
            "response": "Good day,\n\nThank you for contacting InfinityWork Support. Your message has been received and will be reviewed by our support team shortly.\n\nInfinityWork Support Team",
            "confidence": "Low",
            "escalation_required": True,
            "approval_status": "PENDING"
        }
