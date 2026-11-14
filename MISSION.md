# Project Mission: Build OpenScholar Agent
## An Open-Source, Multi-User AI Opportunity Research and Application Assistant

You are acting as a complete senior engineering team responsible for architecting, implementing, testing, and documenting a real-world open-source software product.

Your roles include:

- Senior Software Architect
- Python Backend Engineer
- AI/LLM Engineer
- Research Automation Engineer
- Data and Search Engineer
- DevOps Engineer
- Security Engineer
- Open-Source Product Maintainer

Your mission is not to produce a conceptual proposal, a tutorial, or a collection of example scripts.

**Your mission is to build a functional, maintainable, extensible, and publicly publishable software product.**

You must inspect the available development environment, make sound engineering decisions, create the actual project files, implement the application, run tests, fix problems, and deliver a working MVP.

Do not stop after presenting an architecture or implementation plan.

---

# 1. Product Vision

We want to build an open-source AI Opportunity Research Agent that helps people discover, evaluate, and manage international academic, research, and professional opportunities.

The system should understand a user's academic and professional profile, discover relevant opportunities worldwide, inspect official eligibility requirements, evaluate funding conditions, identify application deadlines, and deliver personalized reports through Telegram.

This must be much more than a search bot that collects links.

The system should be able to:

1. Maintain an independent profile for each user.
2. Discover international opportunities from multiple sources.
3. Find and inspect official university, company, laboratory, and funding pages.
4. Extract admission and employment requirements.
5. Determine whether a user is eligible to apply.
6. Extract funding, salary, tuition coverage, stipends, and benefits.
7. Identify application deadlines and time zones.
8. Detect duplicate opportunities.
9. Track changes to previously discovered opportunities.
10. Rank opportunities according to user preferences and qualifications.
11. Send personalized daily reports through Telegram.
12. Help users prepare application materials.
13. Support multiple LLM providers without depending on a single company.
14. Be publicly available on GitHub and open to community contributions.

The project must be designed as a general-purpose product, not as a personal script for one individual.

Working project name:

**OpenScholar Agent**

The name should remain configurable and independent of any particular AI provider.

## Core Product Principle

Accuracy is more important than the number of links collected.

A small number of officially verified, genuinely relevant opportunities is more valuable than hundreds of irrelevant or unverified results.

---

# 2. Multi-User Architecture and User Profiles

The system must support multiple independent users.

Each user must have a separate profile, preferences, search history, notification settings, and application records.

A user profile should support:

- Current academic degree
- Highest completed academic degree
- Academic discipline and specialization
- University and country
- GPA and grading scale
- Study start and expected graduation dates
- Current enrollment status
- Research experience
- Publications
- Academic and technical projects
- Technical skills
- Programming languages
- Language proficiency and test scores
- Preferred countries and regions
- Preferred academic levels
- Preferred research areas
- Minimum funding or salary requirements
- Visa and work authorization constraints
- Personal application preferences

## Critical: Academic Status Must Be Modeled Correctly

The system must distinguish between:

- A completed Bachelor's degree
- Currently enrolled in a Master's program
- A completed Master's degree
- Currently enrolled in a PhD program
- A completed PhD degree

These states must never be treated as interchangeable.

For example:

A person who has completed a Bachelor's degree and is currently enrolled in a Master's program does NOT hold a completed Master's degree.

This distinction is essential for scholarship eligibility, graduate admissions, internships, and direct-entry PhD opportunities.

The eligibility engine must be able to distinguish between:

- Degree completed
- Degree in progress
- Degree required at application time
- Degree required before enrollment
- Active student enrollment required
- Previous enrollment prohibited

Users must be able to create and modify their profiles through:

- YAML or JSON configuration files
- Telegram commands
- A future web dashboard

Use a validated, versioned profile schema.

---

# 3. Initial Development and Testing Profile

Use the following profile as the initial test profile during development.

This profile must be stored in a sample configuration file, not hardcoded into application logic.

