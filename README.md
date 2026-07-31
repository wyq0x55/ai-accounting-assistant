# AI Accounting Assistant

Self-hosted, **local-first** AI accounting assistant that turns

> spend money → open app → type it in → pick a category → save

into

> spend money → a pre-filled entry appears → one-click confirm.

It combines three parts:

- **Actual Budget** — the canonical ledger (accounts, categories, budgets,
  reports, family sharing). Battle-tested open-source budgeting app.
- **Local LLM** — any OpenAI-compatible endpoint (Ollama / llama.cpp / vLLM),
  used **only as a fallback** when rules and learned history cannot classify.
- **Assistant (this project)** — ingests raw payment messages, extracts amount
  & merchant, classifies, keeps a review queue, learns from your corrections,
  and pushes confirmed entries into Actual Budget.

Everything runs on your own NAS / server. No third-party cloud, offline-capable.

---

## Architecture

```
 raw text / CSV ──▶ Assistant (Flask)
                       │  parse → classify (rules ▸ learned mapping ▸ LLM)
                       │  state machine: detected → ai_classified → pending_review
                       │                 → confirmed → archived
                       │  local SQLite: review queue + self-learning
                       └── on confirm ──▶ Bridge (Node, @actual-app/api) ──▶ Actual Server
                                                                              (ledger / budgets / reports)
 Local LLM (OpenAI-compatible) ◀── fallback only
```

Why a Node **bridge**? Actual Budget has no direct REST transaction API; the
official `@actual-app/api` library (Node) is the only supported way to write
transactions. The bridge is a thin sidecar that exposes an internal REST
surface the Flask assistant calls.

### Classification pipeline (cost-ascending)

1. **Learned merchant mapping** (SQLite) — cheapest, highest priority.
2. **Built-in keyword rules** — free, deterministic.
3. **LLM fallback** — only when 1 and 2 miss. Disabled → item is flagged for
   manual review instead.

Every user correction is written back to the mapping store, so repeat merchants
stop needing the LLM over time.

---

## Quick start

### 1. Configure

```bash
cp .env.example .env
# edit .env: set ACTUAL_PASSWORD (and later ACTUAL_SYNC_ID / ACTUAL_DEFAULT_ACCOUNT_ID)
```

### 2. Boot Actual first and create a budget

```bash
docker compose up -d actual_server
```

Open `http://<host>:5006`, set the password (matching `ACTUAL_PASSWORD`),
create a budget and at least one account. Then:

- `Settings → Advanced → Sync ID` → put it in `.env` as `ACTUAL_SYNC_ID`.

### 3. Start everything

```bash
docker compose up -d --build
```

### 4. Find your account id and set it

```bash
curl http://localhost:5008/accounts
# copy an account "id" into .env -> ACTUAL_DEFAULT_ACCOUNT_ID
docker compose up -d assistant   # restart to pick it up
```

### 5. Use it

Open the assistant UI at `http://<host>:5007`.

- **快速导入 (Import):** paste a payment message, e.g.
  ```
  支付宝付款成功
  商户：永辉超市
  金额：126.58 元
  ```
- **待确认队列 (Review):** confirm / edit / delete. Corrections train the model.
- **统计与月报 (Stats):** category breakdown, top merchants, AI monthly report.

Budgets, balances and family sharing live in Actual at `http://<host>:5006`.

---

## Offline / rules-only mode

Leave `OPENAI_MODEL` empty and the assistant runs with **no LLM**: parsing +
keyword rules + learned mappings only. Fully offline. Items that can't be
classified land in the queue flagged as "需人工" (needs manual).

### Using Ollama

```bash
ollama serve
ollama pull qwen2.5:7b
```

`.env`:

```
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_MODEL=qwen2.5:7b
```

(On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the
`assistant` service, or point `OPENAI_BASE_URL` at the host IP.)

---

## Local development

Backend:

```bash
cd assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python wsgi.py            # http://localhost:5007
```

Frontend:

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173, proxies /api to :5007
```

Run tests:

```bash
cd assistant
pip install pytest
pytest
```

---

## API reference (assistant, prefix `/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Service status, LLM & bridge reachability |
| POST | `/ingest/text` | Ingest one raw message `{text, book?}` |
| POST | `/ingest/manual` | Structured quick entry `{amount, category, merchant?, direction?, note?, auto_confirm?}` |
| POST | `/ingest/csv` | Bulk import (`file` upload or `{csv}`), column `text[,book]` |
| GET | `/transactions?bucket=manual\|auto&state=` | List queue items |
| GET | `/transactions/{id}` | Get one |
| PATCH | `/transactions/{id}` | Edit `amount/merchant/category/direction/book/date` (category edit trains learning) |
| POST | `/transactions/{id}/confirm` | Confirm and sync to Actual |
| DELETE | `/transactions/{id}` | Soft-delete |
| POST | `/sync/retry` | Retry confirmed-but-unsynced items |
| GET/POST/PATCH/DELETE | `/categories[/{id}]` | Manage categories |
| GET/POST/DELETE | `/mappings[/{id}]` | Manage learned merchant mappings |
| GET | `/learning/events` | Correction audit trail |
| GET | `/stats?month=YYYY-MM` | Monthly aggregates |
| GET | `/report/monthly?month=YYYY-MM` | AI natural-language monthly report |

---

## MVP scope

Included: manual/CSV ingestion, amount & merchant extraction, AI category
suggestion, review queue, merchant self-learning, basic statistics, AI monthly
report, Actual Budget sync.

Not included (by design): bank direct-connect, investment analysis, OCR receipt
scanning, multi-currency, automatic iPhone notification reading.

---

## Data & privacy

- All data stored locally (Actual data + assistant SQLite).
- Works offline (rules-only) if no LLM is configured.
- Export via Actual Budget's native export.
- Back up the `actual_data`, `assistant_data` and `bridge_cache` Docker volumes.

---

## Project layout

```
ai-accounting-assistant/
├── docker-compose.yml
├── .env.example
├── DESIGN.md             # iOS-style mobile UI spec (IA, flows, tokens, Flutter tree)
├── assistant/            # Flask backend (+ serves built frontend)
│   ├── app/
│   │   ├── api/          # REST blueprints
│   │   ├── services/     # parser, classifier, llm, learning, pipeline, report, bridge
│   │   ├── models.py     # SQLAlchemy models
│   │   └── __init__.py   # app factory
│   ├── config.py
│   ├── wsgi.py
│   └── tests/            # pytest
├── bridge/               # Node @actual-app/api sidecar
└── frontend/             # Vite + React + TypeScript SPA (iOS-style mobile UI)
    └── src/
        ├── App.tsx           # phone shell + bottom TabBar (5 tabs)
        ├── styles.css        # design tokens (:root) + components
        ├── lib/              # api client, ui helpers (icons, money)
        └── components/       # HomePage, PendingPage(swipe), EntryPage(keypad),
                              # StatsPage(donut+AI), MinePage, Categories, Mappings
```

## UI / design

The frontend is a **mobile-first, iOS-native minimalist** interface: 5-tab
bottom bar (首页 / 待确认 / 记账 / 统计 / 我的), big-number home summary, an
Inbox-style pending queue with **swipe-left-to-confirm / swipe-right-to-edit**,
a keypad quick-entry with category icon grid + voice/paste, and a stats page
with a donut, trend bars and an AI insight card. Brand color `#2BC673`.
See `DESIGN.md` for the full spec (information architecture, page flows, hi-fi
prototype descriptions, component specs, design tokens, and a Flutter widget
tree).
