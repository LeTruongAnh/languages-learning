# Mobile Vocabulary Learning App - Technical Specification

Version: 1.0  
Target: Mobile app + backend API first, web companion later  
Stack recommendation: Flutter + FastAPI + PostgreSQL  
MVP principle: Language-module first, vocabulary and sentence combined, no cross-language mixed session by default

---

## 1. Product Summary

This system replaces the current Google Sheets + Apps Script vocabulary workflow with a proper mobile-first learning product.

The app helps each user maintain a personal vocabulary and sentence learning path across multiple languages. The first supported languages are Chinese and English. The architecture must allow adding Japanese, Korean, French, or other languages later without changing the database schema.

Core idea:

```text
Home
├── Chinese
│   └── Vocabulary + Sentence in one language session
├── English
│   └── Vocabulary + Sentence in one language session
├── Hard Items
├── Dashboard
└── Settings
```

MVP should not default to a mixed Chinese + English session. Each study session should focus on one language.

---

## 2. Product Decisions

### 2.1 Language Module First

The Home screen should show one card per active language.

Example:

```text
Chinese
Due: 12 · New: 8 · Vocab: 14 · Sentences: 6
[Start Chinese]

English
Due: 10 · New: 10 · Vocab: 15 · Sentences: 5
[Start English]
```

This avoids forcing the user to choose between too many modules like:

```text
Chinese Vocabulary
Chinese Sentences
English Vocabulary
English Sentences
```

### 2.2 Vocabulary And Sentence Combined

Inside each language module, vocabulary and sentences are combined into one session.

Example Chinese session:

```text
14 vocabulary items
6 sentence items
20 total items
```

The app should not shuffle vocabulary and sentences completely. It should order items by block:

```text
1. Vocabulary review
2. Vocabulary new
3. Sentence review
4. Sentence new
```

Default ordering:

```text
VOCAB_FIRST_WITH_REVIEW_PRIORITY
```

### 2.3 No Cross-Language Mixed Session In MVP

Do not mix Chinese and English in the same study session in MVP.

Reasons:

- Better focus.
- More stable TTS voice.
- Less context switching.
- Easier backend and mobile UX.
- Better for languages with different writing systems.

Mixed review can be added later as an advanced feature.

### 2.4 Each User Has Personal Learning Data

For MVP, each user owns their own `study_items`.

Use:

```text
study_items.user_id
```

Do not split into shared `content_items` and `user_progress` in MVP. That model is better later if the product adds shared courses or public decks.

With up to 10 users, database size is not a problem if indexed properly.

---

## 3. Target Users And Use Cases

### 3.1 Target Users

- Self-learners studying multiple languages.
- Users who collect their own vocabulary and example sentences.
- Users who want a personal spaced repetition workflow without Anki complexity.
- Early usage: 1-10 private users.

### 3.2 Core Use Cases

1. User logs in.
2. User opens Home and sees active language modules.
3. User chooses Chinese or English.
4. App creates or resumes today's language session.
5. User studies cards one by one.
6. User marks each item: PASS, FAIL, SKIP.
7. Backend updates review state.
8. User checks dashboard progress.
9. User imports or edits items through web/admin tools later.

---

## 4. MVP Scope

### 4.1 Mobile MVP

Required:

- Login.
- Home with language cards.
- Language study session.
- Vocabulary + sentence cards.
- PASS / FAIL / SKIP.
- TTS reading.
- Session progress.
- Basic dashboard.
- Basic settings.
- Hard Items.

Optional for MVP:

- Offline queue.
- CSV import on mobile.
- Advanced charts.
- Mixed language session.

### 4.2 Backend MVP

Required:

- Auth.
- Users.
- Languages.
- Language settings.
- Study items.
- Study sessions.
- Study session items.
- Review submission.
- Dashboard summary.
- Import/export foundation.

Optional for MVP:

- Shared courses.
- Public decks.
- Admin role management.
- AI-generated examples.
- Push notifications.

### 4.3 Web Companion

The website is useful but can come after mobile MVP.

Web should focus on:

- Bulk item management.
- Import CSV/XLSX.
- Edit items.
- Advanced settings.
- Dashboard.
- Export backup.

Recommended web stack:

```text
React/Vite static web
```

Avoid Next.js SSR on small VPS unless needed.

---

## 5. Modern UI/UX Direction

### 5.1 Design Principles