```yaml
profile:
  education:
    bachelor:
      degree: "BSc Computer Science"
      gpa: "16.47/20"
      completed: true

    current_master:
      degree: "MSc Computer Science"
      specialization: "Soft Computing and Artificial Intelligence"
      university: "Shahid Bahonar University of Kerman"
      country: "Iran"
      enrollment: "October 2026"
      currently_enrolled: true
      completed: false

  research_interests:
    - Artificial Intelligence
    - Machine Learning
    - Deep Learning
    - Soft Computing
    - Fuzzy Systems
    - Computer Vision
    - Natural Language Processing
    - Large Language Models
    - Reinforcement Learning
    - Explainable AI
    - Data Science

  projects:
    - name: "Bearing Fault Diagnosis"
      technologies:
        - CNN
        - Fuzzy Logic
        - Python

    - name: "Olympic Medal Prediction"
      technologies:
        - Machine Learning
        - Data Analysis
        - Python

    - name: "Automotive Diagnostics Tool"
      technologies:
        - Python
        - Automotive Diagnostics

  preferences:
    priority_order:
      - funded_masters
      - paid_internships
      - direct_entry_phd

    worldwide: true
    exclude_countries: []

    funding:
      full_funding: true
      partial_funding: true
      paid_internships: true
```

This profile is only an initial development example.

Every user must be able to replace it with their own information.

Never include student IDs, passport numbers, passwords, private contact information, or other sensitive personal data in public repository files.

---

# 4. Opportunity Discovery and Search Engine

The discovery engine is one of the most important components of this product.

Search internationally. Do not exclude countries or regions by default.

The system should discover opportunities from the following categories.

## 4.1 Universities and Academic Institutions

- Official university websites
- Graduate admissions pages
- Scholarship and financial aid pages
- Research opportunity pages
- Graduate school websites
- Faculty and laboratory websites
- Research group announcements
- University career portals
- Research assistantship announcements

## 4.2 Companies and Industrial Research Centers

- Technology companies
- AI companies
- Industrial research laboratories
- R&D departments
- Research internship programs
- Paid student internships
- Graduate trainee programs
- Data science and machine learning teams

## 4.3 Governmental and International Organizations

- Government scholarship programs
- Research funding organizations
- International academic exchange programs
- Public research institutions
- Scientific foundations
- International research programs

## 4.4 Search Provider Architecture

Design the discovery system to be independent of individual search providers.

Potential integrations include:

- Brave Search API
- Tavily
- Google Programmable Search or suitable alternatives
- Other legitimate Search APIs
- RSS feeds
- Public university APIs
- Official opportunity databases
- Direct access to publicly available institutional pages

Do not assume that every provider is free or unrestricted.

For each source, document:

- API availability
- Pricing
- Rate limits
- Terms of Service
- Authentication requirements
- Geographic coverage
- Known limitations

Do not bypass CAPTCHAs, access controls, or website restrictions.

Do not violate website Terms of Service.

Prefer official APIs, RSS feeds, structured data, and publicly accessible official pages whenever possible.

## 4.5 Source Registry

Build a configurable source registry.

Each source should have:

- Source name
- Source category
- Base URL
- Source type
- Search method
- Update frequency
- Access requirements
- Reliability level
- Last successful check
- Last failure
- Enabled/disabled status

The system should report which sources were actually checked.

Never claim comprehensive worldwide coverage.

The system must be transparent about its search coverage and inaccessible sources.

---

# 5. Search Priorities

The search engine must follow this priority order.

## Priority 1: Funded Master's Programs

The primary search priority is funded Master's programs in fields related to:

- Artificial Intelligence
- Soft Computing
- Machine Learning
- Deep Learning
- Data Science
- Computer Vision
- Natural Language Processing
- Robotics
- Computational Intelligence
- Fuzzy Systems
- Trustworthy AI
- Explainable AI

Separate opportunities into two groups.

### A. Funded Master's Programs

Programs offering full or partial financial support.

### B. Second Master's or Alternative Master's Programs

These opportunities require additional eligibility checks.

For every opportunity, determine:

1. Can applicants with only a completed Bachelor's degree apply?
2. Does current enrollment in another Master's program affect eligibility?
3. Are applicants who already hold a Master's degree excluded?
4. Are currently enrolled Master's students eligible?
5. Is withdrawal from the current program required?
6. Are there nationality restrictions?
7. Does the scholarship cover full tuition?
8. Is a living stipend provided?
9. Are health insurance and travel costs covered?
10. Are there restrictions on previous scholarship awards?

Never classify a program as fully funded simply because the advertisement uses the phrase "Fully Funded".

Inspect the actual financial conditions.

