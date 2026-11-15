# OpenScholar Agent

**An Open-Source, Multi-User AI Opportunity Research and Application Assistant**

OpenScholar Agent is a general-purpose AI agent designed to help users discover, evaluate, and manage international academic, research, and professional opportunities. Unlike simple search bots that just collect links, this system focuses on **accuracy and evidence-based verification**. It inspects official pages, evaluates funding, checks eligibility requirements, and delivers personalized reports via Telegram.

## ✨ Key Features

- **Multi-User Architecture:** Each user has an independent profile, preferences, and notification settings.
- **Strict Eligibility Engine:** Accurately distinguishes between completed degrees and degrees in progress. (e.g., A user with a Bachelor's degree currently enrolled in a Master's will be marked correctly for different opportunity types).
- **Evidence-Based Verification:** Uses Grounding and Anti-Prompt-Injection techniques to ensure the AI does not invent facts. Claims are only verified if they exist word-for-word on official pages.
- **Multi-LLM Provider Support:** Not tied to a single company. Supports OpenAI, Anthropic (Claude), Google Gemini, and OpenAI-compatible endpoints.
- **Telegram Integration:** Interactive Telegram bot that sends personalized daily reports in Persian, categorized by opportunities, deadlines, and rejection reasons.
- **Run without LLM:** The system remains fully functional using rule-based extraction even without an LLM API key.

## 🏗️ Architecture & Tech Stack

- **Language:** Python 3.12+
- **Database:** SQLite (with SQLAlchemy, ready to migrate to PostgreSQL)
- **Data Validation:** Pydantic
- **HTTP Client:** HTTPX
- **Architecture:** Modular Monolith

## 🚀 Prerequisites

Before you begin, ensure you have:
- Python 3.12 or higher installed.
- Git installed.
- A Telegram Bot Token (get it from [@BotFather](https://t.me/BotFather)).
- *(Optional)* An API key for an LLM (Gemini, OpenAI, etc.) and a Search API (like Brave).

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mohammadreza4188/open-scholar-agent.git
   cd open-scholar-agent