- Mobile-first.
- Clean, focused, low cognitive load.
- One primary action per screen.
- Language cards are the main navigation.
- Study screen should feel fast and calm.
- Avoid spreadsheet-like UI on mobile.
- Dashboard should be simple, not overloaded.

### 5.2 Visual Style

Recommended style:

- Light background.
- Rounded but not overly soft cards.
- Strong typography for the study item.
- Clear PASS / FAIL / SKIP buttons.
- Language-specific accent colors.
- Large tap targets.

Example accents:

| Language | Accent |
|---|---|
| Chinese | Red / warm rose |
| English | Blue / green |
| Hard Items | Orange |
| Review | Purple |

### 5.3 Mobile Navigation

Use bottom navigation:

```text
Home
Study
Items
Dashboard
Settings
```

MVP can simplify to:

```text
Home
Dashboard
Settings
```

Study is opened from a language card.

### 5.4 Home Screen

Home should show:

- Greeting.
- Today's total progress.
- Language cards.
- Hard Items card.
- Quick Settings shortcut.

Language card fields:

- Language name.
- Due count.
- New count.
- Today's target.
- Vocabulary count.
- Sentence count.
- Progress percent.
- Start / Continue button.

Example:

```text
Chinese
8 / 20 completed today
Due 12 · New 8
Vocabulary 14 · Sentences 6
[Continue]
```

### 5.5 Study Screen

Study card should show:

- Current index: `5 / 20`.
- Item type: Vocabulary or Sentence.
- Study type: New or Review.
- Difficulty.
- Hard level.
- Main text.
- Pronunciation.
- Vietnamese meaning.
- Example and translation.
- TTS button.
- Show / hide meaning.
- PASS / FAIL / SKIP.

Recommended layout:

```text
Chinese · Vocabulary · Review
5 / 20

你好
nǐ hǎo

[Show meaning]

Xin chào
Example...

[FAIL] [SKIP] [PASS]
```

### 5.6 TTS UX

TTS should:

- Use language-specific voice.
- Read main text by default.
- Support replay.
- Optionally auto-read next card.

Settings:

```json
{
  "autoSpeakOnCardOpen": true,
  "speakExample": false,
  "speechRate": 0.9,
  "speechVolume": 1.0
}
```

### 5.7 Dashboard UX

Dashboard MVP should show:

- Today learned.
- PASS / FAIL / SKIP count.
- Pass rate.
- Current streak.
- Due today.
- Hard items count.
- Language breakdown.

Avoid complex charts in MVP. Use simple cards and one weekly trend chart later.

---

## 6. Data Model

### 6.1 Entity Overview

```text
users
languages
language_settings
study_items
study_sessions
study_session_items
review_logs
user_settings
import_batches
```

Do not create separate tables like:

```text
chinese_items
english_items
```

Use generic language records.

---

## 7. PostgreSQL Schema

Use UUID primary keys.

### 7.1 users