Clearly distinguish:

- Full tuition coverage
- Partial tuition coverage
- Living stipend
- Accommodation
- Health insurance
- Travel allowance
- Other financial benefits

If some information is unavailable, explicitly mark it as unknown.

## Priority 2: Paid Research and Industrial Internships

Search for:

- AI Research Internships
- Machine Learning Internships
- Deep Learning Research
- Computer Vision Research
- NLP and LLM Research
- Robotics Research
- Data Science Internships
- AI in Engineering
- AI in Sports Analytics
- Research Assistantships
- Industrial R&D Internships

For each opportunity, verify:

- Can currently enrolled Master's students apply?
- Are international students accepted?
- Are Bachelor's graduates eligible?
- Is active university enrollment required?
- Is a university recommendation letter required?
- Must the student return to their university after the internship?
- Are there graduation-date restrictions?
- Is a salary or stipend provided?
- Are travel and accommodation supported?
- Does the employer assist with work authorization or visas?
- What is the duration?
- What is the expected start date?

Unpaid internships without clearly documented financial support must not appear in the main paid-opportunity list.

They may be placed in a separate optional category if relevant.

## Priority 3: Direct-Entry PhD Opportunities

Search for PhD opportunities that explicitly allow applicants without a completed Master's degree.

Classify requirements into three categories.

**Category A: Bachelor's degree is sufficient at application time.**

**Category B: Bachelor's degree is sufficient when applying, but a Master's degree must be completed before enrollment.**

**Category C: A completed Master's degree is mandatory at application time.**

Only Categories A and B should appear in the actionable direct-entry PhD section.

Category C must appear separately under:

"Currently Not Eligible: Completed Master's Degree Required"

Do not interpret vague phrases such as "Bachelor's and/or Master's degree" as proof of direct-entry eligibility.

Inspect the official admission requirements.

---

# 6. Opportunity Verification Engine

This component is critical.

Every discovered opportunity must pass through a structured verification pipeline.

Required stages:

1. Opportunity discovery
2. Canonical URL resolution
3. Official source identification
4. Official page retrieval
5. Requirement extraction
6. Degree requirement analysis
7. Student-status analysis
8. Nationality restriction analysis
9. Funding extraction
10. Deadline extraction
11. Time-zone identification
12. Profile compatibility evaluation
13. Verification status assignment
14. Database storage

Each opportunity should contain a structured record similar to:

```json
{
  "opportunity_id": "unique_id",
  "title": "Opportunity Title",
  "organization": "University or Company",
  "country": "Country",
  "category": "masters",
  "field": "Artificial Intelligence",
  "official_url": "https://example.com",
  "application_url": "https://example.com/apply",
  "funding_type": "full",
  "funding_amount": null,
  "currency": null,
  "tuition_coverage": "full",
  "stipend": null,
  "insurance": null,
  "travel_support": null,
  "eligibility": [],
  "degree_requirement": null,
  "student_status_requirement": null,
  "nationality_restrictions": null,
  "deadline": null,
  "deadline_timezone": null,
  "start_date": null,
  "duration": null,
  "verification_status": "verified",
  "profile_match_score": null,
  "eligibility_decision": null,
  "last_checked": null
}
```

The schema may be improved during implementation.

Use null or an explicit unknown value whenever information is unavailable.

Never invent:

- Funding amounts
- Salaries
- Deadlines
- Admission requirements
- Application URLs
- Eligibility conditions

## Verification Levels

Implement the following statuses:

- Verified
- Partially Verified
- Unverified
- Closed
- Withdrawn

Definitions:

**Verified:** The important claims have been checked against official sources.

**Partially Verified:** Some important information has been verified, but one or more critical details remain unavailable.

**Unverified:** There is insufficient official evidence to confirm the opportunity.

**Closed:** The application deadline has passed or the official source confirms that applications are closed.

**Withdrawn:** The opportunity has been cancelled or withdrawn.

Unverified opportunities must never be presented as confirmed actionable opportunities.

Store:

- Official source URL
- Supporting page URL
- Verification timestamp
- Extracted evidence
- Last checked timestamp
- Verification notes

Where possible, store the relevant page section or a short supporting quotation for every important claim.

Do not rely on search engine snippets as verification.

---

# 7. Eligibility Intelligence and Profile Matching

