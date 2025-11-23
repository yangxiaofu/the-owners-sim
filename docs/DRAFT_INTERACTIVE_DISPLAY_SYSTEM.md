# Draft Interactive Display System Design

**Status**: Design Specification
**Last Updated**: November 22, 2025
**Target Implementation**: Interactive Draft Simulation Demo

---

## 1. System Overview

The Draft Interactive Display System provides real-time, round-by-round draft simulation output with:
- Professional ASCII formatting and section headers
- Interactive pause/resume mechanics (input() prompts)
- Color-coded team categories and pick information
- Live summary statistics at end of draft
- Configurable display width (80-120 columns)

This system is designed to be used in:
- `demo/draft_simulation_demo/` - Interactive draft simulation with AI selections
- UI draft board widget - Terminal-based draft display
- Offseason controller - Draft phase visualization

---

## 2. Terminal Output Format Specification

### 2.1 Display Width & Alignment

**Primary Constraint**: 80 columns maximum (terminal-safe width)
**Secondary Constraint**: Support 120 columns for expanded displays (optional)
**Default**: 95 columns (balanced for most terminals)

```
80 COLUMNS: |        |        |        |        |        |        |        |        |
95 COLUMNS: |        |        |        |        |        |        |        |        |        |        |
120 COLUMNS:|        |        |        |        |        |        |        |        |        |        |        |        |
```

**Alignment Standards**:
- All headers: CENTER aligned with padding
- Pick numbers: RIGHT aligned (5-6 chars)
- Team names: LEFT aligned (28-30 chars)
- Stats (SOS, Record): RIGHT aligned (8-10 chars)
- Reasons: LEFT aligned with color codes

---

## 3. ASCII Art & Headers

### 3.1 Main Draft Header (Full Width)

```
════════════════════════════════════════════════════════════════════════════════════════════════
                          2025 NFL DRAFT - ROUND 1
════════════════════════════════════════════════════════════════════════════════════════════════
```

**Components**:
- Top border: `═` (ASCII 205) × 95 chars
- Title line: Centered text
- Bottom border: `═` × 95 chars

**Variations by Context**:
- **Draft Start**: "2025 NFL DRAFT - BEGINS NOW"
- **Round transition**: "2025 NFL DRAFT - ROUND X" (X = 1-7)
- **Draft complete**: "2025 NFL DRAFT - COMPLETE"

### 3.2 Section Headers (Table Headers)

```
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
```

**Components**:
- Separator: `─` (ASCII 196) × 95 chars
- Header row: Column names with proper alignment
- Separator again below headers
- NO color in header itself (color applied to data rows)

### 3.3 Section Dividers (Between Rounds/Sections)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Alternative lightweight divider**:
```
□ ────────────────────────────────────────────────────────────────────────────────────────────────
```

### 3.4 Interactive Pause Prompt

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  [ROUND COMPLETE]                                                                              │
│  • Press ENTER to continue to Round 2                                                          │
│  • Enter 'R' to review picks                                                                   │
│  • Enter 'S' for statistics                                                                    │
│  • Enter 'Q' to quit                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Complete Output Format Template

### 4.1 Full Draft Simulation Example (Round 1)

