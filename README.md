# ⚡ AutoFlow — AI Workflow Automation Agents

4 intelligent agents powered by **Gemini 2.5 Flash** with a Flask web interface.

## Agents Included
| Agent | What it Does |
|-------|-------------|
| ✉️ **Email Reply Bot** | Reads incoming emails → generates polished replies with tone control |
| 🎙️ **Meeting Summary Bot** | Transcripts → summaries, action items, decisions, next agenda |
| ✅ **Task Manager Agent** | Natural language → create/prioritize/complete tasks |
| 📅 **Calendar Assistant** | Natural language → schedule, reschedule, view events |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your Gemini API key
- Go to https://aistudio.google.com/app/apikey
- Create a free API key (Gemini 2.5 Flash is free-tier eligible)

### 3. Set your API key
```bash
# Option A: Environment variable (recommended)
export GEMINI_API_KEY="your_key_here"

# Option B: Edit app.py line 13
GEMINI_API_KEY = "your_key_here"
```

### 4. Run the app
```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Optional: Real Email Sending (SMTP)
To actually send emails, POST to `/api/send-email`:
```json
{
  "to": "recipient@example.com",
  "subject": "Re: Your email",
  "body": "The generated reply...",
  "smtp": {
    "from_email": "you@gmail.com",
    "password": "your_app_password",
    "host": "smtp.gmail.com",
    "port": 587
  }
}
```
For Gmail, use an **App Password** (not your main password).

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/email-agent` | Generate email reply |
| POST | `/api/meeting-agent` | Summarize meeting |
| POST | `/api/task-agent` | Manage tasks |
| POST | `/api/calendar-agent` | Schedule events |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/send-email` | Send real email via SMTP |

## Project Structure
```
workflow_agents/
├── app.py              # Flask app + all 4 agents
├── requirements.txt    # Dependencies
├── README.md
└── templates/
    └── index.html      # Full UI dashboard
```