Build an independent eligibility engine.

This is potentially the most valuable feature of the entire product.

The system must distinguish between:

1. Eligibility Status
2. Profile Match Score

These are separate outputs.

A high profile match score does not mean that the applicant is eligible.

## 7.1 Profile Match Score

Calculate a score from 0 to 100 using factors such as:

- Research field relevance
- Degree compatibility
- GPA compatibility
- Technical skills
- Research experience
- Publications
- Student status
- Nationality and visa compatibility
- Funding preferences
- Remaining time before deadline

Make the scoring system configurable.

Explain the reasons behind the score.

## 7.2 Eligibility Status

Use these statuses:

- Eligible
- Likely Eligible
- Uncertain
- Not Eligible

A confirmed disqualifying requirement must result in Not Eligible.

For example:

If a position explicitly requires a completed Master's degree, an applicant who only holds a Bachelor's degree and is currently enrolled in a Master's program must not be marked eligible.

The system must distinguish:

- Degree in progress
- Degree completed
- Degree required at application time
- Degree required before program commencement
- Active enrollment requirement
- Previous enrollment restrictions

## 7.3 Evidence-Based Decisions

Every eligibility decision should include:

- Requirement
- User profile fact
- Comparison result
- Supporting official source
- Confidence level
- Explanation
- Unresolved questions

If the official requirements are ambiguous, return Uncertain rather than guessing.

The eligibility engine must be testable independently of the LLM.

Use deterministic rules for explicit requirements wherever possible.

Use LLMs to interpret ambiguous natural-language requirements, not as the sole authority for eligibility decisions.

---

# 8. Multi-Provider LLM Architecture

The product must not depend exclusively on OpenAI, Anthropic, Google, or any other provider.

Implement a provider-based architecture.

Initial provider targets:

- OpenAI API
- Anthropic Claude API
- Google Gemini API
- OpenAI-compatible APIs
- Local LLMs where technically feasible

Users should be able to:

- Select a provider
- Select a model
- Supply their own API key
- Test the connection
- Change providers without modifying application logic
- Disable LLM functionality entirely
- Monitor usage and estimated costs

## 8.1 Provider Interface

Design a common abstraction, for example:

```python
class LLMProvider:
    async def analyze_opportunity(self, opportunity, profile):
        raise NotImplementedError

    async def extract_requirements(self, page_content):
        raise NotImplementedError

    async def generate_application_document(self, context):
        raise NotImplementedError
```

Improve this interface where appropriate.

Use separate adapters for individual providers.

Do not mix provider-specific API logic with the core application.

## 8.2 LLM Responsibilities

LLMs may be used to:

- Interpret opportunity descriptions
- Extract structured requirements
- Identify ambiguous eligibility language
- Explain profile compatibility
- Summarize official pages
- Generate Persian reports
- Assist with application documents
- Identify missing information

LLMs must not invent missing facts.

Important claims must be traceable to official sources.

Use structured outputs and schema validation whenever possible.

## 8.3 Security Against Prompt Injection

Treat all external web content as untrusted data.

An opportunity page must never be able to override system instructions, expose API keys, access private user profiles, or change application configuration.

Separate:

- System instructions
- User profile data
- Retrieved web content
- Model output

Validate all model-generated structured data before storing or acting on it.

## 8.4 LLM Optionality

The system must remain useful without an LLM API key.

The basic version should support:

- Search
- Page retrieval
- Basic structured extraction
- Database storage
- Rule-based eligibility checks
- Duplicate detection
- Telegram reporting

LLM-powered analysis should be an optional enhancement.

---

# 9. Telegram Bot

Build a Telegram bot for user interaction and notifications.

Each user must be associated with an independent profile and notification configuration.

Initial commands:

- `/start`
- `/help`
- `/profile`
- `/edit_profile`
- `/run`
- `/status`
- `/settings`
- `/sources`
- `/opportunities`
- `/deadlines`
- `/pause`
- `/resume`

Implement user authentication and authorization carefully.

A Telegram user must only be able to access their own information.

## 9.1 Daily Report

Send a personalized daily report at the user's configured local time.

The report should contain:

### Section 1: Funded Master's Programs

For each opportunity:

- University
- Country
- Program title
- Funding type
- Tuition coverage
- Living stipend
- Admission requirements
- Eligibility status
- Profile match score
- Deadline
- Official source
- Application link