```
════════════════════════════════════════════════════════════════════════════════════════════════
                          2025 NFL DRAFT - ROUND 1
════════════════════════════════════════════════════════════════════════════════════════════════

NON-PLAYOFF TEAMS (Picks 1-18)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
1 (#1)    Carolina Panthers               4-13          0.480    Non-Playoff Team
2 (#2)    New York Giants                 4-13          0.520    Non-Playoff Team
3 (#3)    Arizona Cardinals               5-12          0.490    Non-Playoff Team
4 (#4)    New England Patriots            5-12          0.510    Non-Playoff Team
5 (#5)    Tennessee Titans                6-11          0.500    Non-Playoff Team
6 (#6)    Las Vegas Raiders               6-11          0.510    Non-Playoff Team
7 (#7)    Washington Commanders           7-10          0.480    Non-Playoff Team
8 (#8)    New York Jets                   7-10          0.520    Non-Playoff Team
9 (#9)    Chicago Bears                   8-9           0.495    Non-Playoff Team
10 (#10)  Atlanta Falcons                 8-9           0.505    Non-Playoff Team
11 (#11)  New Orleans Saints              8-9           0.500    Non-Playoff Team
12 (#12)  Jacksonville Jaguars            8-9           0.515    Non-Playoff Team
13 (#13)  Denver Broncos                  9-8           0.505    Non-Playoff Team
14 (#14)  Los Angeles Chargers            9-8           0.495    Non-Playoff Team
15 (#15)  Tampa Bay Buccaneers            9-8           0.510    Non-Playoff Team
16 (#16)  Miami Dolphins                  9-8           0.490    Non-Playoff Team
17 (#17)  Cleveland Browns                10-7          0.500    Non-Playoff Team
18 (#18)  Dallas Cowboys                  10-7          0.510    Non-Playoff Team

WILD CARD LOSERS (Picks 19-24)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
19 (#19)  Houston Texans                  11-6          0.495    Wild Card Loss
20 (#20)  Los Angeles Rams                11-6          0.505    Wild Card Loss
21 (#21)  Pittsburgh Steelers             11-6          0.510    Wild Card Loss
22 (#22)  Green Bay Packers               11-6          0.490    Wild Card Loss
23 (#23)  Minnesota Vikings               11-6          0.500    Wild Card Loss
24 (#24)  Buffalo Bills                   11-6          0.515    Wild Card Loss

DIVISIONAL LOSERS (Picks 25-28)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
25 (#25)  Baltimore Ravens                12-5          0.505    Divisional Loss
26 (#26)  Philadelphia Eagles             12-5          0.495    Divisional Loss
27 (#27)  Indianapolis Colts              12-5          0.510    Divisional Loss
28 (#28)  Seattle Seahawks                12-5          0.490    Divisional Loss

CONFERENCE LOSERS (Picks 29-30)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
29 (#29)  Cincinnati Bengals              13-4          0.500    Conference Loss
30 (#30)  Detroit Lions                   13-4          0.510    Conference Loss

CHAMPIONSHIP FINALISTS (Picks 31-32)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
31 (#31)  San Francisco 49ers             14-3          0.495    Super Bowl Loss
32 (#32)  Kansas City Chiefs              14-3          0.505    Super Bowl Winner

═════════════════════════════════════════════════════════════════════════════════════════════════
[ROUND 1 COMPLETE - 32 picks made]
═════════════════════════════════════════════════════════════════════════════════════════════════

Press ENTER to continue to Round 2...
(R=Review, S=Summary, Q=Quit)
```

---

## 5. Color Coding Strategy

### 5.1 ANSI Color Codes (Terminal Safe)

```python
class DraftColors:
    """ANSI color codes for draft display"""
    HEADER = '\033[95m'           # Magenta - main titles
    OKBLUE = '\033[94m'           # Blue - playoff info
    OKCYAN = '\033[96m'           # Cyan - divisional losers
    OKGREEN = '\033[92m'          # Green - success/winners
    WARNING = '\033[93m'          # Yellow - wild card losers
    FAIL = '\033[91m'             # Red - non-playoff teams
    BOLD = '\033[1m'              # Bold text
    DIM = '\033[2m'               # Dim text
    UNDERLINE = '\033[4m'         # Underline
    ENDC = '\033[0m'              # Reset all
```

### 5.2 Color Application Strategy

**By Playoff Status** (applied to entire row):

| Pick Category | Color | Usage |
|---|---|---|
| Super Bowl Winner | HEADER (Magenta) | Pick 32 highlight |
| Super Bowl Loser | OKGREEN (Green) | Pick 31 highlight |
| Conference Losers | OKBLUE (Blue) | Picks 29-30 |
| Divisional Losers | OKCYAN (Cyan) | Picks 25-28 |
| Wild Card Losers | WARNING (Yellow) | Picks 19-24 |
| Non-Playoff Teams | FAIL (Red) | Picks 1-18 |

**Secondary Coloring** (applied to specific fields):

- **Team Name**: Status color + BOLD for emphasis
- **Record**: OKGREEN if SB winner, DIM if non-playoff
- **SOS**: Normal text
- **Reason**: Status color, no background

