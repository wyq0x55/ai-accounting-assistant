# Design Specification — AI Accounting Assistant (iOS-style)

Product principle: **users don't do bookkeeping, they only confirm.** The system
captures, parses, classifies and learns. This document specifies the mobile UI
that ships in `frontend/` (Vite + React, mobile-first, iOS-native aesthetic).

Visual language: iOS-native, minimalist, card-based, medium information density,
soft corners, light shadows, generous whitespace, readability-first.

---

## 1. Information Architecture

```
App (bottom TabBar, 5 tabs)
├── 首页 Home            高频只读概览
│   ├── Monthly summary (expense / income / balance, big numbers)
│   ├── Pending banner  (count -> deep link to 待确认)
│   └── Recent expenses (card list)
├── 待确认 Pending       CORE — Inbox
│   ├── Summary bar (count, needs-attention)
│   ├── Swipe cards (merchant / amount / time / AI category / confidence)
│   │     ├── swipe left  -> confirm
│   │     ├── swipe right -> edit (bottom sheet)
│   │     └── tap         -> detail / edit sheet
│   └── Edit sheet (category grid + amount)
├── 记账 Entry (center)  Quick manual entry
│   ├── Amount display (visual center)
│   ├── Direction toggle (支出 / 收入)
│   ├── Category icon grid
│   ├── Merchant (optional)
│   ├── Numeric keypad
│   └── Voice input / Paste-to-parse
├── 统计 Stats
│   ├── AI insight card (natural-language summary)
│   ├── Category donut
│   ├── Category detail bars
│   ├── Trend bars
│   └── Top merchants
└── 我的 Mine
    ├── System status (LLM / Actual / sync retry)
    ├── Category management
    ├── Merchant mapping (self-learning)
    └── Open Actual Budget (budgets / reports / family sharing)
```

Data sources (assistant REST API, prefix `/api`): `/stats`, `/report/monthly`,
`/transactions`, `/transactions/{id}/confirm|PATCH|DELETE`, `/ingest/text`,
`/ingest/manual`, `/categories`, `/mappings`, `/health`, `/sync/retry`.

---

## 2. Page Flow

```
                 ┌───────────────┐
        launch ─▶│    首页 Home   │──"待确认 N"──▶┐
                 └──────┬────────┘               │
                        │ tab                      ▼
                        │                 ┌──────────────────┐
                        ├────────────────▶│   待确认 Pending  │
                        │                 │  (Inbox)          │
                        │                 └───┬───────┬───────┘
                        │              swipe L│       │swipe R / tap
                        │             confirm │       │edit sheet
                        │                     ▼       ▼
                        │             POST /confirm  PATCH -> confirm
                        │                     │
                        │                     ▼  synced -> Actual Budget
                        │            ┌──────────────────┐
                        ├───────────▶│   记账 Entry      │
                        │            │ keypad / voice /  │
                        │            │ paste-to-parse    │
                        │            └───┬──────────┬────┘
                        │      manual save│         │paste
                        │  POST /ingest/manual   POST /ingest/text
                        │                 │         └─▶ 待确认 queue
                        │                 ▼
                        │            confirmed + synced
                        ├───────────▶ 统计 Stats ─▶ /report/monthly (AI card)
                        └───────────▶ 我的 Mine  ─▶ settings / mappings / Actual
```

Confirmation state machine (backend): `detected → ai_classified →
pending_review → confirmed → archived` (archived = synced into Actual).

---

## 3. Home — hi-fi prototype

- **Nav (large title):** left `概览`; right two status pills `AI 在线`, `Actual`.
- **Hero card** (brand gradient `#2BC673`, radius 20, soft green shadow):
  - Label `本月支出`, big number `¥3,280` (40px/800).
  - Sub line `共 N 笔消费`.
  - Two frosted sub-tiles: `本月收入 ¥…` / `结余 ¥…`.
- **Pending banner** (only if count>0): blue `#3B82F6` on `#EAF1FF`,
  `📥 有 N 条待确认账目` + `去确认 ›` (tap → Pending tab).
- **Recent list** section title `最近消费`; white card; each row:
  round category emoji avatar (brand-weak bg) + merchant (15/600) + `分类 · 日期`
  + amount (expense neutral, income green). Row divider `#EEF0F3`.
- Reachability: everything one thumb-tap; primary numbers above the fold.

---

## 4. Pending — hi-fi prototype (CORE)

- **Summary bar:** brand-weak background, `📥 N 条待确认 · M 条需留意`, hint
  `左滑确认 · 右滑修改`.