### Section 2: Paid Internships

For each opportunity:

- Organization
- Country
- Position title
- Salary or stipend
- Student-status requirements
- Duration
- Start date
- Deadline
- Eligibility status
- Official source
- Application link

### Section 3: Direct-Entry PhD Opportunities

For each opportunity:

- University
- Country
- Research topic
- Funding type
- Degree requirement
- Bachelor's-only eligibility
- Deadline
- Eligibility status
- Official source
- Application link

### Section 4: Urgent Deadlines

Highlight opportunities whose deadlines are:

- Today
- Tomorrow
- Within the next seven days

Use the user's local time zone.

Do not confuse a date-only deadline with a confirmed exact closing time.

### Section 5: Rejected Opportunities

Show selected examples of rejected opportunities with clear rejection reasons.

Examples:

- Completed Master's degree required
- Nationality restriction
- Active enrollment required but not satisfied
- No confirmed funding
- Application closed
- Official information unavailable

### Section 6: Search Summary

Always report the search outcome.

If no new verified matching opportunities are found, send a message such as:

"No new opportunities meeting your eligibility and verification requirements were found today."

Never create fake or duplicate opportunities to fill a report.

## 9.2 Interactive Opportunity Actions

Users should be able to request:

- Full opportunity analysis
- Admission requirement details
- Funding breakdown
- Eligibility explanation
- Application checklist
- CV review
- Professor email draft
- Motivation letter draft

Implement pagination and message-length handling for Telegram.

Avoid sending excessive messages.

---

# 10. Application Assistant

The long-term vision is to extend the product from an Opportunity Research Agent into an Application Assistant.

Design modular components for future development.

## 10.1 CV Assistant

- Academic CV generation
- CV improvement
- Opportunity-specific CV adaptation
- Identification of missing qualifications
- Consistency checks against the user's profile

## 10.2 Motivation Letter Assistant

- Generate opportunity-specific motivation letters
- Use only real user experiences and qualifications
- Avoid fabricated achievements
- Adapt content to the institution and research opportunity
- Allow user review and editing

## 10.3 Professor Contact Assistant

- Find relevant professors
- Analyze research interests
- Compare professor research with the user's background
- Draft personalized introductory emails
- Track correspondence

## 10.4 Application Checklist

Track:

- Required documents
- Application deadlines
- Preparation status
- Completed tasks
- Outstanding tasks

## 10.5 Application Tracker

Support statuses:

- Interested
- Preparing
- Submitted
- Interview
- Accepted
- Rejected
- Waitlisted

The user must explicitly approve any actual application submission or external communication.

Never submit applications or send emails automatically without explicit authorization.

---

# 11. Database and Duplicate Detection

Use a reliable database architecture.

SQLite is acceptable for the MVP.

The architecture must support migration to PostgreSQL for multi-user production deployments.

Expected entities include:

- Users
- Profiles
- Providers
- Search Sources
- Opportunities
- Opportunity Evidence
- Eligibility Results
- Verification Records
- Notifications
- Applications
- User Preferences
- Search Runs
- Provider Usage Records

Use appropriate indexes, relationships, migrations, and constraints.

## 11.1 Duplicate Detection

An opportunity discovered on multiple websites must not be sent multiple times.

Use a combination of:

- Canonical URL
- Organization
- Opportunity title
- Application ID
- Deadline
- Content fingerprint

Use fuzzy matching where appropriate, but avoid incorrectly merging unrelated opportunities.

## 11.2 Opportunity Updates

If an existing opportunity changes:

- Update its stored record.
- Record the change.
- Preserve historical information where useful.
- Notify the user when the change is important.

Examples:

- Deadline extended
- Funding changed
- Position reopened
- Application page updated
- Opportunity withdrawn

A changed deadline must be reported as an update, not as a completely new opportunity.

If a previously closed opportunity reopens, update its status and notify the user.

---

# 12. Scheduling and Automation

The application must support:

- Manual execution
- Daily scheduled execution
- User-configurable notification times
- User-specific time zones
- Pause and resume
- Retry after temporary failures
- Execution logs
- Prevention of duplicate jobs
- Safe handling of concurrent tasks

Potential deployment options:

- GitHub Actions for a simple initial scheduled deployment
- Docker
- VPS deployment
- Local execution

