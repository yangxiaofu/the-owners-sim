# Team Data Configuration Guide for Designers

## Overview

This guide shows game designers how to modify team configurations, coaching styles, and game balance without requiring programming knowledge. All team data is stored in easy-to-edit JSON files.

## Quick Start

**📁 Team Data Location**: `src/game_engine/data/sample_data/teams.json`

**🔄 How to Apply Changes**: 
1. Edit the JSON file
2. Save the file  
3. Restart the game simulation
4. Changes take effect immediately

## Basic Team Configuration

### Team Information
```json
{
  "id": 1,
  "name": "Bears",           ← Team nickname
  "city": "Chicago",         ← Team city
  "founded": 1919,           ← Year established  
  "division": "NFC North",   ← Division name
  "conference": "NFC"        ← Conference (NFC/AFC)
}
```

### Team Ratings (0-100 scale)

#### Offensive Ratings
```json
"offense": {
  "qb_rating": 68,     ← Quarterback quality (passing, leadership)
  "rb_rating": 75,     ← Running back ability (rushing, receiving)  
  "wr_rating": 62,     ← Wide receiver corps (catching, speed, routes)
  "ol_rating": 70,     ← Offensive line (pass protection, run blocking)
  "te_rating": 65      ← Tight ends (blocking, receiving)
}
```

#### Defensive Ratings  
```json
"defense": {
  "dl_rating": 82,     ← Defensive line (pass rush, run stopping)
  "lb_rating": 78,     ← Linebackers (coverage, run support, blitzing)
  "db_rating": 70      ← Defensive backs (coverage, ball skills)
}
```

#### Other Ratings
```json
"special_teams": 72,     ← Kicking, punting, return coverage
"overall_rating": 65     ← Team's overall strength (auto-calculated or manual)
```

## Coaching Configuration

### Coach Ratings (0-100)
```json
"coaching": {
  "offensive": 60,       ← Offensive coordinator rating
  "defensive": 75        ← Defensive coordinator rating
}
```

### Coaching Archetypes

#### Offensive Coordinator Archetypes
Choose the offensive philosophy that fits your team:

```json
"offensive_coordinator": {
  "archetype": "run_heavy"    ← Choose from options below
}
```

**Available Offensive Archetypes:**
- **`"run_heavy"`** - Power running game, physical style
- **`"west_coast"`** - Short passing, ball control, timing routes  
- **`"air_raid"`** - Deep passing, vertical routes, big plays
- **`"balanced_attack"`** - Versatile offense, uses all weapons

#### Defensive Coordinator Archetypes
Choose the defensive philosophy:

```json
"defensive_coordinator": {
  "archetype": "run_stuffing"    ← Choose from options below  
}
```

**Available Defensive Archetypes:**
- **`"run_stuffing"`** - Stop the run first, strong interior line
- **`"zone_coverage"`** - Coverage-heavy, prevent big plays
- **`"aggressive_blitz"`** - Pressure-heavy, force turnovers  
- **`"multiple_defense"`** - Versatile, changes based on situation

### Coordinator Personalities
Affects decision-making and play calling:

```json
"offensive_coordinator": {
  "personality": "traditional"    ← Choose from options below
}
```

**Available Personalities:**
- **`"traditional"`** - Conservative, proven methods
- **`"innovative"`** - Creative, adaptive, modern approaches
- **`"aggressive"`** - High-risk, high-reward play calling
- **`"balanced"`** - Situational, adapts to game state
- **`"defensive_minded"`** - Conservative, field position focused

### Custom Modifiers
Fine-tune team performance with specific bonuses:

```json
"offensive_coordinator": {
  "custom_modifiers": {
    "power_emphasis": 0.08,      ← 8% bonus to power running
    "short_passing_bonus": 0.05  ← 5% bonus to short passes
  }
}
```

**Common Custom Modifiers:**

#### Offensive Modifiers
- `"power_emphasis": 0.08` - Bonus to power running plays
- `"aaron_rodgers_effect": 0.12` - Elite QB performance bonus
- `"deep_passing_bonus": 0.06` - Bonus to deep throws
- `"vertical_passing": 0.10` - Bonus to vertical routes
- `"methodical_execution": 0.06` - Bonus to ball control offense

#### Defensive Modifiers  
- `"interior_strength": 0.10` - Bonus to interior line play
- `"coverage_emphasis": 0.08` - Bonus to pass coverage
- `"blitz_frequency": 0.15` - 15% increase in blitz rate
- `"pass_rush_emphasis": 0.12` - Bonus to pass rush
- `"bend_dont_break": 0.08` - Bonus in red zone defense

