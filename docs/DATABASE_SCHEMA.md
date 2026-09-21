# PostgreSQL schema (production target)

```sql
CREATE TABLE agents (id text PRIMARY KEY, mission_id uuid, state text, x double precision, y double precision, battery numeric, last_seen timestamptz, created_at timestamptz DEFAULT now());
CREATE TABLE missions (id uuid PRIMARY KEY, scenario text, status text, started_at timestamptz, ended_at timestamptz);
CREATE TABLE tasks (id text PRIMARY KEY, mission_id uuid, pickup_x int, pickup_y int, dropoff_x int, dropoff_y int, priority text, status text, assigned_agent text REFERENCES agents(id));
CREATE TABLE recovery_events (id uuid PRIMARY KEY, mission_id uuid, failed_agent text, replacement_agent text, recovery_seconds numeric, reason text, created_at timestamptz DEFAULT now());
CREATE TABLE benchmark_runs (id uuid PRIMARY KEY, scenario text, coordination_mode text, agents int, success_rate numeric, recovery_seconds numeric, collision_rate numeric, overhead numeric, delivery_seconds numeric);
```

The current demo uses deterministic in-memory state because no PostgreSQL connection string is present in the protected environment. Keep migrations in Alembic when enabling production persistence.