For production multi-user scheduling, consider an appropriate job scheduler and persistent task storage.

Do not assume GitHub Actions is the ideal permanent architecture for a large multi-user service.

If using GitHub Actions:

- Use UTC scheduling.
- Document daylight-saving-time limitations.
- Avoid exposing secrets in logs.
- Prevent concurrent executions from sending duplicate reports.
- Provide manual workflow dispatch.

---

# 13. Security and Privacy

Security must be designed from the beginning.

Required protections:

- Never hardcode API keys.
- Never commit Telegram tokens.
- Include `.env` in `.gitignore`.
- Provide `.env.example`.
- Separate users' data.
- Enforce authorization checks.
- Avoid logging sensitive data.
- Validate all external input.
- Protect against prompt injection.
- Implement rate limits.
- Provide API usage controls.
- Provide user data deletion.
- Protect database credentials.
- Use secure secret storage for deployments.

Public repository contents must never contain private user profiles or credentials.

For GitHub Actions, document how to configure repository secrets.

For production multi-user deployments, do not store every user's API key in plaintext.

Evaluate appropriate encryption and secret-management strategies.

The product should clearly explain which data is stored, where it is stored, and which external services receive it.

---

# 14. GitHub Repository Structure

Create a clean and professional repository.

Suggested structure:

```text
open-scholar-agent/
│
├── .github/
│   ├── workflows/
│   │   ├── daily-research.yml
│   │   └── tests.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── config/
│   ├── profile.example.yaml
│   └── settings.example.yaml
│
├── src/
│   └── open_scholar/
│       ├── core/
│       ├── config/
│       ├── search/
│       ├── sources/
│       ├── verification/
│       ├── eligibility/
│       ├── ranking/
│       ├── llm/
│       │   ├── base.py
│       │   ├── openai_provider.py
│       │   ├── anthropic_provider.py
│       │   └── gemini_provider.py
│       ├── telegram/
│       ├── notifications/
│       ├── application_assistant/
│       ├── database/
│       └── scheduler/
│
├── tests/
│
├── scripts/
│
├── docs/
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

This is a starting proposal, not a rigid requirement.

Improve the structure if your final architecture justifies it.

Avoid creating a monolithic Python file.

Keep business logic, integrations, data access, and user interfaces separate.

---

# 15. Open-Source Strategy

The repository will be public on GitHub.

External developers should be able to contribute:

- New search providers
- New LLM providers
- New university sources
- New opportunity categories
- New languages
- New eligibility rules
- New application-assistant features

Provide:

- Professional README
- Installation guide
- Configuration guide
- Telegram setup guide
- OpenAI setup guide
- Claude setup guide
- Gemini setup guide
- Provider development guide
- Contribution guide
- Issue templates
- Pull request template
- Automated tests
- Security policy
- License

MIT is the initial license preference, but inspect the licenses of all dependencies before finalizing the licensing strategy.

Clearly explain that users can supply their own API keys and that the product is not tied to a specific LLM provider.

The README should include:

- Product overview
- Features
- Architecture
- Screenshots or sample Telegram reports, if available
- Installation
- Configuration
- Usage
- Deployment
- Security notes
- Limitations
- Contribution instructions
- Roadmap

Do not claim that features work unless they have actually been implemented and tested.

---

# 16. Technology Stack

Python is the preferred primary language.

Potential technologies:

- Python 3.12+
- FastAPI, if an HTTP API is needed
- Pydantic for schema validation
- SQLAlchemy
- Alembic for migrations
- SQLite
- PostgreSQL
- APScheduler or another suitable scheduler
- Telegram Bot API
- HTTPX
- BeautifulSoup
- Playwright only where automated access is permitted
- Pytest
- Docker
- GitHub Actions

For LLM integrations, use official SDKs where appropriate.

Before selecting a dependency:

1. Check whether it is actively maintained.
2. Check its license.
3. Check security considerations.
4. Check compatibility.
5. Pin or constrain versions appropriately.
6. Avoid unnecessary dependencies.

Do not add technologies simply because they are popular.

Choose the simplest reliable architecture that meets the requirements.

---

# 17. Testing and Reliability

Testing is mandatory.

Do not deliver a project that only appears to work.

Implement tests for:

1. Profile creation and validation
2. Configuration loading
3. Search providers
4. Page retrieval
5. Opportunity extraction
6. Degree requirement extraction
7. Student-status classification
8. Eligibility decisions
9. Deadline parsing
10. Time-zone handling
11. Duplicate detection
12. Opportunity updates
13. LLM provider adapters using mocks
14. Telegram notification generation using mocks
15. Security-sensitive configuration
16. Network and API failures
17. Database operations
18. Scheduler behavior

## Required Eligibility Test Scenarios

Test at least the following cases:

**Scenario A:** User has a completed Bachelor's degree and no Master's enrollment.

**Scenario B:** User has a completed Bachelor's degree and is currently enrolled in a Master's program, but has not completed it.

**Scenario C:** User has a completed Master's degree.

**Scenario D:** Opportunity requires only a Bachelor's degree.

**Scenario E:** Opportunity requires a completed Master's degree.

**Scenario F:** Opportunity requires active university enrollment.

**Scenario G:** Opportunity accepts Bachelor's applicants at application time but requires a Master's degree before enrollment.

**Scenario H:** Opportunity excludes applicants with previous Master's enrollment.

These cases must not be incorrectly classified as equivalent.

Use mocked external services for automated tests.

Create separate integration tests for real services where credentials are available.

Never expose real API keys during testing.

---

# 18. Future Web Dashboard

The initial release should focus on Telegram and configuration files.

However, keep the architecture ready for a future web dashboard.

Potential features:

- User profile management
- Opportunity search and filtering
- Saved opportunities
- Application tracking
- Provider and model selection
- API usage monitoring
- Historical reports
- Notification settings
- Eligibility explanations

Do not spend excessive development time on the dashboard in the initial phase.

The research and eligibility engine must work first.

---

# 19. Execution Roadmap

Implement the project incrementally.

Do not attempt to build every future feature before the core system works.

## Phase 0: Environment and Architecture Inspection

Before writing code:

1. Inspect the current working directory.
2. Identify existing files and repositories.
3. Inspect available development tools.
4. Check the Python environment.
5. Check existing dependencies.
6. Identify whether Git is initialized.
7. Determine whether this is a new project or an existing codebase.
8. Inspect existing project files before modifying anything.

If a repository already exists, do not overwrite it blindly.

Preserve useful work.

Then create a concise architecture and implementation plan.

Proceed with implementation immediately after the plan.

## Phase 1: Functional MVP

Implement:

- Project structure
- Configuration system
- User profile schema
- Search provider abstraction
- At least a few real, accessible search sources
- Official page retrieval
- Basic opportunity extraction
- Verification status
- Initial eligibility rules
- Database storage
- Duplicate detection
- Persian report generation
- Telegram integration
- Manual execution
- Automated tests
- Installation documentation

The MVP must work without an LLM API key.

At least one end-to-end test must demonstrate:

1. A real or controlled opportunity source is queried.
2. An opportunity is extracted.
3. Its information is stored.
4. Basic eligibility analysis is performed.
5. A Telegram report is generated.
6. A test or authorized real Telegram message is successfully delivered.

Never claim a real Telegram message was sent if no valid bot token was available.

## Phase 2: Multi-LLM Integration

Implement:

- Common provider interface
- OpenAI adapter
- Anthropic adapter
- Gemini adapter
- OpenAI-compatible adapter where feasible
- Provider configuration
- Model selection
- API key management
- Connection testing
- Error handling
- Usage and cost tracking

Test adapters using mocks when credentials are unavailable.

## Phase 3: Research and Eligibility Intelligence

Implement:

- Better official-page extraction
- Structured eligibility analysis
- Degree-status reasoning
- Funding analysis
- Nationality restrictions
- Deadline extraction
- Evidence-based decisions
- Profile matching
- Opportunity ranking
- Duplicate and update detection
- Improved reporting

## Phase 4: Automation and Deployment

Implement:

- Scheduled execution
- User-specific time zones
- GitHub Actions
- Docker
- VPS deployment documentation
- Persistent job management
- Multi-user safeguards
- Rate limits
- Retry policies
- Usage controls

## Phase 5: Application Assistant

Implement modular support for:

- CV Assistant
- Motivation Letter Assistant
- Professor Email Assistant
- Application Checklist
- Application Tracker

Actual application submissions and external communications must always require explicit user authorization.

---

# 20. MVP Acceptance Criteria

The MVP is not complete until all the following conditions are satisfied:

- A user can create and validate a profile.
- The profile can be modified without changing source code.
- The system can query real opportunity sources.
- The system can retrieve official pages.
- Opportunities can be extracted and stored.
- Verification status is assigned correctly.
- Degree and student status are evaluated separately.
- Eligibility rules work for the required test cases.
- Duplicate opportunities are detected.
- Reports can be generated in Persian.
- Telegram integration works when valid credentials are provided.
- Manual execution works.
- The system provides useful basic functionality without an LLM API key.
- Installation and configuration are documented.
- Automated tests pass.
- No private information or secrets are committed to the repository.

Do not mark an acceptance criterion as completed unless there is actual evidence.

---

# 21. Engineering and Execution Rules

These rules are mandatory.

## Rule 1: Build, Do Not Merely Describe

Do not stop after producing an architecture document.

Create the actual files and implement the software.

## Rule 2: Inspect Before Modifying

Always inspect the existing environment and files before changing them.

Do not overwrite existing work without understanding it.

## Rule 3: Work in Small, Verifiable Steps

Implement a component, test it, fix issues, and then proceed.

Do not generate a huge amount of untested code.

## Rule 4: Be Honest About Execution

Never claim that code was executed, a test passed, an API was contacted, or a Telegram message was sent unless that actually happened.

Clearly distinguish:

- Implemented
- Tested successfully
- Tested with mocks
- Not tested
- Blocked by missing credentials
- Planned for a future phase

## Rule 5: Do Not Fabricate Research Results

Never invent opportunities, deadlines, funding amounts, official sources, or admission requirements.

If the system cannot verify an important fact, mark it as unknown.

## Rule 6: Protect Private Information

Do not place private user information, API keys, bot tokens, or credentials in public repository files.

## Rule 7: Make Independent Engineering Decisions

You are expected to make reasonable technical decisions without asking for approval for every small implementation detail.

If a decision has major architectural consequences, document the alternatives and your reasoning.

## Rule 8: Avoid Premature Complexity

Do not build a large distributed system before the MVP works.

Prioritize a clean modular monolith initially unless there is a strong technical reason to do otherwise.

## Rule 9: Keep Documentation Updated

Update documentation as features are implemented.

Do not describe future functionality as if it already exists.

## Rule 10: Continue Until a Meaningful Deliverable Exists

Do not stop merely because you have produced a plan.

If you encounter a limitation, complete all independent work that remains possible and clearly report the blocked components.

---

# 22. Final Delivery Report

At the end of the implementation session, provide a detailed delivery report containing:

1. Final architecture
2. Repository structure
3. Files created or modified
4. Implemented features
5. Tests executed
6. Actual test results
7. Features that remain incomplete
8. External APIs and services required
9. Required environment variables
10. Estimated operational costs
11. Telegram setup instructions
12. GitHub Actions setup instructions
13. Docker setup instructions
14. Local execution instructions
15. Public GitHub publishing instructions
16. Security considerations
17. Known limitations
18. Recommended next development phase

Include exact commands required to install, configure, test, and run the application.

If credentials are missing, explain exactly which steps require them.

Do not fabricate successful execution.

---

# 23. Final Instruction

Start by inspecting the actual development environment and existing repository.

Then:

1. Evaluate the architecture.
2. Identify potential technical problems.
3. Make necessary improvements.
4. Create the project structure.
5. Implement Phase 1.
6. Run the tests.
7. Fix discovered problems.
8. Verify the MVP acceptance criteria.
9. Update the documentation.
10. Provide the final delivery report.

**Do not return only a design document, a roadmap, or pseudocode.**

**I expect actual implementation, actual files, actual tests, and a working MVP to the extent permitted by the available environment and credentials.**

The most important priorities are:

1. Correct eligibility decisions.
2. Official-source verification.
3. Reliable opportunity discovery.
4. User privacy and security.
5. A functional Telegram workflow.
6. Maintainable open-source architecture.
7. Provider-independent AI integration.

Build a product that people can genuinely use, extend, and contribute to.

The goal is not to create another bot that sends random scholarship links.

The goal is to build a trustworthy, evidence-based, multi-user AI Opportunity Research Agent.