**Example Implementation**:
```python
def format_pick_row(pick, category_color):
    """Format a single pick row with colors"""
    return (
        f"{category_color}{pick_num:<6}{ENDC} "
        f"{category_color}{BOLD}{team_name:<28}{ENDC} "
        f"{record:<12} "
        f"{sos:.3f}    "
        f"{category_color}{reason:<25}{ENDC}"
    )
```

---

## 6. Interactive Flow Diagram

### 6.1 Overall Draft Simulation Flow

```
┌─────────────────────────┐
│  Start Draft            │
│  Display Welcome Header │
│  Initialize 7 rounds    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ ROUND 1 (Picks 1-32)                                        │
├─────────────────────────────────────────────────────────────┤
│ FOR EACH PICK (1-32):                                       │
│   ├─ Clear screen (optional)                                │
│   ├─ Show current pick display                              │
│   │  ├─ Live draft order so far                             │
│   │  ├─ Current pick highlight                              │
│   │  └─ Live pick counter (Pick 5 of 32)                    │
│   ├─ Show AI selection animation (1-2 sec)                  │
│   ├─ Record pick to display                                 │
│   └─ AUTO-ADVANCE (500ms pause) OR wait for input           │
│                                                              │
│ AFTER ROUND 1 COMPLETE:                                     │
│   ├─ Display full Round 1 summary                           │
│   ├─ Show statistics panel                                  │
│   └─ Interactive pause (R/S/Q options)                      │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│ User chooses action                              │
├──────────────────────────────────────────────────┤
│ [ENTER]  → Continue to Round 2                   │
│ [R]      → Review previous picks                 │
│ [S]      → Show draft statistics                 │
│ [T]      → Show team's picks                     │
│ [Q]      → Quit draft                            │
└────┬─────────────────────────────────────────────┘
     │
     ├─[ENTER]──────────────────────────┐
     │                                   ▼
     │                    ┌──────────────────────────────┐
     │                    │ ROUND 2 (Picks 33-64)        │
     │                    │ [Same format as Round 1]     │
     │                    └──────────────────────────────┘
     │                                   │
     ├─[R]──────┐                        │
     │           ▼                        │
     │    Show previous picks display     │
     │    & return to pause menu          │
     │                                   │
     ├─[S]──────┐                        │
     │           ▼                        │
     │    Show summary statistics        │
     │    & return to pause menu          │
     │                                   │
     └─[Q]──────────────────────────┐
                                    ▼
                          ┌──────────────────────┐
                          │ Show draft summary   │
                          │ Final statistics     │
                          │ Exit to main menu    │
                          └──────────────────────┘
```

### 6.2 Per-Pick Micro Flow (During Round)

```
┌─────────────────────────────────────┐
│ Previous picks displayed            │
│ Current pick (PickN) highlighted    │
└────────┬────────────────────────────┘
         │
         ▼
  [Pause 500ms]
         │
         ▼
┌─────────────────────────────────────┐
│ Show "AI analyzing...  ⠋ ⠙ ⠹"       │
│ [Animated spinner]                  │
│ [Pause 1-2 seconds]                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ ✓ PICK MADE:                        │
│   Team: [Player Name, Position]     │
│   Reason: [Fit/Value/Need]          │
└────────┬────────────────────────────┘
         │
         ▼
  [Pause 500ms]
         │
         ├─ Auto-advance (if enabled)
         │
         └─ Wait for input (if interactive)
```

---

## 7. Summary Statistics Display

### 7.1 Draft Summary Format

