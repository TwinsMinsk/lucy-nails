---
trigger: always_on
---

# GEMINI.md - Antigravity Kit (Customized for Nails Course)

> This file defines how the AI behaves in this workspace.

---

В ЧАТЕ ВСЕГДА ОТВЕЧАЙ И ПИШИ НА РУССКОМ ЯЗЫКЕ!!!

## 🚀 PROJECT CONTEXT (USER OVERRIDE)

> **CRITICAL:** These rules override any generic defaults.

### 0. Cursor IDE (приоритет для этого репозитория)

- Главный onboarding для AI в **Cursor**: **`AGENTS.md`** + правила в **`.cursor/rules/`** + карта **`CODEBASE.md`**.
- Файл **`GEMINI.md`** и дерево **`.agent/`** — перенос из прошлой среды (Antigravity/др.): это **справочный архив** глубоких сценариев и skill-файлов. Не читай всё подряд из `.agent/` — только релевантный `SKILL.md` по задаче.
- Если инструкции в `GEMINI.md` расходятся с `AGENTS.md` / `.cursor/rules` для Cursor — **выигрывают** `AGENTS.md` и `.cursor/rules`.

### 1. Tech Stack & Architecture
- **Frontend:** Next.js **16** (App Router), React **19**, TypeScript, Tailwind CSS, shadcn/ui, `lucide-react` (см. `frontend/package.json`).
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic V2.
- **Database:** PostgreSQL 15 (asyncpg), Redis (Optional).
- **Testing:** pytest (backend).
- **Integrations:** Kinescope (Video DRM), Prodamus (Payments), Telegram Bot.

### 2. Environment (Windows Native)
- **OS:** Windows 11 (Native, **NO Docker**).
- **Shell:** PowerShell.
  - Activate venv: `.\backend\venv\Scripts\Activate.ps1`
  - Run Dev: `.\scripts\dev.ps1`
  - Run Tests: `$env:PYTHONPATH="backend"; .\backend\venv\Scripts\python.exe -m pytest backend/tests -v`
- **Secrets:** корневой `.env` (+ опционально `backend/.env`). Для Next используйте `frontend/.env.local` (см. `frontend/.env.example` и `Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`).
- **DB Access:** Localhost (`localhost:5432`). Пароль и `DATABASE_URL` в `.env`.

### 3. Database Schema (7 Tables)
| Table | Key Fields |
|-------|------------|
| `users` | id (UUID), email, password_hash, telegram_id, role |
| `courses` | id, title, price_self, price_support, is_published |
| `modules` | id, course_id, title, order_index |
| `lessons` | id, module_id, kinescope_video_id, duration_seconds |
| `purchases` | id, user_id, course_id, tariff, expires_at |
| `progress` | id, user_id, lesson_id, watched_seconds, is_completed |
| `certificates` | id, user_id, course_id, pdf_url |

### 4. Code Rules (Strict)
- **Auth:** ONLY via FastAPI Dependencies (`get_current_user`). **NO RLS in DB.**
- **ORM:** Always use `async_session`. Eager load via `.options(selectinload(...))`.
- **UI:** Server Components by default. 'use client' only for interactivity.
- **Language:**
  - Ответы пользователю — **на русском**.
  - Комментарии в коде и стиль имён — **как в затрагиваемом файле/модуле** (в проекте часто русские docstring/комментарии на backend; во frontend чаще короткий английский — не ломай без нужды).

---

## CRITICAL: AGENT & SKILL PROTOCOL (START HERE)

> **MANDATORY:** You MUST read the appropriate agent file and its skills BEFORE performing any implementation. Это правило пришло из Antigravity-потока.

> **Cursor note:** В **Cursor** базовый onboarding — **`AGENTS.md` + `.cursor/rules/` + `CODEBASE.md`**. Файлы в **`.agent/agents/`** открывай **только если** задача действительно про тот workflow/роль; не читай архив целиком «на всякий случай».

### 1. Modular Skill Loading Protocol
Agent activated → Check frontmatter "skills:" field │ └── For EACH skill: ├── Read SKILL.md (INDEX only) ├── Find relevant sections from content map └── Read ONLY those section files


- **Selective Reading:** DO NOT read ALL files in a skill folder. Read `SKILL.md` first, then only read sections matching the user's request.
- **Rule Priority:** P0 (**`AGENTS.md` + `.cursor/rules/`**, затем Project Context в `GEMINI.md`) > P1 (Agent `.agent/agents/*.md` при необходимости) > P2 (конкретный `SKILL.md` в `.agent/skills/...`).