## Team Philosophy
Overall team approach that affects all game situations:

```json
"team_philosophy": "physical_dominance"    ← Choose philosophy
```

**Available Team Philosophies:**
- **`"physical_dominance"`** - Ground control, tough defense
- **`"methodical_execution"`** - Ball control, mistake-free football  
- **`"explosive_plays"`** - Big play oriented, high-scoring
- **`"star_power"`** - Talent-based, rely on individual excellence
- **`"high_risk_reward"`** - Aggressive on both sides of the ball
- **`"field_position"`** - Conservative, strategic field position game

## Financial Information
```json
"salary_cap": 224800000,    ← Team's salary cap limit
"cap_space": 18500000       ← Available cap space
```

## Example: Creating an Aggressive Team

Let's transform the Chicago Bears into an aggressive, high-risk team:

```json
"1": {
  "id": 1,
  "name": "Bears",
  "city": "Chicago", 
  "ratings": {
    "offense": {
      "qb_rating": 75,        ← Increase QB for aggressive passing
      "rb_rating": 70,        ← Reduce RB, less focus on running
      "wr_rating": 80,        ← Increase WR for deep threats
      "ol_rating": 70,
      "te_rating": 65
    },
    "defense": {
      "dl_rating": 85,        ← Increase pass rush
      "lb_rating": 82,        ← Increase for blitzing
      "db_rating": 75         ← Increase for coverage
    },
    "special_teams": 72,
    "coaching": {
      "offensive": 75,        ← Increase coordinator ratings
      "defensive": 80,
      "offensive_coordinator": {
        "archetype": "air_raid",           ← Change to aggressive passing
        "personality": "aggressive",        ← Aggressive play calling
        "custom_modifiers": {
          "deep_passing_bonus": 0.10,      ← Bonus to deep throws
          "vertical_passing": 0.08         ← Bonus to vertical routes  
        }
      },
      "defensive_coordinator": {
        "archetype": "aggressive_blitz",   ← Change to blitz-heavy
        "personality": "aggressive",        ← Aggressive approach
        "custom_modifiers": {
          "blitz_frequency": 0.20,         ← 20% more blitzes
          "pass_rush_emphasis": 0.15       ← 15% pass rush bonus
        }
      }
    },
    "overall_rating": 75      ← Increase overall due to aggression
  },
  "team_philosophy": "high_risk_reward"   ← Change philosophy
}
```

## Best Practices

### ⚖️ Balance Considerations
- Keep overall team ratings realistic (40-95 range)
- Balance strengths and weaknesses for realistic teams
- Custom modifiers should typically be 0.05-0.15 (5%-15%)
- Match archetypes with team personnel ratings

### 🧪 Testing Changes
1. Make small changes first (±5 rating points)
2. Test in single games before major modifications  
3. Keep backups of working configurations
4. Document changes for tracking balance evolution

### 📋 Common Mistakes
- **Too many high ratings**: Creates unrealistic super-teams
- **Conflicting archetypes**: Run-heavy offense with low RB rating
- **Extreme modifiers**: Values above 0.20 can break game balance
- **Mismatched philosophy**: Conservative team with aggressive coordinators

## Troubleshooting

### Game Won't Start
- Check JSON syntax (commas, brackets, quotes)
- Verify all required fields are present
- Use a JSON validator tool online

### Unrealistic Results  
- Review custom modifier values (keep under 0.15)
- Check that archetypes match team strengths
- Ensure overall ratings are balanced

### Changes Not Applied
- Restart the game simulation completely
- Verify file was saved properly
- Check file location: `src/game_engine/data/sample_data/teams.json`

## Quick Reference

### Rating Scale
- **90-100**: Elite, best in league
- **80-89**: Very good, above average  
- **70-79**: Good, average starter quality
- **60-69**: Below average, backup quality
- **50-59**: Poor, significant weakness
- **Below 50**: Terrible, major liability

### Modifier Scale
- **0.05**: Small bonus (5%)
- **0.08**: Moderate bonus (8%) 
- **0.10**: Significant bonus (10%)
- **0.12**: Large bonus (12%)
- **0.15**: Major bonus (15%)
- **Above 0.15**: Use sparingly, can break balance

This guide provides everything needed to customize team configurations and create unique, balanced football experiences without touching any code!