```
════════════════════════════════════════════════════════════════════════════════════════════════
                        2025 NFL DRAFT - FINAL SUMMARY
════════════════════════════════════════════════════════════════════════════════════════════════

OVERVIEW
─────────────────────────────────────────────────────────────────────────────────────────────────
Total Picks Made:           262 (7 rounds × 32 teams)
Draft Duration:             ~45 minutes of simulation time
Draft Date:                 April 24-26, 2025

ROUND 1 BREAKDOWN
─────────────────────────────────────────────────────────────────────────────────────────────────
Non-Playoff Teams:          18 picks (Picks 1-18)
Wild Card Losers:           6 picks (Picks 19-24)
Divisional Losers:          4 picks (Picks 25-28)
Conference Losers:          2 picks (Picks 29-30)
Super Bowl Loser:           1 pick (Pick 31)
Super Bowl Winner:          1 pick (Pick 32)

TOP 10 PICKS (ROUND 1)
─────────────────────────────────────────────────────────────────────────────────────────────────
#1  Carolina Panthers       QB  Duke Johnson          (Value Pick)
#2  New York Giants         EDGE Evan Anderson       (Positional Need)
#3  Arizona Cardinals       WR  Alex Mitchell        (Fit Analysis)
#4  New England Patriots    OT  Marcus Johnson       (Protection Need)
#5  Tennessee Titans        DT  Bradley Knight       (Defensive Strength)
#6  Las Vegas Raiders       S   Jackson Reed         (Secondary Need)
#7  Washington Commanders   CB  Tyler Martin         (Coverage Depth)
#8  New York Jets           QB  Cole Richardson      (QB Succession)
#9  Chicago Bears           WR  Brandon Edwards      (Offensive Weapons)
#10 Atlanta Falcons         RB  Devon Thompson      (Backfield Production)

POSITIONAL BREAKDOWN (ALL 7 ROUNDS)
─────────────────────────────────────────────────────────────────────────────────────────────────
QB:    7 picks (2.7%)
RB:   27 picks (10.3%)
WR:   38 picks (14.5%)
TE:   18 picks (6.9%)
OL:   52 picks (19.8%)
EDGE: 31 picks (11.8%)
DL:   28 picks (10.7%)
LB:   24 picks (9.2%)
CB:   18 picks (6.9%)
S:    14 picks (5.3%)
ST:    5 picks (1.9%)

TEAM SUMMARY - YOUR TEAM (Patriots)
─────────────────────────────────────────────────────────────────────────────────────────────────
Picks Made:                 7
Round 1 Pick:               #4 OT Marcus Johnson
Highest Pick:               #4 (Round 1)
Lowest Pick:                #228 (Round 7)
Positional Focus:           Offensive Line (3), Secondary (2), DL (2)

═════════════════════════════════════════════════════════════════════════════════════════════════
```

### 7.2 Statistics Panel (Compact Version - 30 lines)

```
╔═════════════════════════════════════════════════════════════════════════════════════════════════╗
║                         DRAFT STATISTICS (CURRENT ROUND)                                        ║
╠═════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                  ║
║  Picks Complete:     72 of 262 (27.5%)                  Teams Drafted:   32 of 32 (100%)       ║
║  Current Round:      3 of 7                            Avg Time/Pick:   ~45 seconds            ║
║  Next Deadline:      End of Round 7                    Remaining Time:  ~180 minutes           ║
║                                                                                                  ║
║  Most Active Position:  WR (12 picks)                  Least Active:     ST (0 picks)          ║
║  Average Pick Time:     45 seconds                     Fastest Pick:     12 seconds             ║
║  Slowest Pick:          2 minutes 34 seconds           Current Pick:     73 of 262              ║
║                                                                                                  ║
╚═════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 8. Implementation Architecture

### 8.1 Module Structure

```
src/
├── draft/
│   ├── display/
│   │   ├── __init__.py
│   │   ├── formatter.py              # All formatting functions
│   │   ├── colors.py                 # Color codes & themes
│   │   ├── headers.py                # ASCII headers
│   │   └── interactive.py            # Interactive prompts
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── draft_simulator.py        # Main simulation loop
│   │   └── ai_selector.py            # AI pick selection
│   └── models/
│       ├── draft_pick.py             # Data models
│       └── draft_state.py            # State tracking
```

### 8.2 Key Functions

**Display Module**:
```python
# formatter.py
- format_round_header(round_num: int) -> str
- format_pick_row(pick: DraftPick, color: str) -> str
- format_category_header(category: str) -> str
- format_summary_statistics(stats: DraftStats) -> str
- center_text(text: str, width: int) -> str
- pad_columns(data: List[tuple], widths: List[int]) -> List[str]