### 2. Enforcement Protocol
1. **When agent is activated:**
    - ✅ READ Project Context (Top of file).
    - ✅ CHECK frontmatter `skills:` list.
    - ✅ LOAD each skill's `SKILL.md`.
    - ✅ APPLY all rules.
2. **Forbidden:** Never skip reading agent rules or skill instructions.

---

## 📥 REQUEST CLASSIFIER (STEP 2)

**Before ANY action, classify the request:**

| Request Type | Trigger Keywords | Active Tiers | Result |
|--------------|------------------|--------------|--------|
| **QUESTION** | "what is", "how does", "explain" | TIER 0 only | Text Response |
| **SURVEY/INTEL**| "analyze", "list files", "overview" | TIER 0 + Explorer | Session Intel (No File) |
| **SIMPLE CODE** | "fix", "add", "change" (single file) | TIER 0 + TIER 1 (lite) | Inline Edit |
| **COMPLEX CODE**| "build", "create", "implement", "refactor" | TIER 0 + TIER 1 (full) + Agent | **{task-slug}.md Required** |
| **DESIGN/UI** | "design", "UI", "page", "dashboard" | TIER 0 + TIER 1 + Agent | **{task-slug}.md Required** |
| **SLASH CMD** | /create, /orchestrate, /debug | Command-specific flow | Variable |

---

## TIER 0: UNIVERSAL RULES (Always Active)

### 🌐 Language Handling

When user's prompt is NOT in English:
1. **Internally translate** for better comprehension
2. **Respond in user's language** - match their communication (Russian/Русский)
3. Комментарии/идентификаторы в коде — **согласованно с текущим файлом** (см. PROJECT CONTEXT §4)

### 🧹 Clean Code (Global Mandatory)

**ALL code MUST follow** `.agent/skills/clean-code/SKILL.md` (читай выборочно: INDEX → нужные секции). **No exceptions.**

- Concise, direct, solution-focused
- No verbose explanations
- **Self-Documentation:** Every agent is responsible for documenting their own changes in relevant `.md` files.

### 📁 File Dependency Awareness

**Before modifying ANY file:**
1. Прочитай `CODEBASE.md` (есть в репозитории) или проследуй по imports.
2. Identify dependent files
3. Update ALL affected files together

### 🗺️ System Map Read

> 🔴 **MANDATORY:** Read `Docs/ARCHITECTURE.md` (и при первом входе — `CODEBASE.md`) at session start.

---

## TIER 1: CODE RULES (When Writing Code)

### 📱 Project Type Routing

| Project Type | Primary Agent | Skills |
|--------------|---------------|--------|
| **WEB** (Next.js, React web) | `frontend-specialist` | frontend-design |
| **BACKEND** (API, server, DB) | `backend-specialist` | api-patterns, database-design |

### 🛑 Socratic Gate

**For complex requests, STOP and ASK first:**

| Request Type | Strategy | Required Action |
|--------------|----------|-----------------|
| **New Feature / Build** | Deep Discovery | ASK minimum 3 strategic questions |
| **Code Edit / Bug Fix** | Context Check | Confirm understanding + ask impact questions |

**Protocol:** 1. **Never Assume:** If even 1% is unclear, ASK.
2. **Wait:** Do NOT invoke subagents or write code until the user clears the Gate.

### 🏁 Final Checklist Protocol

**Trigger:** When the user says "son kontrolleri yap", "final checks", "проверь всё", or similar phrases.

| Task Stage | Command | Purpose |
|------------|---------|---------|
| **Manual Audit** | `python .agent/scripts/checklist.py .` | Priority-based project audit |

**Priority Execution Order:**
1. **Security** → 2. **Lint** → 3. **Schema** → 4. **Tests**

### 🎭 Gemini Mode Mapping

| Mode | Agent | Behavior |
|------|-------|----------|
| **plan** | `project-planner` | 4-phase methodology. NO CODE before Phase 4. |
| **ask** | - | Focus on understanding. Ask questions. |
| **edit** | `orchestrator` | Execute. Check `{task-slug}.md` first. |

---

## 📁 QUICK REFERENCE

### Available Master Agents
- `orchestrator`: Coordination
- `backend-specialist`: API + DB
- `frontend-specialist`: UI/UX + Next.js

### Key Skills
- `clean-code`: Coding standards (GLOBAL)
- `api-patterns`: FastAPI best practices
- `frontend-design`: shadcn/ui patterns