- **Swipe card** (radius 14, shadow-1), foreground over a two-color background:
  - Left underlay green `确认 ✓`, right underlay blue `修改`.
  - Foreground: category avatar, merchant (bold) + amount (20/800),
    meta `日期 · 支付方式 · 来源`, then two chips `分类` + `置信度 95%`,
    and a confidence bar (green ≥80%, orange below).
  - Gesture: drag translateX (pointer events, clamp ±140).
    - `≤ -96px` → confirm (`POST /transactions/{id}/confirm`), card removed,
      toast `已确认 ✓`.
    - `≥ +96px` or tap → **Edit sheet**.
  - Motion: release springs back at 240ms `cubic-bezier(.22,.61,.36,1)`.
- **Edit sheet** (bottom, radius 20 top): 2×5 category icon grid, amount field,
  `仅保存` / `保存并确认`. Category change trains the merchant mapping.
- Goal: confirm many items in <5s — swipe is the primary path, no dialogs.
- Empty state: `🎉 全部确认完毕，收件箱已清空`.

---

## 5. Stats — hi-fi prototype

- **Month picker** (native `<input type="month">` styled as a field).
- **AI insight card** (soft green gradient, `✨ AI 分析`): 3–5 sentence summary
  from `/report/monthly` (LLM when available, else deterministic template).
  Example copy: `本月消费 ¥3280。餐饮占比 36%，较上月 +15%。咖啡消费偏多，可考虑控制非必要饮品。`
- **Category donut:** SVG stroke-dasharray donut (14px ring), soft palette;
  legend rows `色块 · 分类 · 百分比` (top 6).
- **Category detail bars:** brand fill, label + `¥amount`.
- **Trend:** simple vertical bars per month (no gridlines, no axes).
- **Top merchants:** ranked rows `# · 商户 · ¥金额`.
- Deliberately avoids dense financial charts; each block is one card.

---

## 6. Component Specification

| Component | Purpose | Key props / states | Notes |
| --- | --- | --- | --- |
| `TabBar` | 5-tab navigation | active tab; center FAB (`记账`) raised, brand circle; badge on 待确认 | 64px, blurred, safe-area padding |
| `NavLargeTitle` | page title + status | title; llm/bridge pills | sticky, translucent blur |
| `HeroSummary` | monthly big numbers | expense, income, balance, count | brand gradient, radius 20 |
| `Banner` | inline callout | tone (blue/green), text, action | pending deep-link |
| `TxRow` | transaction line | icon, merchant, sub, amount, direction | 40px avatar, divider |
| `Chip` | status/label tag | tone: green/amber/blue/neutral | pill, 11px |
| `SwipeCard` | inbox item | tx, onConfirm, onEdit; drag dx | pointer events, ±140 clamp, ±96 threshold |
| `ConfidenceBar` | AI confidence | percent; green≥80 else orange | 6px |
| `BottomSheet` | edit/paste modal | open, onClose, children | radius 20 top, scrim 35% |
| `CategoryGrid` | icon picker | categories, selected, onSelect | 5-col, active = brand-weak + inset ring |
| `Keypad` | numeric entry | onKey (0-9, ., ⌫) | 3-col, press scale .96 |
| `AmountDisplay` | entry focus | amount string, currency | 52px/800 |
| `DirectionToggle` | expense/income | value, onChange | pill segmented |
| `Donut` | category share | data[{category,percent}] | SVG dasharray |
| `Bar` | value bars | value, max | brand fill |
| `AICard` | NL summary | summary, source | soft green gradient |
| `ListRow` | settings row | left, right/action | 14px divider |
| `Toast` | transient feedback | message | above tabbar, pill |

Interaction rules: high-frequency actions are single-thumb reachable and ≤2 taps
(swipe-confirm is effectively 1 gesture). Animations 200–300ms, soft easing, no
flashy effects, no decorative gradients beyond brand surfaces.

---

## 7. Design Tokens