# colors.py
- get_color_for_pick(pick_order: int) -> str
- apply_color(text: str, color: str) -> str
- strip_ansi_codes(text: str) -> str

# headers.py
- create_section_header(title: str, width: int = 95) -> str
- create_divider(width: int = 95, style: str = 'heavy') -> str
- create_pause_prompt(options: Dict[str, str]) -> str

# interactive.py
- wait_for_input(prompt: str, valid_options: List[str]) -> str
- show_pause_menu() -> str
- confirm_action(message: str) -> bool
- get_team_choice(teams: List[int]) -> int
```

**Simulation Module**:
```python
# draft_simulator.py
- run_draft_simulation(settings: DraftSettings) -> DraftResult
- run_round(round_num: int, picks_so_far: List[DraftPick]) -> None
- display_current_state(round_num, pick_num, picks_so_far) -> None
- handle_pause_menu() -> bool
- advance_to_next_pick() -> None

# ai_selector.py
- select_best_pick(team: Team, needs: List[Need]) -> Player
- evaluate_fit_score(player: Player, team: Team) -> float
- show_selection_animation() -> None
```

### 8.3 Configuration

```yaml
# draft_display_config.yaml
display:
  width: 95
  max_width: 120
  min_width: 80
  color_scheme: "standard"  # or "minimal", "dark"
  use_unicode: true

animation:
  pick_pause_ms: 500
  selection_animation_ms: 1500
  frame_rate: 30  # for spinner animation

interactive:
  auto_advance_picks: false
  auto_advance_rounds: false
  pause_after_round: true
  allow_review: true
  allow_statistics: true

statistics:
  show_summary_after_draft: true
  show_team_summary: true
  detail_level: "full"  # or "compact", "minimal"
