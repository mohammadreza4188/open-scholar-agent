# OpenScholar Agent

**An Open-Source, Multi-User AI Opportunity Research Agent**

OpenScholar Agent is a multi-user AI-powered research agent designed to discover, evaluate, and manage international academic, research, and professional opportunities.

Unlike traditional search bots that simply collect links, OpenScholar Agent focuses on accuracy, eligibility validation, and evidence-based verification. It analyzes opportunity requirements, evaluates funding information, distinguishes between completed and ongoing academic degrees, and delivers personalized daily reports through Telegram.

The project aims to make international academic and professional opportunities more accessible through reliable, automated, and personalized AI-assisted research.

---

## ✨ Key Features

### 1. Multi-User Architecture
- Independent user profiles and academic backgrounds.
- Personalized opportunity preferences.
- Individual notification settings.
- Isolated user-specific data management.

### 2. Strict Eligibility Engine
- Distinguishes completed degrees from degrees currently in progress.
- Evaluates academic qualifications against opportunity requirements.
- Identifies eligibility mismatches before recommending opportunities.
- Reduces false-positive recommendations.

For example, a user currently enrolled in a Master's program is not automatically considered to have completed that degree.

### 3. Evidence-Based Verification
- Grounding-based verification of extracted information.
- Evidence-oriented opportunity evaluation.
- Anti-Prompt-Injection protections.
- Distinguishes verified claims from uncertain or unavailable information.
- Prioritizes official opportunity sources over unverified descriptions.

### 4. Multi-LLM Provider Support

OpenScholar Agent is designed to be provider-independent.

Supported providers include:

- OpenAI
- Anthropic (Claude)
- Google Gemini
- OpenAI-compatible API endpoints

Users can configure their preferred LLM provider without redesigning the core application.

### 5. Telegram Integration
- Interactive Telegram bot.
- Personalized daily opportunity reports.
- Persian-language report delivery.
- Categorized opportunity notifications.
- Eligibility-based filtering and rejection explanations.

### 6. LLM-Optional Operation
The application can operate without an LLM API key through its rule-based extraction and processing capabilities.

LLM integration enhances analysis and verification but is not a mandatory dependency for basic functionality.

---

## 🏗️ Architecture & Technology Stack

OpenScholar Agent follows a modular monolithic architecture, separating application responsibilities into maintainable components.

| Component | Technology |
|---|---|
| Programming Language | Python 3.12+ |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data Validation | Pydantic |
| HTTP Client | HTTPX |
| Messaging Interface | Telegram Bot API |
| AI Integration | OpenAI, Anthropic, Google Gemini |
| Configuration | Environment Variables |
| Architecture | Modular Monolith |

### Architectural Principles

- **Modularity:** Independent components for user management, opportunity processing, eligibility evaluation, and AI integration.
- **Provider Independence:** LLM providers are accessed through a unified integration layer.
- **Data Integrity:** Structured data validation and database persistence.
- **Security:** Input validation, prompt-injection protections, and evidence-based verification.
- **Extensibility:** Designed to support additional search providers, database backends, and user interfaces.

---

## 📋 Prerequisites

Before installing OpenScholar Agent, ensure that you have:

- Python 3.12 or higher.
- Git.
- pip (Python package installer).
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).

### Optional Requirements

Depending on your configuration:

- An API key from an LLM provider:
  - OpenAI
  - Anthropic
  - Google Gemini
- An API key from a search provider (planned integration):
  - Brave Search
  - Tavily

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/mohammadreza4188/open-scholar-agent.git
cd open-scholar-agent