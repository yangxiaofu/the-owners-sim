# Transaction System Walkthrough - Simple Terms

## What Are Transactions?

**Transactions** are records of every roster move that happens in your NFL simulation:
- Drafting a player → DRAFT transaction
- Signing a free agent → UFA_SIGNING transaction
- Cutting a player → RELEASE transaction
- Franchise tagging → FRANCHISE_TAG transaction
- Trading → TRADE transaction
- etc.

Think of it like a **transaction history** in your bank account, but for player moves.

## How It Works (5 Simple Steps)

### Step 1: App Starts - Create the Transaction Table

**File: `main.py` (lines 39-57)**

When you start the app, it runs this code:

```python
# Read the migration SQL file
migration_path = "../../src/database/migrations/003_player_transactions_table.sql"
conn = sqlite3.connect(db_path)
conn.executescript(migration_sql)  # Creates the player_transactions table
conn.commit()
```

**What happens:**
- Reads a SQL file that defines the `player_transactions` table structure
- Creates the table in your SQLite database (if it doesn't exist)
- Table has columns for: player_id, team_id, transaction_type, date, details, etc.

**Result:** You now have an empty table ready to record transactions.

---

### Step 2: Something Happens During Simulation

**Example:** User signs a free agent in the offseason

```
User clicks: "Sign Patrick Mahomes to 5-year, $50M contract"
```

---

### Step 3: An Event Gets Created and Executed

**File: `events/free_agency_events.py` → `UFASigningEvent`**

When you sign a player, the system creates a **UFASigningEvent** object:

```python
event = UFASigningEvent(
    team_id=7,  # Detroit Lions
    player_id=12345,  # Patrick Mahomes
    contract_years=5,
    contract_value=50000000,
    signing_bonus=10000000,
    season=2025,
    event_date=Date(2025, 3, 15),
    dynasty_id="my_dynasty",
    transaction_logger=TransactionLogger()  # LOGGER INJECTED HERE
)

# Execute the event (signs the player, creates contract in database)
result = event.simulate()
```

**What happens:**
- Event creates the contract in the database
- Event updates the salary cap
- Event updates the roster
- **Event calls the TransactionLogger** to record the transaction

---

### Step 4: TransactionLogger Saves the Transaction

**File: `src/persistence/transaction_logger.py`**

The event calls this method:

```python
transaction_logger.log_from_event_result(
    event_result=result,  # Contains player_id, team_id, contract details
    dynasty_id="my_dynasty",
    season=2025
)
```

**What the logger does (automatic):**

#### 4a. Extract Data from EventResult
```python
# Logger reads the event result and extracts:
player_id = 12345
player_name = "Patrick Mahomes"
team_id = 7
transaction_type = "UFA_SIGNING"
transaction_date = "2025-03-15"
details = {
    "contract_years": 5,
    "contract_value": 50000000,
    "signing_bonus": 10000000
}
```

#### 4b. Insert Into Database
```python
conn.execute('''
    INSERT INTO player_transactions (
        dynasty_id, season, transaction_type,
        player_id, player_name, to_team_id,
        transaction_date, details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    "my_dynasty",
    2025,
    "UFA_SIGNING",
    12345,
    "Patrick Mahomes",
    7,
    "2025-03-15",
    '{"contract_years": 5, "contract_value": 50000000}'  # JSON
))

conn.commit()
```

**Result:** Transaction is now saved in the database with a unique `transaction_id`.

---

### Step 5: You Can Query Transaction History

**File: `src/persistence/transaction_api.py` (or UI code)**

Later, you can retrieve transactions:

```python
# Get all transactions for your dynasty
transactions = transaction_api.get_transactions(
    dynasty_id="my_dynasty",
    season=2025
)

# Result:
[
    {
        "transaction_id": 1,
        "transaction_type": "UFA_SIGNING",
        "player_name": "Patrick Mahomes",
        "to_team_id": 7,
        "transaction_date": "2025-03-15",
        "details": {"contract_years": 5, "contract_value": 50000000}
    },
    # ... more transactions
]
```

---

## Visual Flow Diagram

```
┌─────────────────┐
│  main.py        │
│  (App Starts)   │
└────────┬────────┘
         │
         │ 1. Create player_transactions table
         │
         ▼
┌─────────────────────────────────┐
│  SQLite Database                │
│  ┌───────────────────────────┐  │
│  │ player_transactions table │  │
│  │ (empty)                   │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
         │
         │ 2. User signs free agent
         │
         ▼
┌─────────────────┐
│  UI/Controller  │
│  "Sign Player"  │
└────────┬────────┘
         │
         │ 3. Create event
         │
         ▼
┌────────────────────┐
│  UFASigningEvent   │
│  .simulate()       │
└────────┬───────────┘
         │
         │ 4. Execute event
         │    - Create contract
         │    - Update cap
         │    - Update roster
         │
         │ 5. Call logger
         │
         ▼
┌──────────────────────┐
│  TransactionLogger   │
│  .log_from_event()   │
└────────┬─────────────┘
         │
         │ 6. Extract data from event
         │    - player_id, team_id, date
         │    - contract details
         │
         │ 7. INSERT INTO database
         │
         ▼
┌─────────────────────────────────┐
│  SQLite Database                │
│  ┌───────────────────────────┐  │
│  │ player_transactions       │  │
│  │                           │  │
│  │ ID | Type       | Player  │  │
│  │ 1  | UFA_SIGN   | Mahomes │  │  ← NEW ROW
│  └───────────────────────────┘  │
└─────────────────────────────────┘
         │
         │ 8. User views transaction history
         │
         ▼
┌────────────────────┐
│  UI: Transactions  │
│  View              │
│                    │
│  Mar 15: Signed    │
│  Patrick Mahomes   │
│  5yr / $50M        │
└────────────────────┘
```

---

## Types of Transactions Recorded

The system records **14 different transaction types**:

1. **DRAFT** - Player drafted
2. **UDFA_SIGNING** - Undrafted free agent signed
3. **UFA_SIGNING** - Unrestricted free agent signed
4. **RFA_SIGNING** - Restricted free agent signed
5. **RELEASE** - Player released
6. **WAIVER_CLAIM** - Player claimed off waivers
7. **TRADE** - Player traded
8. **ROSTER_CUT** - Player cut from roster
9. **PRACTICE_SQUAD_ADD** - Added to practice squad
10. **PRACTICE_SQUAD_REMOVE** - Removed from practice squad
11. **PRACTICE_SQUAD_ELEVATE** - Elevated to active roster
12. **FRANCHISE_TAG** - Player franchise tagged
13. **TRANSITION_TAG** - Player transition tagged
14. **RESTRUCTURE** - Contract restructured

---

## Key Design Principles

### 1. Dynasty Isolation
Every transaction has a `dynasty_id`, so multiple save files don't interfere:

```sql
WHERE dynasty_id = 'my_dynasty'  -- Only shows transactions for this save
```

### 2. Automatic Logging
You don't manually log transactions - events do it automatically:

```python
# Event handles everything
event = UFASigningEvent(..., transaction_logger=logger)
event.simulate()  # Signing + logging happen together
```

### 3. Event Integration
Transactions are linked to the events that created them:

```sql
SELECT * FROM player_transactions WHERE event_id = 'evt_123'
-- Shows the transaction from that specific event
```

### 4. JSON Details Storage
Each transaction can store custom details as JSON:

```json
{
  "contract_years": 5,
  "contract_value": 50000000,
  "signing_bonus": 10000000,
  "avg_per_year": 10000000
}
```

This allows flexible storage without adding 100 columns to the table.

---

## Real-World Example: Franchise Tag Flow

Let's walk through franchise tagging a player:

### Code Execution
```python
# 1. User action: "Franchise Tag Patrick Mahomes"
from events.contract_events import FranchiseTagEvent

# 2. Event created
event = FranchiseTagEvent(
    team_id=7,
    player_id=12345,
    player_name="Patrick Mahomes",
    player_position="QB",
    season=2025,
    event_date=Date(2025, 3, 4),
    dynasty_id="my_dynasty",
    transaction_logger=TransactionLogger()
)

# 3. Event executes
result = event.simulate()
# - Creates 1-year contract at franchise tag salary
# - Updates salary cap
# - Calls transaction logger

# 4. Logger extracts data
tx_data = {
    "transaction_type": "FRANCHISE_TAG",
    "player_id": 12345,
    "player_name": "Patrick Mahomes",
    "team_id": 7,
    "transaction_date": "2025-03-04",
    "details": {
        "tag_type": "exclusive",
        "tag_salary": 45000000,
        "cap_impact": 45000000
    }
}

# 5. Logger saves to database
transaction_id = logger.log_transaction(**tx_data)
# Returns: 42 (new transaction ID)
```

### Database Result
```sql
SELECT * FROM player_transactions WHERE transaction_id = 42;

-- Result:
transaction_id: 42
dynasty_id: "my_dynasty"
season: 2025
transaction_type: "FRANCHISE_TAG"
player_id: 12345
player_name: "Patrick Mahomes"
to_team_id: 7
transaction_date: "2025-03-04"
details: '{"tag_type":"exclusive","tag_salary":45000000,"cap_impact":45000000}'
contract_id: 87
event_id: "evt_franchise_tag_12345"
created_at: "2025-03-04 14:23:17"
```

### UI Display
```
Transaction History - 2025 Season

Mar 4, 2025
FRANCHISE TAG: Patrick Mahomes (QB)
Team: Detroit Lions
Tag Salary: $45,000,000
Contract: 1 year, exclusive franchise tag
```

---

## Summary: Why This Matters

**Without transaction logging:**
- No record of roster changes
- Can't see signing history
- Can't track player movement between teams
- No audit trail

**With transaction logging:**
- ✅ Complete history of every roster move
- ✅ See when/how every player was acquired
- ✅ Track contract history
- ✅ Audit trail for debugging ("Why is my cap wrong?")
- ✅ Can build features like "Team History" views
- ✅ Can answer "How did I get this player?"

It's like having **receipts for every personnel decision** you make in your dynasty.

---

## Where To Look In The Code

- **Table Creation**: `main.py` lines 39-57
- **Table Schema**: `src/database/migrations/003_player_transactions_table.sql`
- **Logger Class**: `src/persistence/transaction_logger.py`
- **Event Integration**: `events/free_agency_events.py`, `events/contract_events.py`, etc.
- **Query API**: `src/persistence/transaction_api.py`
- **Demo**: `demo/transaction_logging_demo/offseason_transaction_workflow.py`
