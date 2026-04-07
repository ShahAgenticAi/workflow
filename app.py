from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import threading
import time
import json
import os
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Gemini Setup ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key="AIzaSyCwvBa0j-tvLcuXyUyfPnN2SI7IxWiCNsg")
model = genai.GenerativeModel("gemini-2.5-flash")

# ── In-memory store (replace with DB in production) ─────────────────────────
tasks_store = []
meetings_store = []
scheduled_jobs = []
email_history = []
calendar_events = []

# ══════════════════════════════════════════════════════════════════════════════
#  AGENT 1 — Email Reply Bot
# ══════════════════════════════════════════════════════════════════════════════
def email_reply_agent(email_content: str, tone: str = "professional", context: str = "") -> dict:
    prompt = f"""You are an intelligent email reply assistant.

Original Email:
{email_content}

Tone: {tone}
Additional Context: {context if context else 'None'}

Generate a complete, polished email reply. Return as JSON:
{{
  "subject": "Re: <original subject>",
  "body": "<full email body>",
  "key_points": ["point1", "point2"],
  "suggested_followup": "<optional follow-up action>"
}}
Only return valid JSON, no markdown fences."""

    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
    except:
        result = {
            "subject": "Re: Your Email",
            "body": response.text,
            "key_points": ["Review the generated reply"],
            "suggested_followup": "Send after review"
        }
    email_history.append({
        "id": len(email_history) + 1,
        "original": email_content[:100] + "...",
        "reply": result.get("body", "")[:100] + "...",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tone": tone
    })
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT 2 — Meeting Summary Bot
# ══════════════════════════════════════════════════════════════════════════════
def meeting_summary_agent(transcript: str, meeting_title: str = "Meeting") -> dict:
    prompt = f"""You are an expert meeting notes assistant.

Meeting Title: {meeting_title}
Transcript/Notes:
{transcript}

Analyze and return as JSON:
{{
  "summary": "<2-3 sentence overview>",
  "action_items": [
    {{"task": "...", "owner": "...", "deadline": "..."}}
  ],
  "decisions": ["decision1", "decision2"],
  "key_topics": ["topic1", "topic2"],
  "next_meeting_agenda": ["agenda item 1", "agenda item 2"],
  "sentiment": "positive|neutral|negative"
}}
Only return valid JSON, no markdown fences."""

    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
    except:
        result = {
            "summary": response.text[:300],
            "action_items": [],
            "decisions": [],
            "key_topics": [],
            "next_meeting_agenda": [],
            "sentiment": "neutral"
        }
    result["title"] = meeting_title
    result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    meetings_store.append(result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT 3 — Task Manager Agent
# ══════════════════════════════════════════════════════════════════════════════
def task_manager_agent(user_input: str, existing_tasks: list = None) -> dict:
    tasks_json = json.dumps(existing_tasks or tasks_store, indent=2)
    prompt = f"""You are an intelligent task management assistant.

User Request: {user_input}

Current Tasks:
{tasks_json}

Based on the request, return a JSON response:
{{
  "action": "create|update|prioritize|analyze|complete",
  "tasks": [
    {{
      "id": <number>,
      "title": "...",
      "description": "...",
      "priority": "high|medium|low",
      "status": "pending|in_progress|completed",
      "due_date": "YYYY-MM-DD or null",
      "tags": ["tag1"],
      "estimated_hours": <number or null>
    }}
  ],
  "message": "<helpful message to user>",
  "productivity_tip": "<one actionable tip>"
}}
Only return valid JSON, no markdown fences."""

    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
        # Merge tasks into store
        for t in result.get("tasks", []):
            existing = next((x for x in tasks_store if x.get("id") == t.get("id")), None)
            if existing:
                existing.update(t)
            else:
                if not t.get("id"):
                    t["id"] = len(tasks_store) + 1
                tasks_store.append(t)
    except:
        result = {"action": "analyze", "tasks": tasks_store, "message": response.text, "productivity_tip": ""}
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT 4 — Calendar Assistant
# ══════════════════════════════════════════════════════════════════════════════
def calendar_assistant_agent(user_request: str) -> dict:
    existing_events = json.dumps(calendar_events, indent=2)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""You are a smart calendar scheduling assistant.

Current DateTime: {current_time}
User Request: {user_request}

Existing Events:
{existing_events}

Return JSON:
{{
  "action": "schedule|reschedule|cancel|view|remind",
  "events": [
    {{
      "id": <number>,
      "title": "...",
      "date": "YYYY-MM-DD",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "description": "...",
      "attendees": ["name1"],
      "location": "...",
      "reminder_minutes": <number>
    }}
  ],
  "conflicts": [],
  "suggestions": ["suggestion1"],
  "message": "<response to user>"
}}
Only return valid JSON, no markdown fences."""

    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
        for ev in result.get("events", []):
            existing = next((x for x in calendar_events if x.get("id") == ev.get("id")), None)
            if existing:
                existing.update(ev)
            else:
                if not ev.get("id"):
                    ev["id"] = len(calendar_events) + 1
                calendar_events.append(ev)
    except:
        result = {"action": "view", "events": calendar_events, "message": response.text, "suggestions": [], "conflicts": []}
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/email-agent", methods=["POST"])
def api_email():
    data = request.json
    result = email_reply_agent(
        email_content=data.get("email_content", ""),
        tone=data.get("tone", "professional"),
        context=data.get("context", "")
    )
    return jsonify({"success": True, "result": result})


@app.route("/api/meeting-agent", methods=["POST"])
def api_meeting():
    data = request.json
    result = meeting_summary_agent(
        transcript=data.get("transcript", ""),
        meeting_title=data.get("title", "Meeting")
    )
    return jsonify({"success": True, "result": result})


@app.route("/api/task-agent", methods=["POST"])
def api_task():
    data = request.json
    result = task_manager_agent(user_input=data.get("input", ""))
    return jsonify({"success": True, "result": result, "all_tasks": tasks_store})


@app.route("/api/calendar-agent", methods=["POST"])
def api_calendar():
    data = request.json
    result = calendar_assistant_agent(user_request=data.get("request", ""))
    return jsonify({"success": True, "result": result, "all_events": calendar_events})


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "emails_processed": len(email_history),
        "meetings_summarized": len(meetings_store),
        "tasks_total": len(tasks_store),
        "tasks_completed": len([t for t in tasks_store if t.get("status") == "completed"]),
        "events_scheduled": len(calendar_events),
        "recent_emails": email_history[-3:] if email_history else [],
        "recent_tasks": tasks_store[-5:] if tasks_store else [],
        "upcoming_events": sorted(calendar_events, key=lambda x: x.get("date", ""))[:3]
    })


@app.route("/api/send-email", methods=["POST"])
def send_real_email():
    """Optional: actually send email via SMTP"""
    data = request.json
    smtp_config = data.get("smtp", {})
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_config.get("from_email")
        msg["To"] = data.get("to")
        msg["Subject"] = data.get("subject")
        msg.attach(MIMEText(data.get("body"), "plain"))

        with smtplib.SMTP(smtp_config.get("host", "smtp.gmail.com"),
                          smtp_config.get("port", 587)) as server:
            server.starttls()
            server.login(smtp_config.get("from_email"), smtp_config.get("password"))
            server.sendmail(smtp_config.get("from_email"), data.get("to"), msg.as_string())
        return jsonify({"success": True, "message": "Email sent!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