```jsonc
// color
{
  "color.brand":        "#2BC673",
  "color.brand.weak":   "#E7F8EF",
  "color.bg":           "#F7F8FA",
  "color.card":         "#FFFFFF",
  "color.text":         "#1F2937",
  "color.muted":        "#6B7280",
  "color.line":         "#EEF0F3",
  "status.income":      "#2BC673",  // 收入 绿
  "status.expense":     "#F59E0B",  // 支出 橙
  "status.danger":      "#EF4444",  // 异常 红
  "status.pending":     "#3B82F6",  // 待确认 蓝
  "chart.palette":      ["#2BC673","#3B82F6","#F59E0B","#A78BFA","#EF4444","#14B8A6","#F472B6","#64748B"]
}

// radius
{ "radius.lg": 20, "radius.md": 14, "radius.sm": 10, "radius.pill": 999 }

// spacing (4pt scale)
{ "space.1": 4, "space.2": 8, "space.3": 12, "space.4": 16, "space.5": 20, "space.6": 24 }

// elevation
{
  "shadow.1": "0 1px 2px rgba(16,24,40,.04), 0 4px 16px rgba(16,24,40,.06)",
  "shadow.2": "0 8px 24px rgba(16,24,40,.10)"
}

// typography (SF Pro / PingFang SC)
{
  "font.display": { "size": 40, "weight": 800, "tracking": "-0.02em" },
  "font.amount":  { "size": 52, "weight": 800 },
  "font.title":   { "size": 22, "weight": 700 },
  "font.body":    { "size": 15, "weight": 400 },
  "font.caption": { "size": 12, "weight": 400, "color": "muted" }
}

// motion
{ "motion.duration": "240ms", "motion.ease": "cubic-bezier(.22,.61,.36,1)" }

// layout
{ "layout.maxWidth": 440, "tabbar.height": 64 }
```

These tokens are the source of truth and are mirrored in
`frontend/src/styles.css` (`:root` custom properties).

---

## 8. Flutter Widget Structure

A parallel native implementation would map 1:1 to the tokens above.

```
MaterialApp (theme: AppTheme.fromTokens)
└── HomeShell (StatefulWidget)                     // bottom nav host
    ├── Scaffold
    │   ├── body: IndexedStack(index: currentTab)
    │   │   ├── HomeTab
    │   │   │   ├── LargeTitleHeader(title: '概览', trailing: StatusPills)
    │   │   │   ├── HeroSummaryCard(expense, income, balance)
    │   │   │   ├── PendingBanner(count, onTap)
    │   │   │   └── RecentList(children: [TxRow...])
    │   │   ├── PendingTab
    │   │   │   ├── SummaryBar(count, needsAttention)
    │   │   │   └── ListView(
    │   │   │         children: [
    │   │   │           Dismissible(                 // swipe gestures
    │   │   │             key, 
    │   │   │             background: ConfirmBg(),   // green 确认
    │   │   │             secondaryBackground: EditBg(), // blue 修改
    │   │   │             confirmDismiss: (dir) => dir == start ? confirm() : openEditSheet(),
    │   │   │             child: InboxCard(tx, ConfidenceBar),
    │   │   │           ) ...
    │   │   │         ])
    │   │   ├── EntryTab
    │   │   │   ├── AmountDisplay(amount)
    │   │   │   ├── DirectionToggle(value)
    │   │   │   ├── CategoryGrid(categories, selected)
    │   │   │   ├── MerchantField()
    │   │   │   ├── Keypad(onKey)
    │   │   │   └── ActionRow([VoiceButton, PasteButton, SaveButton])
    │   │   ├── StatsTab
    │   │   │   ├── MonthPicker()
    │   │   │   ├── AiInsightCard(summary)
    │   │   │   ├── CategoryDonut(CustomPainter)     // dasharray -> arcs
    │   │   │   ├── CategoryBars()
    │   │   │   ├── TrendBars()
    │   │   │   └── TopMerchants()
    │   │   └── MineTab
    │   │       ├── SystemStatusCard(llm, bridge, retrySync)
    │   │       ├── CategoryManager()
    │   │       ├── MerchantMappingList()
    │   │       └── OpenActualTile()
    │   └── bottomNavigationBar: AppTabBar(
    │         items: [Home, Pending(badge), EntryFab(center), Stats, Mine])
    └── Providers / State
        ├── ApiClient (dio)         -> /api endpoints
        ├── TransactionsController  (pending queue, confirm, edit)
        ├── StatsController         (stats, monthly report)
        └── SettingsController      (categories, mappings, health)

// Bottom sheets
showModalBottomSheet -> EditSheet(CategoryGrid + AmountField + [Save, SaveAndConfirm])
showModalBottomSheet -> PasteSheet(TextField + ParseButton -> /ingest/text)

// Reusable widgets: BrandCard, Chip, ConfidenceBar, PillToggle, Toast(SnackBar)
// Theme tokens: ColorScheme(seed: #2BC673), radii 20/14/10, AnimationDuration 240ms.
```

The React implementation in `frontend/` is the runnable reference; the Flutter
tree above is a drop-in structure for a native app sharing the same tokens and
the same backend API.