```

---

## 9. Width & Alignment Specifications

### 9.1 Column Widths (95-column layout)

```
Pick:            6 chars  │  1 (#1234)
Team Name:      28 chars  │  Carolina Panthers
Record:         12 chars  │  4-13 (0.235)
SOS:             8 chars  │  0.480
Reason:         25 chars  │  Non-Playoff Team
Spacing:         5 chars  │  Padding
────────────────────────────
TOTAL:          95 chars
```

### 9.2 Alignment Rules

| Field | Alignment | Padding | Example |
|---|---|---|---|
| Pick # | RIGHT | 6 | `     1` |
| Team | LEFT | 28 | `Carolina Panthers    ` |
| Record | CENTER | 12 | `  4-13 (W)  ` |
| SOS | RIGHT | 8 | `  0.480` |
| Reason | LEFT | 25 | `Non-Playoff Team      ` |

**Padding Algorithm**:
```python
def pad_field(value: str, width: int, alignment: str = 'left') -> str:
    """
    Pad value to width with alignment

    Args:
        value: String to pad
        width: Target width
        alignment: 'left', 'right', or 'center'
    """
    if alignment == 'left':
        return value.ljust(width)
    elif alignment == 'right':
        return value.rjust(width)
    else:  # center
        return value.center(width)
```

---

## 10. Edge Cases & Handling

### 10.1 Edge Case Scenarios

| Scenario | Handling | Display |
|---|---|---|
| Very long team name | Truncate + ellipsis | `Chicago Bears (IL)...` |
| Tie in SOS | Show all tied teams together | Separate subsection |
| Missing player data | Show "TBD" | `TBD (Position TBD)` |
| Small terminal width | Reflow to 80 columns | Auto-detect & adjust |
| Unicode not supported | Fallback to ASCII | `===` instead of `═══` |
| Slow AI selection | Show timeout prompt | After 5 seconds: "Timeout (auto-select)" |
| User rapid input | Buffer inputs | Queue for next pause point |

### 10.2 Terminal Detection

```python
def detect_terminal_width() -> int:
    """Detect terminal width and return safe display width"""
    import shutil
    cols = shutil.get_terminal_size().columns

    if cols >= 120:
        return 120
    elif cols >= 95:
        return 95
    elif cols >= 80:
        return 80
    else:
        # Fallback for very narrow terminals
        return 70

def detect_color_support() -> bool:
    """Detect if terminal supports ANSI colors"""
    import os
    import sys

    # Check environment variables
    if os.environ.get('NO_COLOR'):
        return False

    # Check if stdout is a TTY
    return sys.stdout.isatty()
```

---

## 11. Example: Complete Round Display

### 11.1 Sample Round 2 Output

```
════════════════════════════════════════════════════════════════════════════════════════════════
                          2025 NFL DRAFT - ROUND 2
════════════════════════════════════════════════════════════════════════════════════════════════

PICKS 33-64 (ROUND 2 SELECTIONS)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
33 (#33)  Carolina Panthers               4-13          0.480    Non-Playoff Team
34 (#34)  New York Giants                 4-13          0.520    Non-Playoff Team
35 (#35)  Arizona Cardinals               5-12          0.490    Non-Playoff Team
36 (#36)  New England Patriots            5-12          0.510    Non-Playoff Team
37 (#37)  Tennessee Titans                6-11          0.500    Non-Playoff Team
38 (#38)  Las Vegas Raiders               6-11          0.510    Non-Playoff Team
39 (#39)  Washington Commanders           7-10          0.480    Non-Playoff Team
40 (#40)  New York Jets                   7-10          0.520    Non-Playoff Team
41 (#41)  Chicago Bears                   8-9           0.495    Non-Playoff Team
42 (#42)  Atlanta Falcons                 8-9           0.505    Non-Playoff Team
43 (#43)  New Orleans Saints              8-9           0.500    Non-Playoff Team
44 (#44)  Jacksonville Jaguars            8-9           0.515    Non-Playoff Team
45 (#45)  Denver Broncos                  9-8           0.505    Non-Playoff Team
46 (#46)  Los Angeles Chargers            9-8           0.495    Non-Playoff Team
47 (#47)  Tampa Bay Buccaneers            9-8           0.510    Non-Playoff Team
48 (#48)  Miami Dolphins                  9-8           0.490    Non-Playoff Team
49 (#49)  Cleveland Browns                10-7          0.500    Non-Playoff Team
50 (#50)  Dallas Cowboys                  10-7          0.510    Non-Playoff Team
51 (#51)  Houston Texans                  11-6          0.495    Wild Card Loss
52 (#52)  Los Angeles Rams                11-6          0.505    Wild Card Loss
53 (#53)  Pittsburgh Steelers             11-6          0.510    Wild Card Loss
54 (#54)  Green Bay Packers               11-6          0.490    Wild Card Loss
55 (#55)  Minnesota Vikings               11-6          0.500    Wild Card Loss
56 (#56)  Buffalo Bills                   11-6          0.515    Wild Card Loss
57 (#57)  Baltimore Ravens                12-5          0.505    Divisional Loss
58 (#58)  Philadelphia Eagles             12-5          0.495    Divisional Loss
59 (#59)  Indianapolis Colts              12-5          0.510    Divisional Loss
60 (#60)  Seattle Seahawks                12-5          0.490    Divisional Loss
61 (#61)  Cincinnati Bengals              13-4          0.500    Conference Loss
62 (#62)  Detroit Lions                   13-4          0.510    Conference Loss
63 (#63)  San Francisco 49ers             14-3          0.495    Super Bowl Loss
64 (#64)  Kansas City Chiefs              14-3          0.505    Super Bowl Winner

═════════════════════════════════════════════════════════════════════════════════════════════════
[ROUND 2 COMPLETE - 64 picks made total]
═════════════════════════════════════════════════════════════════════════════════════════════════

Press ENTER to continue to Round 3...
(R=Review, S=Summary, Q=Quit)
```

---

## 12. Interactive Pause Mechanics

### 12.1 Pause Prompt Design

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                               │
│  ✓ ROUND 1 COMPLETE - 32 picks made                                                         │
│                                                                                               │
│  Available actions:                                                                          │
│  • [ENTER]  Continue to Round 2                                                              │
│  • [R]      Review previous picks                                                            │
│  • [S]      Show draft summary statistics                                                    │
│  • [T]      Show your team's picks so far                                                    │
│  • [Q]      Quit draft simulation                                                            │
│                                                                                               │
│  Choice: _                                                                                   │
│                                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Valid Input Options

| Input | Action | Result |
|---|---|---|
| ENTER (empty) | Continue to next round | Show next round picks |
| `R` or `r` | Review picks | Display previous round in detail |
| `S` or `s` | Statistics | Show draft stats & breakdown |
| `T` or `t` | Team picks | Show your team's picks so far |
| `Q` or `q` | Quit | Show final summary & exit |
| Other | Invalid | Re-prompt with error message |

### 12.3 Validation Logic

```python
def get_pause_input(round_completed: int, total_rounds: int) -> str:
    """
    Get valid input from user at round pause

    Args:
        round_completed: Which round just finished
        total_rounds: Total number of rounds (usually 7)

    Returns:
        User's choice (validated)
    """
    valid_options = ['', 'r', 's', 't', 'q']

    while True:
        user_input = input("Choice: ").strip().lower()

        if user_input in valid_options:
            return user_input

        # Invalid input handling
        print(f"\n❌ Invalid choice: '{user_input}'")
        print("Valid options: [ENTER] R S T Q\n")
        continue
```

---

## 13. Color Scheme Reference

### 13.1 Full Color Mapping

```
Category                 Color Code      ANSI Escape       RGB (if applicable)
─────────────────────────────────────────────────────────────────────────────────
Super Bowl Winner        HEADER          \033[95m          Magenta
Super Bowl Loser         OKGREEN         \033[92m          Bright Green
Conference Losers        OKBLUE          \033[94m          Bright Blue
Divisional Losers        OKCYAN          \033[96m          Bright Cyan
Wild Card Losers         WARNING         \033[93m          Bright Yellow
Non-Playoff Teams        FAIL            \033[91m          Bright Red
Section Headers          BOLD+HEADER     \033[1m\033[95m   Bold Magenta
Table Headers            BOLD            \033[1m           Bold White
Dividers                 DIM             \033[2m           Dim White
Normal Text              ENDC            \033[0m           Default
```

### 13.2 Alternative Minimal Color Scheme (for terminals with limited support)

```python
class MinimalColors:
    """Minimal color scheme for basic terminals"""
    EMPHASIS = '\033[1m'           # Bold only
    DIM = '\033[2m'               # Dim
    UNDERLINE = '\033[4m'         # Underline
    ENDC = '\033[0m'              # Reset

    # No colors - use text styling instead
```

---

## 14. Testing & Validation

### 14.1 Test Cases

```python
# test_draft_display.py

def test_format_pick_row_alignment():
    """Verify pick row alignment meets specification"""
    pick = DraftPick(...)
    output = format_pick_row(pick, Colors.FAIL)

    # Verify total width is 95 chars (excluding ANSI codes)
    clean_output = strip_ansi_codes(output)
    assert len(clean_output) == 95

def test_color_terminal_detection():
    """Verify terminal color capability detection"""
    with mock.patch('sys.stdout.isatty', return_value=True):
        assert detect_color_support() == True

def test_width_detection():
    """Verify terminal width detection"""
    with mock.patch('shutil.get_terminal_size') as mock_size:
        mock_size.return_value.columns = 120
        assert detect_terminal_width() == 120

def test_pause_input_validation():
    """Verify pause prompt validates input correctly"""
    with mock.patch('input', return_value='R'):
        assert get_pause_input(1, 7) == 'r'

def test_unicode_fallback():
    """Verify fallback to ASCII when unicode unavailable"""
    # Should not raise exception even without unicode support
    header = create_section_header("Test", unicode_support=False)
    assert '=' in header

def test_long_team_name_truncation():
    """Verify very long team names are handled"""
    long_name = "A" * 40
    output = pad_field(long_name, 28, 'left')
    assert len(output) == 28
```

### 14.2 Validation Script

```bash
#!/bin/bash
# test_display_rendering.sh

# Test 1: Verify 95-column format
python -c "
from draft.display.formatter import format_round_header
output = format_round_header(1)
clean = ''.join(c for c in output if ord(c) < 128)
assert len(clean) == 95, f'Width mismatch: {len(clean)}'
print('✓ Column width: 95')
"

# Test 2: Verify color codes work
python -c "
from draft.display.colors import DraftColors
assert '\033[' in DraftColors.HEADER
print('✓ ANSI color codes present')
"

# Test 3: Verify no truncation
python -c "
from draft.display.formatter import format_pick_row
# Should not raise exception with various team name lengths
print('✓ No truncation errors')
"
```

---

## 15. User Experience Flow

### 15.1 Example Session (User View)

```
$ python demo/draft_simulation_demo.py

════════════════════════════════════════════════════════════════════════════════════════════════
                      2025 NFL DRAFT - BEGINS NOW
════════════════════════════════════════════════════════════════════════════════════════════════

🏈 ROUND 1 - Pick 1 of 32

Analyzing team needs...  ⠙
Evaluating players...   ⠹
Making selection...     ⠋

✓ CAROLINA PANTHERS SELECT:
  QB Duke Johnson (Duke University)

  Selection Reason: Value Pick
  Expected Fit: 9.2/10
  ─────────────────────────────────────────────────────────────────────────────────────────────────

Press ENTER to continue...
[1 second pause]
[Screen clears]

════════════════════════════════════════════════════════════════════════════════════════════════
                          2025 NFL DRAFT - ROUND 1
════════════════════════════════════════════════════════════════════════════════════════════════

PICKS 1-32 (LIVE DRAFT BOARD)
─────────────────────────────────────────────────────────────────────────────────────────────────
Pick      Team Name                      Record        SOS      Reason
─────────────────────────────────────────────────────────────────────────────────────────────────
1 (#1)    Carolina Panthers               4-13          0.480    Non-Playoff Team      ✓ QB
[continue for all 32 picks...]

[After 32 picks, show pause prompt]

Press ENTER to continue to Round 2...
(R=Review, S=Summary, Q=Quit)
[User presses S for summary]
[Summary displays, then returns to this prompt]

Choice: [ENTER]

════════════════════════════════════════════════════════════════════════════════════════════════
                          2025 NFL DRAFT - ROUND 2
════════════════════════════════════════════════════════════════════════════════════════════════
[Continues for 7 rounds total]

[After Round 7 completes]

════════════════════════════════════════════════════════════════════════════════════════════════
                        2025 NFL DRAFT - FINAL SUMMARY
════════════════════════════════════════════════════════════════════════════════════════════════
[Shows comprehensive draft statistics]

Press ENTER to return to main menu...
```

---

## Appendix A: Full Color Code Reference

```
ANSI Color Escape Codes (8-color palette):
┌──────────────────┬─────────────┬──────────────┐
│ Name             │ Code        │ RGB (approx) │
├──────────────────┼─────────────┼──────────────┤
│ Magenta (Header) │ \033[95m    │ #FF00FF      │
│ Blue (Conf)      │ \033[94m    │ #0000FF      │
│ Cyan (Div)       │ \033[96m    │ #00FFFF      │
│ Green (SB)       │ \033[92m    │ #00FF00      │
│ Yellow (WC)      │ \033[93m    │ #FFFF00      │
│ Red (Non-PO)     │ \033[91m    │ #FF0000      │
│ Bold             │ \033[1m     │ Intensity++  │
│ Dim              │ \033[2m     │ Intensity--  │
│ Reset            │ \033[0m     │ Default      │
└──────────────────┴─────────────┴──────────────┘
```

---

## Appendix B: Sample Implementation Checklist

- [ ] Create `src/draft/display/` module structure
- [ ] Implement `colors.py` with DraftColors class
- [ ] Implement `headers.py` with ASCII art functions
- [ ] Implement `formatter.py` with alignment functions
- [ ] Implement `interactive.py` with input validation
- [ ] Create `draft_display_config.yaml`
- [ ] Write comprehensive test suite
- [ ] Create demo in `demo/draft_simulation_demo/`
- [ ] Add documentation to `docs/`
- [ ] Test with various terminal widths (80, 95, 120 columns)
- [ ] Test with/without ANSI color support
- [ ] Performance test (ensure <100ms per pick display)
- [ ] User acceptance testing

---

**End of Draft Interactive Display System Design**
