# FlowHR AI
AI-powered HR and workplace workflow management. Python · Streamlit · SQLAlchemy · Pandas · Plotly · Gemini.

## Features
| Module | What it does |
|---|---|
| Employees | Add/edit/deactivate employees, auto IDs (EMP0001…), departments, optional login creation |
| Leave | Apply, balances per type, HR approve/reject with notes, history, attendance check-in/out |
| Tasks & Deadlines | Assign tasks, priorities, deadlines, automatic Overdue detection, status updates |
| Client Emails | Clients, email log, automatic urgency, AI reply drafts (editable), optional SMTP sending, follow-ups, history |
| Meetings | Schedule with participants, agenda, notes, reminders |
| AI Assistant | Chat grounded in real DB data: summaries, overdue work, deadlines, emails, productivity |
| Notifications | Leave decisions, deadline/overdue/meeting reminders, pending-email alerts |
| Dashboard / Reports | KPI cards, Plotly charts, weekly/monthly stats, productivity, CSV export, audit log |
| Security | bcrypt hashing, role-based access (Admin / HR Manager / Employee), input validation, audit trail, secrets in `.env` |

## Run it (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run app.py
```
First launch: create the admin account. Then use **Employees → Add employee** (with a login) to create HR Managers and Employees.

## AI and email (optional)
Put `GEMINI_API_KEY=...` in `.env` for AI chat and reply drafting (free key: Google AI Studio).
Without a key the assistant shows live data summaries and reply templates.
For sending real emails fill `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (Gmail needs an App Password).

## Switch to MySQL
`pip install pymysql`, then in `.env`: `DATABASE_URL=mysql+pymysql://user:password@localhost:3306/flowhr`

## Structure
- `app.py` entry point (setup, login, navigation)
- `config/` settings · `database/` engine + 13 SQLAlchemy models
- `services/` business logic: auth, employee, leave, attendance, task, email, meeting, notification, analytics, ai, audit
- `views/` one Streamlit page per sidebar item · `utils/` validators, errors, styling
- `tests/` pytest suite → `python -m pytest`

## GitHub
Never commit `.env` or `*.db` (already in `.gitignore`).
