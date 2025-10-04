# Contract Generator

Converts simple player contract data from JSON into detailed year-by-year NFL contract structures with realistic salary cap calculations.

## Quick Start

```bash
# Run demonstration with 5 contract examples
PYTHONPATH=src python demo/cap_calculator_demo/contract_generator.py

# Run usage examples
PYTHONPATH=src python demo/cap_calculator_demo/example_usage.py
```

## Core Features

1. **Signing Bonus Proration**: Max 5 years per NFL CBA rules
2. **Realistic Salary Escalation**: Different patterns by contract type
3. **Guaranteed Money Distribution**: Frontloaded in early years
4. **Cap Hit Calculations**: Base salary + proration per year
5. **Multiple Contract Types**: Extension, rookie, veteran minimum, practice squad, free agent, restructure

## Basic Usage

```python
from demo.cap_calculator_demo.contract_generator import ContractGenerator

# Simple contract from player JSON
contract = {
    "contract_years": 10,
    "annual_salary": 45000000,
    "signing_bonus": 10000000,
    "guaranteed_money": 141481905,
    "contract_type": "extension",
    "cap_hit_2025": 28062269
}

# Generate detailed breakdown
generator = ContractGenerator()
details = generator.generate_contract_details(contract, start_year=2025)

# Display formatted summary
print(generator.format_contract_summary(details))
```

## Output Structure

```python
{
    'total_value': 450000000,           # Total contract value
    'signing_bonus': 10000000,          # Signing bonus
    'signing_bonus_proration': 2000000, # Annual proration
    'proration_years': 5,               # Years prorated (max 5)
    'guaranteed_money': 141481905,      # Total guaranteed
    'contract_type': 'extension',       # Contract type
    'start_year': 2025,
    'end_year': 2034,
    'year_details': [
        {
            'year': 2025,
            'base_salary': 26062269,
            'base_guaranteed': 36648015,
            'proration': 2000000,
            'cap_hit': 28062269,
            'guaranteed_total': 38648015
        },
        # ... more years
    ]
}
```

## Contract Types

### Extension (4% escalation)
Star player extensions with escalating salaries.

```python
{
    "contract_years": 10,
    "annual_salary": 45000000,
    "signing_bonus": 10000000,
    "guaranteed_money": 141481905,
    "contract_type": "extension"
}
```

### Rookie (Flat)
First-round picks with guaranteed early years.

```python
{
    "contract_years": 4,
    "annual_salary": 8000000,
    "signing_bonus": 12000000,
    "guaranteed_money": 32000000,
    "contract_type": "rookie"
}
```

### Veteran Minimum (Flat)
League minimum, no bonuses.

```python
{
    "contract_years": 1,
    "annual_salary": 1165000,
    "signing_bonus": 0,
    "guaranteed_money": 0,
    "contract_type": "veteran_minimum"
}
```

### Practice Squad (Flat)
Practice squad rate.

```python
{
    "contract_years": 1,
    "annual_salary": 216000,
    "signing_bonus": 0,
    "guaranteed_money": 0,
    "contract_type": "practice_squad"
}
```

### Free Agent (3.5% escalation)
Mid-tier signings with moderate escalation.

```python
{
    "contract_years": 3,
    "annual_salary": 12000000,
    "signing_bonus": 5000000,
    "guaranteed_money": 20000000,
    "contract_type": "free_agent"
}
```

## NFL Rules Implemented

1. **5-Year Max Proration**: Signing bonuses spread over max 5 years (NFL CBA)
2. **Salary Escalation**: Realistic patterns based on contract type
3. **Guaranteed Frontloading**: Early years fully/partially guaranteed
4. **Cap Hit Formula**: Base salary + signing bonus proration
5. **Dead Money**: Remaining proration accelerates on release

## Advanced Features

### Cap Hit Validation

```python
# Validate against known cap hit
details = generator.generate_contract_details(
    contract,
    start_year=2025,
    use_actual_cap_hit=True  # Adjusts to match cap_hit_2025
)
```

### Dead Money Analysis

```python
# Calculate if cut after year 3
year_3 = details['year_details'][3]
remaining_years = details['proration_years'] - 3
dead_money = (remaining_years * details['signing_bonus_proration']) + year_3['guaranteed_total']
cap_savings = year_3['cap_hit'] - dead_money
```

## Example Output

```
======================================================================
NFL CONTRACT DETAILS
======================================================================
Contract Type: EXTENSION
Total Value: $450,000,000
Signing Bonus: $10,000,000
Guaranteed Money: $141,481,905
Years: 2025-2034
Signing Bonus Proration: $2,000,000/year over 5 years

----------------------------------------------------------------------
Year   Base Salary     Guaranteed      Proration    Cap Hit
----------------------------------------------------------------------
2025   $26,062,269     $36,648,015     $2,000,000   $28,062,269
2026   $38,113,936     $38,113,936     $2,000,000   $40,113,936
2027   $39,638,493     $39,638,493     $2,000,000   $41,638,493
...
======================================================================
```

## Files

- `contract_generator.py`: Main ContractGenerator class (18KB)
- `example_usage.py`: Usage examples and demonstrations (4KB)
- `CONTRACT_GENERATOR.md`: This documentation

## Integration

Works with player JSON structures:

```json
{
    "name": "Patrick Mahomes",
    "position": "QB",
    "contract": {
        "contract_years": 10,
        "annual_salary": 45000000,
        "signing_bonus": 10000000,
        "guaranteed_money": 141481905,
        "contract_type": "extension",
        "cap_hit_2025": 28062269
    }
}
```

Extract `contract` object and pass to `generate_contract_details()`.

## Validation Results

```
✅ Contract Generator Validation
Total Value: $439,414,254
Signing Bonus Proration: $2,000,000
Proration Years: 5
First Year Cap Hit: $28,062,269
Expected First Year Cap Hit: $28,062,269
Match: True

✅ Year-by-year breakdown available
✅ 10 years of details generated
✅ All requirements met
```

## Future Enhancements

- Roster bonuses and workout bonuses
- Performance incentives (LTBE vs NLTBE)
- Option years and voidable years
- Restructure calculations
- Dead money with June 1 designations
- Trade dead money mechanics
- Year-over-year cap inflation

---

**Part of The Owners Sim - NFL Salary Cap Calculator Demo**
