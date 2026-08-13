# Section 7 — Database & Storage Questions

---

**Q1. Why did you choose SQLite for this project?**
**A1.** Three reasons. First, zero setup — SQLite requires no server process, no connection string, no credentials. The database is a single file. For a portfolio project and MVP, this is a massive productivity win. Second, async support via aiosqlite — I can make all database calls non-blocking. Third, the query patterns here are simple CRUD — insert meeting, retrieve by ID, update summary field. SQLite handles that easily. The tradeoff is that SQLite doesn't handle concurrent writes well, so it won't scale to multiple API worker processes. That's a known, accepted limitation for this stage.

**What the interviewer is testing:** Can you articulate why you made a storage choice?
**Possible follow-up:** At what point would you migrate to PostgreSQL and how would you do it?

---

**Q2. What do you store in the database and how is it structured?**
**A2.** One main table: `meetings`. It has columns for `id` (UUID string, primary key), `title` (nullable text), `transcript` (the raw input), `summary_json` (the full structured analysis serialised as JSON text), `status` (enum-like: "uploaded" or "summarised"), and `created_at` (ISO timestamp). I deliberately store the summary as a JSON string rather than normalised columns because the schema evolves frequently during development, and normalising action items into a separate table adds join complexity for minimal benefit at this scale. In production I'd normalise action items into their own table for proper querying and indexing.

**What the interviewer is testing:** Do you understand schema design tradeoffs?
**Possible follow-up:** How would you efficiently query for all high-priority action items across all meetings?

---

**Q3. How do you initialise the database on startup?**
**A3.** I have an `init_db()` async function in `app/config/database.py`. It connects to the SQLite file and runs a `CREATE TABLE IF NOT EXISTS` statement. The `IF NOT EXISTS` makes it idempotent — safe to call on every startup without wiping data. `init_db()` is called inside the FastAPI lifespan context manager before the app starts accepting requests. I also call it in tests via a session-scoped `autouse` fixture — this ensures the table exists before any test runs, regardless of test order.

**What the interviewer is testing:** Do you handle database initialisation properly in both app and test contexts?
**Possible follow-up:** How would you handle database schema migrations in production?

---

**Q4. [Advanced] How would you migrate from SQLite to PostgreSQL?**
**A4.** The key design decision I made is that all database logic is isolated in `app/services/meeting_service.py` — routes never touch the database directly. So the migration only requires changing the service layer. I'd replace aiosqlite with asyncpg or SQLAlchemy async. The SQL queries are standard enough that most would work unchanged. The main differences: PostgreSQL uses `$1` placeholders instead of `?`, UUID columns are native, and JSON columns are first-class. I'd also add Alembic for migrations — SQLite's `CREATE TABLE IF NOT EXISTS` approach doesn't work when you need to alter existing tables without data loss.

**What the interviewer is testing:** Did you design for future change, or is the database tightly coupled?
**Possible follow-up:** Would you use an ORM like SQLAlchemy or raw SQL? What are the tradeoffs?

---

**Q5. How is ChromaDB data stored separately from SQLite?**
**A5.** They store completely different things. SQLite stores meeting metadata, transcripts, and structured summaries — relational data with known schemas. ChromaDB stores vector embeddings of document chunks — high-dimensional float arrays with associated metadata. ChromaDB persists its data to a local directory (`./chroma_db/`) in its own binary format. They're separate systems because their data types, query patterns, and access patterns are fundamentally different. The only link between them is the `source` metadata field in ChromaDB, which stores the filename of the ingested document.

**What the interviewer is testing:** Do you understand why different storage systems are used for different data types?
**Possible follow-up:** What would you store in Redis if you added it to this stack?

---

**Q6. [Tricky] The summary is stored as a JSON string in SQLite. What problems could that cause?**
**A6.** Several potential issues. First, you can't query inside it efficiently — finding all meetings where Bob has an action item requires loading all summaries and parsing in Python. Second, if the JSON schema changes, old summaries in the database have the old schema — you need a migration or a version field to handle that gracefully. Third, JSON text search is not indexed. In production I'd split this: core summary fields (summary text, status) stay in the meetings table, action items go into an `action_items` table with `meeting_id` foreign key, risks into a `risks` table, etc. This enables proper SQL queries and indexing.

**What the interviewer is testing:** Do you understand the tradeoffs of JSON-in-SQL storage?
**Possible follow-up:** How would you migrate existing JSON summaries to normalised tables without downtime?