```sql
create table users (
  id uuid primary key,
  email varchar(255) not null unique,
  password_hash text not null,
  display_name varchar(120),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 7.2 languages

Each user can have their own active language list.

```sql
create table languages (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  code varchar(20) not null,
  name varchar(80) not null,
  native_name varchar(120),
  tts_lang varchar(20) not null,
  accent_color varchar(20),
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, code)
);
```

Examples:

| code | name | tts_lang |
|---|---|---|
| zh | Chinese | zh-CN |
| en | English | en-US |
| ja | Japanese | ja-JP |

### 7.3 language_settings

```sql
create table language_settings (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  language_id uuid not null references languages(id) on delete cascade,
  daily_limit int not null default 20,
  vocabulary_ratio numeric(4,3) not null default 0.700,
  sentence_ratio numeric(4,3) not null default 0.300,
  new_ratio numeric(4,3) not null default 0.600,
  review_ratio numeric(4,3) not null default 0.400,
  times_limit int not null default 3,
  sentence_times_limit int not null default 3,
  review_intervals int[] not null default array[1,3,7],
  sentence_review_intervals int[] not null default array[1,3,7],
  difficulty_filter text[] not null default array['ALL'],
  sentence_difficulty_filter text[] not null default array['ALL'],
  topic_filter text[] not null default array['ALL'],
  situation_filter text[] not null default array['ALL'],
  frequency_filter text[] not null default array['ALL'],
  include_passed_items boolean not null default false,
  passed_review_after_days int not null default 100,
  reset_on_fail boolean not null default true,
  avoid_same_day_repeat boolean not null default true,
  sort_mode varchar(30) not null default 'random',
  item_ordering varchar(50) not null default 'VOCAB_FIRST_WITH_REVIEW_PRIORITY',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, language_id)
);
```

### 7.4 study_items

One table stores both vocabulary and sentence items.

```sql
create table study_items (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  language_id uuid not null references languages(id) on delete cascade,
  item_type varchar(20) not null check (item_type in ('VOCABULARY', 'SENTENCE')),
  text text not null,
  pronunciation text,
  vietnamese_meaning text,
  example text,
  example_vietnamese text,
  topic varchar(120),
  situation varchar(120),
  difficulty varchar(40),
  frequency_level varchar(40),
  notes text,
  source varchar(120),
  source_row int,
  last_date_review date,
  next_review_date date,
  times_review int not null default 0,
  passed boolean not null default false,
  wrong_count int not null default 0,
  last_result varchar(20),
  hard_level varchar(30) not null default 'Normal',
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Recommended indexes:

```sql
create index idx_study_items_user_language on study_items(user_id, language_id);
create index idx_study_items_due on study_items(user_id, language_id, next_review_date, passed);
create index idx_study_items_type on study_items(user_id, language_id, item_type);
create index idx_study_items_hard on study_items(user_id, hard_level) where hard_level in ('Hard', 'Very Hard');
create index idx_study_items_archived on study_items(user_id, is_archived);
```

### 7.5 study_sessions

```sql
create table study_sessions (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  language_id uuid references languages(id) on delete set null,
  session_type varchar(40) not null default 'LANGUAGE_DAILY',
  status varchar(30) not null default 'ACTIVE',
  study_date date not null default current_date,
  total_items int not null default 0,
  completed_items int not null default 0,
  pass_count int not null default 0,
  fail_count int not null default 0,
  skip_count int not null default 0,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  updated_at timestamptz not null default now()
);
```

Session types:

```text
LANGUAGE_DAILY
LANGUAGE_EXTRA
LANGUAGE_WEEKLY
HARD_ITEMS
ALL_DUE
```

MVP requires:

```text
LANGUAGE_DAILY
LANGUAGE_EXTRA
HARD_ITEMS
```

### 7.6 study_session_items

```sql
create table study_session_items (
  id uuid primary key,
  session_id uuid not null references study_sessions(id) on delete cascade,
  study_item_id uuid not null references study_items(id) on delete cascade,
  position int not null,
  planned_bucket varchar(40) not null,
  result varchar(20),
  applied_at timestamptz,
  created_at timestamptz not null default now(),
  unique(session_id, study_item_id)
);
```

Do not copy all item text here. Join with `study_items` when reading.

### 7.7 review_logs

```sql
create table review_logs (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  language_id uuid references languages(id) on delete set null,
  session_id uuid references study_sessions(id) on delete set null,
  study_item_id uuid references study_items(id) on delete set null,
  result varchar(20) not null check (result in ('PASS', 'FAIL', 'SKIP')),
  old_times_review int,
  new_times_review int,
  old_passed boolean,
  new_passed boolean,
  old_wrong_count int,
  new_wrong_count int,
  old_hard_level varchar(30),
  new_hard_level varchar(30),
  old_next_review_date date,
  new_next_review_date date,
  self_note text,
  created_at timestamptz not null default now()
);
```

Indexes:

```sql
create index idx_review_logs_user_date on review_logs(user_id, created_at desc);
create index idx_review_logs_user_language_date on review_logs(user_id, language_id, created_at desc);
create index idx_review_logs_item on review_logs(study_item_id, created_at desc);
```

### 7.8 user_settings

```sql
create table user_settings (
  id uuid primary key,
  user_id uuid not null unique references users(id) on delete cascade,
  timezone varchar(80) not null default 'Asia/Ho_Chi_Minh',
  auto_speak_on_card_open boolean not null default true,
  speak_example boolean not null default false,
  speech_rate numeric(3,2) not null default 0.90,
  speech_volume numeric(3,2) not null default 1.00,
  theme varchar(30) not null default 'system',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 7.9 import_batches

```sql
create table import_batches (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  language_id uuid references languages(id) on delete set null,
  file_name text,
  status varchar(30) not null default 'PENDING',
  total_rows int not null default 0,
  imported_rows int not null default 0,
  failed_rows int not null default 0,
  error_summary text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);
```

---

## 8. Review Algorithm

### 8.1 Result Rules

When user submits PASS:

```text
times_review += 1
passed = times_review >= times_limit
wrong_count unchanged
hard_level recalculated from wrong_count
next_review_date = null if passed else today + review_interval[times_review]
last_result = PASS
```

When user submits FAIL:

```text
times_review = 0 if reset_on_fail else unchanged
passed = false
wrong_count += 1
hard_level recalculated
next_review_date = tomorrow
last_result = FAIL
```

When user submits SKIP:

```text
Do not update progress fields.
Only write review log and session item result.
```

### 8.2 Hard Level

```text
wrong_count >= 3  => Very Hard
wrong_count >= 2  => Hard
else              => Normal
```

### 8.3 Review Intervals

Default:

```text
[1, 3, 7]
```

For vocabulary and sentence, settings can differ:

```text
review_intervals
sentence_review_intervals
```

---

## 9. Session Creation Algorithm

### 9.1 Create Daily Language Session

Endpoint:

```http
POST /api/languages/{languageId}/study-sessions/daily
```

Pseudo-code:

```ts
async function createLanguageDailySession(userId, languageId) {
  settings = await getLanguageSettings(userId, languageId)
  today = currentDateInUserTimezone(userId)

  existing = await findActiveSession(userId, languageId, today, 'LANGUAGE_DAILY')
  if (existing) return existing

  vocabLimit = round(settings.dailyLimit * settings.vocabularyRatio)
  sentenceLimit = settings.dailyLimit - vocabLimit

  vocabSelected = await pickItems({
    userId,
    languageId,
    itemType: 'VOCABULARY',
    limit: vocabLimit,
    newRatio: settings.newRatio,
    settings
  })

  sentenceSelected = await pickItems({
    userId,
    languageId,
    itemType: 'SENTENCE',
    limit: sentenceLimit,
    newRatio: settings.newRatio,
    settings
  })

  arranged = arrangeItems(vocabSelected, sentenceSelected, settings.itemOrdering)

  session = await createSession(userId, languageId, 'LANGUAGE_DAILY', arranged.length)
  await createSessionItems(session.id, arranged)

  return sessionWithItems(session.id)
}
```

### 9.2 Candidate Rules

Candidate must match:

- `user_id`
- `language_id`
- `item_type`
- not archived
- difficulty filter
- topic filter
- situation filter for sentences
- frequency filter
- not passed unless include passed is true
- due for review or new
- not already studied today if avoid same-day repeat is true

### 9.3 New vs Review

New:

```text
times_review = 0
passed = false
last_date_review is null
```

Review:

```text
passed = false
next_review_date <= today
```

### 9.4 Selection Ratio

For each item type:

```text
newLimit = round(limit * newRatio)
reviewLimit = limit - newLimit
```

If one bucket is not enough, fill remaining slots from the other bucket.

### 9.5 Ordering

For default `VOCAB_FIRST_WITH_REVIEW_PRIORITY`:

```text
1. VOCABULARY REVIEW
2. VOCABULARY NEW
3. SENTENCE REVIEW
4. SENTENCE NEW
```

---

## 10. Backend API

Base path:

```text
/api
```

### 10.1 Auth

```http
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

Login response:

```json
{
  "accessToken": "...",
  "refreshToken": "...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "displayName": "Phong"
  }
}
```

### 10.2 Languages

```http
GET    /languages
POST   /languages
GET    /languages/{languageId}
PATCH  /languages/{languageId}
DELETE /languages/{languageId}
```

`DELETE` should soft-disable language by default:

```text
is_active = false
```

### 10.3 Language Settings

```http
GET   /languages/{languageId}/settings
PATCH /languages/{languageId}/settings
```

### 10.4 Study Items

```http
GET    /study-items
POST   /study-items
GET    /study-items/{itemId}
PATCH  /study-items/{itemId}
DELETE /study-items/{itemId}
```

Query params:

```text
languageId
itemType
difficulty
topic
situation
hardLevel
passed
dueOnly
search
page
pageSize
```

### 10.5 Study Sessions

```http
POST /languages/{languageId}/study-sessions/daily
POST /languages/{languageId}/study-sessions/extra
GET  /languages/{languageId}/study-sessions/current
GET  /study-sessions/{sessionId}
POST /study-sessions/{sessionId}/items/{sessionItemId}/review
POST /study-sessions/{sessionId}/complete
```

Review request:

```json
{
  "result": "PASS",
  "selfNote": "optional note"
}
```

Review response:

```json
{
  "sessionItemId": "uuid",
  "studyItemId": "uuid",
  "result": "PASS",
  "newProgress": {
    "timesReview": 2,
    "passed": false,
    "wrongCount": 0,
    "hardLevel": "Normal",
    "nextReviewDate": "2026-07-04"
  },
  "sessionProgress": {
    "completedItems": 5,
    "totalItems": 20,
    "passCount": 4,
    "failCount": 1,
    "skipCount": 0
  }
}
```

### 10.6 Hard Items

```http
GET  /hard-items
POST /hard-items/study-sessions
```

### 10.7 Dashboard

```http
GET /dashboard/summary
GET /dashboard/languages
GET /dashboard/history?range=30d
```

### 10.8 Import / Export

```http
POST /imports/study-items
GET  /imports/{batchId}
GET  /exports/study-items.csv
GET  /exports/backup.json
```

---

## 11. Mobile App Architecture

### 11.1 Flutter Recommended Structure

```text
lib/
  main.dart
  app/
    router.dart
    theme.dart
  core/
    api/
    auth/
    storage/
    errors/
  features/
    auth/
      data/
      domain/
      presentation/
    home/
      data/
      domain/
      presentation/
    study/
      data/
      domain/
      presentation/
    items/
      data/
      domain/
      presentation/
    dashboard/
      data/
      domain/
      presentation/
    settings/
      data/
      domain/
      presentation/
```

### 11.2 State Management

Recommended:

```text
Riverpod
```

Acceptable:

```text
Bloc
```

Use one approach consistently.

### 11.3 Offline Strategy

MVP can be online-first.

Phase 2 can add:

- Cache current session.
- Queue review submissions.
- Sync when online.

For MVP, show clear network error states.

### 11.4 Mobile Screens

Required screens:

```text
LoginScreen
HomeScreen
LanguageStudyScreen
StudyCardScreen
SessionCompleteScreen
DashboardScreen
SettingsScreen
HardItemsScreen
ItemListScreen
ItemFormScreen
```

### 11.5 Study Flow

```text
Home
→ Tap Start Chinese
→ GET or POST current daily session
→ Study card 1
→ PASS/FAIL/SKIP
→ Submit review
→ Next card
→ Complete screen
```

### 11.6 TTS In Flutter

Use:

```text
flutter_tts
```

Map language:

| language code | TTS |
|---|---|
| zh | zh-CN |
| en | en-US |
| ja | ja-JP |

TTS should read:

- Vocabulary text for vocabulary item.
- Sentence text for sentence item.

Do not read pronunciation by default.

---

## 12. Backend Architecture

### 12.1 FastAPI Structure

```text
app/
  main.py
  core/
    config.py
    security.py
    database.py
    errors.py
  models/
    user.py
    language.py
    language_setting.py
    study_item.py
    study_session.py
    review_log.py
  schemas/
  repositories/
  services/
    auth_service.py
    language_service.py
    study_item_service.py
    study_session_service.py
    review_service.py
    dashboard_service.py
    import_service.py
  api/
    routes/
      auth.py
      languages.py
      study_items.py
      study_sessions.py
      dashboard.py
      imports.py
```

### 12.2 Service Responsibilities

`study_session_service.py`:

- Create daily session.
- Create extra session.
- Pick candidates.
- Arrange session items.
- Return current active session.

`review_service.py`:

- Apply PASS / FAIL / SKIP.
- Update `study_items`.
- Update `study_session_items`.
- Create `review_logs`.
- Update session counters.

`dashboard_service.py`:

- Today summary.
- Language summary.
- History trend.

### 12.3 Transactions

Review submission must run in one transaction:

```text
update study_item
update study_session_item
insert review_log
update study_session counters
commit
```

If any step fails, rollback.

### 12.4 Idempotency

Avoid double-applying the same session item.

If `study_session_items.applied_at` is not null:

- Return existing state.
- Do not update `study_items` again.

---

## 13. Validation Rules

### 13.1 Study Item

Required:

- `language_id`
- `item_type`
- `text`

For vocabulary:

- `text` is vocabulary.

For sentence:

- `text` is sentence.
- `situation` optional but recommended.

### 13.2 Settings

Validate:

```text
daily_limit between 1 and 200
vocabulary_ratio + sentence_ratio = 1
new_ratio + review_ratio = 1
times_limit between 1 and 20
review_intervals positive integers
```

### 13.3 Review Result

Allowed:

```text
PASS
FAIL
SKIP
```

---

## 14. Import Format

CSV/XLSX columns:

```text
language
item_type
text
pronunciation
vietnamese_meaning
example
example_vietnamese
topic
situation
difficulty
frequency_level
notes
```

For migration from Google Sheets:

| Old column | New field |
|---|---|
| Vocabulary | text, item_type = VOCABULARY |
| Sentence | text, item_type = SENTENCE |
| Pronunciation | pronunciation |
| Vietnamese_Meaning | vietnamese_meaning |
| Example | example |
| Example_Vietnamese | example_vietnamese |
| Topic | topic |
| Situation | situation |
| Difficulty | difficulty |
| Frequency_Level | frequency_level |
| Notes | notes |

---

## 15. Security

MVP:

- JWT access token.
- Refresh token.
- Argon2 password hashing.
- User-scoped queries only.
- Never allow user to access another user's language/item/session.
- Rate limit login.

Every query must include:

```text
user_id = current_user.id
```

---

## 16. Deployment

Recommended VPS for MVP:

```text
2 vCPU
4GB RAM
60-80GB SSD
Ubuntu 24.04
Docker Compose
```

Minimum:

```text
2 vCPU
2GB RAM
40GB SSD
```

Services:

```text
caddy
api
postgres
```

Website should be React/Vite static served by Caddy.

Avoid on small VPS:

- Next.js SSR.
- Redis unless needed.
- Elasticsearch.
- AI model hosting.
- Server-side TTS.

---

## 17. Docker Compose Sketch

```yaml
services:
  api:
    image: vocab-api:latest
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db
    expose:
      - "8000"
    volumes:
      - ./uploads:/app/uploads

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: vocab_app
      POSTGRES_USER: vocab
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "work_mem=4MB"
      - "-c"
      - "maintenance_work_mem=64MB"
      - "-c"
      - "max_connections=30"

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./web-dist:/srv/web
      - caddydata:/data
      - caddyconfig:/config
    depends_on:
      - api

volumes:
  pgdata:
  caddydata:
  caddyconfig:
```

Caddyfile:

```caddyfile
yourdomain.com {
  root * /srv/web
  encode gzip zstd

  handle_path /api/* {
    reverse_proxy api:8000
  }

  handle {
    try_files {path} /index.html
    file_server
  }
}
```

---

## 18. Development Milestones

### Phase 1 - Backend Foundation

- FastAPI project.
- PostgreSQL.
- Alembic.
- Auth.
- Users.
- Languages.
- Language settings.
- Study items CRUD.

### Phase 2 - Study Engine

- Candidate selection.
- Daily language session.
- Extra language session.
- Review submission.
- Review logs.
- Hard items.
- Dashboard summary.

### Phase 3 - Mobile MVP

- Flutter project.
- Login.
- Home language modules.
- Study session UI.
- PASS / FAIL / SKIP.
- TTS.
- Dashboard.
- Settings.

### Phase 4 - Import And Web Companion

- CSV/XLSX import.
- Study item table.
- Bulk edit.
- Export backup.
- React/Vite web.

### Phase 5 - Polish

- Offline queue.
- Better charts.
- Notifications.
- Weekly review.
- Advanced filters.

---

## 19. MVP Acceptance Criteria

Backend is complete when:

- User can register and login.
- User can create Chinese and English languages.
- User can configure each language separately.
- User can create vocabulary and sentence items.
- User can create a daily session per language.
- Session combines vocabulary and sentence by ratio.
- User can submit PASS / FAIL / SKIP.
- Review state updates correctly.
- Logs are created.
- Dashboard returns correct numbers.
- User cannot access another user's data.

Mobile is complete when:

- User can login.
- Home shows Chinese and English cards.
- User can start Chinese session.
- User can study vocabulary and sentence cards.
- TTS reads current card.
- PASS / FAIL / SKIP works.
- Session complete screen appears.
- Dashboard shows today stats.
- Settings can update basic language config.

---

## 20. Final MVP Decision

Build the MVP as:

```text
Flutter mobile app
FastAPI backend
PostgreSQL database
Language-based learning modules
Vocabulary + sentence combined per language
No cross-language mixed session by default
Each user owns personal study items
Generic language schema for future scale
```

This design is simple enough to build quickly, but flexible enough to support more languages and a future web companion.
