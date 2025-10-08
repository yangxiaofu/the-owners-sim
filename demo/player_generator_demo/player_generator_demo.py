#!/usr/bin/env python3
"""
Player Generator Demo

Demonstrates the player generation system capabilities:
- Generate individual players with specific archetypes
- Generate complete 7-round draft classes (224 players)
- View attribute distributions and position-weighted overall calculations
- Inspect player details including ratings and metadata

Usage:
    PYTHONPATH=src python demo/player_generator_demo/player_generator_demo.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from player_generation.generators.player_generator import PlayerGenerator
from player_generation.generators.draft_class_generator import DraftClassGenerator
from player_generation.generators.attribute_generator import AttributeGenerator
from player_generation.generators.name_generator import NameGenerator
from player_generation.core.generation_context import GenerationConfig, GenerationContext
from player_generation.archetypes.base_archetype import PlayerArchetype, Position, AttributeRange
from player_generation.archetypes.archetype_registry import ArchetypeRegistry


def create_demo_archetypes():
    """Create test archetypes for demo (Sprint 3 will add JSON configuration)."""
    registry = ArchetypeRegistry()

    # QB Archetype
    qb_archetype = PlayerArchetype(
        archetype_id="demo_qb",
        position=Position.QB,
        name="Balanced QB",
        description="Well-rounded quarterback",
        physical_attributes={
            "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5),
            "strength": AttributeRange(min=70, max=85, mean=77, std_dev=5),
            "agility": AttributeRange(min=70, max=85, mean=77, std_dev=5)
        },
        mental_attributes={
            "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
        },
        position_attributes={
            "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5),
            "arm_strength": AttributeRange(min=75, max=92, mean=83, std_dev=6)
        },
        overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
        frequency=1.0,
        peak_age_range=(28, 32),
        development_curve="normal"
    )

    # RB Archetype
    rb_archetype = PlayerArchetype(
        archetype_id="demo_rb",
        position=Position.RB,
        name="Balanced RB",
        description="All-purpose running back",
        physical_attributes={
            "speed": AttributeRange(min=85, max=96, mean=90, std_dev=4),
            "strength": AttributeRange(min=70, max=88, mean=79, std_dev=6),
            "agility": AttributeRange(min=82, max=95, mean=88, std_dev=4)
        },
        mental_attributes={
            "awareness": AttributeRange(min=70, max=88, mean=79, std_dev=6),
            "vision": AttributeRange(min=75, max=92, mean=83, std_dev=5)
        },
        position_attributes={
            "carrying": AttributeRange(min=75, max=92, mean=83, std_dev=5),
            "elusiveness": AttributeRange(min=78, max=94, mean=86, std_dev=5)
        },
        overall_range=AttributeRange(min=68, max=92, mean=80, std_dev=7),
        frequency=1.0,
        peak_age_range=(25, 29),
        development_curve="early"
    )

    # WR Archetype
    wr_archetype = PlayerArchetype(
        archetype_id="demo_wr",
        position=Position.WR,
        name="Balanced WR",
        description="Complete receiver",
        physical_attributes={
            "speed": AttributeRange(min=85, max=97, mean=91, std_dev=4),
            "strength": AttributeRange(min=65, max=82, mean=73, std_dev=5),
            "agility": AttributeRange(min=80, max=95, mean=87, std_dev=5)
        },
        mental_attributes={
            "awareness": AttributeRange(min=72, max=90, mean=81, std_dev=5)
        },
        position_attributes={
            "catching": AttributeRange(min=80, max=96, mean=88, std_dev=5),
            "route_running": AttributeRange(min=75, max=92, mean=83, std_dev=5)
        },
        overall_range=AttributeRange(min=68, max=93, mean=80, std_dev=7),
        frequency=1.0,
        peak_age_range=(26, 30),
        development_curve="normal"
    )

    # EDGE Archetype
    edge_archetype = PlayerArchetype(
        archetype_id="demo_edge",
        position=Position.EDGE,
        name="Speed Rusher",
        description="Edge rusher with elite speed",
        physical_attributes={
            "speed": AttributeRange(min=85, max=97, mean=91, std_dev=4),
            "strength": AttributeRange(min=75, max=90, mean=82, std_dev=5),
            "agility": AttributeRange(min=82, max=95, mean=88, std_dev=4)
        },
        mental_attributes={
            "awareness": AttributeRange(min=70, max=88, mean=79, std_dev=5)
        },
        position_attributes={
            "pass_rush": AttributeRange(min=80, max=96, mean=88, std_dev=5),
            "run_defense": AttributeRange(min=68, max=85, mean=76, std_dev=5)
        },
        overall_range=AttributeRange(min=70, max=93, mean=81, std_dev=7),
        frequency=1.0,
        peak_age_range=(26, 30),
        development_curve="normal"
    )

    # Additional positions for draft class generation
    positions_data = [
        ("TE", Position.TE),
        ("OT", Position.OT),
        ("OG", Position.OG),
        ("C", Position.C),
        ("DT", Position.DT),
        ("LB", Position.LB),
        ("CB", Position.CB),
        ("S", Position.S)
    ]

    for pos_str, pos_enum in positions_data:
        archetype = PlayerArchetype(
            archetype_id=f"demo_{pos_str.lower()}",
            position=pos_enum,
            name=f"Balanced {pos_str}",
            description=f"Complete {pos_str} player",
            physical_attributes={
                "speed": AttributeRange(min=70, max=90, mean=80, std_dev=6),
                "strength": AttributeRange(min=70, max=90, mean=80, std_dev=6),
                "agility": AttributeRange(min=70, max=90, mean=80, std_dev=6)
            },
            mental_attributes={
                "awareness": AttributeRange(min=70, max=90, mean=80, std_dev=6)
            },
            position_attributes={
                "technique": AttributeRange(min=70, max=90, mean=80, std_dev=6)
            },
            overall_range=AttributeRange(min=65, max=92, mean=78, std_dev=8),
            frequency=1.0,
            peak_age_range=(26, 30),
            development_curve="normal"
        )
        registry.archetypes[archetype.archetype_id] = archetype

    # Register main archetypes
    registry.archetypes[qb_archetype.archetype_id] = qb_archetype
    registry.archetypes[rb_archetype.archetype_id] = rb_archetype
    registry.archetypes[wr_archetype.archetype_id] = wr_archetype
    registry.archetypes[edge_archetype.archetype_id] = edge_archetype

    return registry


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_player_card(player, show_ratings: bool = True):
    """Print formatted player card."""
    print(f"\n┌─ {player.name} ".ljust(79, "─") + "┐")
    print(f"│ Position: {player.position:<10} Age: {player.age:<3} Overall: {player.true_overall:<3} ".ljust(79) + "│")
    print(f"│ Archetype: {player.archetype_id:<40}".ljust(79) + "│")
    print(f"│ Draft: Round {player.draft_round}, Pick {player.draft_pick} ({player.draft_year if hasattr(player, 'draft_year') else 'N/A'})".ljust(79) + "│")

    if show_ratings and player.true_ratings:
        print(f"│ ".ljust(79) + "│")
        print(f"│ KEY RATINGS:".ljust(79) + "│")

        # Show top 5 ratings
        sorted_ratings = sorted(player.true_ratings.items(), key=lambda x: x[1], reverse=True)
        for i, (attr, rating) in enumerate(sorted_ratings[:5]):
            attr_display = attr.replace("_", " ").title()
            print(f"│   {attr_display:<25} {rating}".ljust(79) + "│")

    print("└" + "─" * 78 + "┘")


# Global registry for all demos
DEMO_REGISTRY = None

def get_demo_registry():
    """Get or create the demo archetype registry."""
    global DEMO_REGISTRY
    if DEMO_REGISTRY is None:
        DEMO_REGISTRY = create_demo_archetypes()
    return DEMO_REGISTRY


def demo_single_player_generation():
    """Demonstrate generating a single player."""
    print_header("DEMO 1: Single Player Generation")

    print("Generating a first-round QB prospect...\n")

    registry = get_demo_registry()
    generator = PlayerGenerator(registry=registry)
    config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        position="QB",
        draft_round=1,
        draft_pick=5,
        draft_year=2025
    )

    player = generator.generate_player(config)
    print_player_card(player)

    print(f"\nExpected overall range for Round 1: 75-95")
    print(f"Generated overall: {player.true_overall}")
    print(f"✓ Player successfully generated with realistic attributes")


def demo_position_comparison():
    """Demonstrate different positions and their attribute weights."""
    print_header("DEMO 2: Position-Specific Generation")

    positions = ["QB", "RB", "WR", "EDGE"]

    print("Generating one player at each position to show attribute differences...\n")

    registry = get_demo_registry()
    generator = PlayerGenerator(registry=registry)

    for pos in positions:
        config = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            position=pos,
            draft_round=2,
            draft_pick=40,
            draft_year=2025
        )

        player = generator.generate_player(config)
        print(f"\n{pos} - {player.name} (Overall: {player.true_overall})")

        # Show top 3 attributes for this position
        sorted_ratings = sorted(player.true_ratings.items(), key=lambda x: x[1], reverse=True)
        print("  Top attributes:")
        for attr, rating in sorted_ratings[:3]:
            print(f"    • {attr.replace('_', ' ').title()}: {rating}")


def demo_draft_round_ranges():
    """Demonstrate how draft round affects overall ratings."""
    print_header("DEMO 3: Draft Round Impact on Overall Ratings")

    print("Generating players in each round to show overall progression...\n")

    registry = get_demo_registry()
    generator = PlayerGenerator(registry=registry)

    round_ranges = {
        1: (75, 95),
        3: (68, 85),
        5: (62, 78),
        7: (55, 72)
    }

    for round_num, (expected_min, expected_max) in round_ranges.items():
        config = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            position="WR",
            draft_round=round_num,
            draft_pick=round_num * 32,
            draft_year=2025
        )

        player = generator.generate_player(config)

        print(f"Round {round_num}: {player.name}")
        print(f"  Expected range: {expected_min}-{expected_max}")
        print(f"  Generated overall: {player.true_overall}")
        print(f"  ✓ Within expected range: {expected_min <= player.true_overall <= expected_max}\n")


def demo_complete_draft_class():
    """Demonstrate generating a complete 7-round draft class."""
    print_header("DEMO 4: Complete Draft Class Generation")

    print("Generating complete 7-round NFL draft class (224 players)...\n")

    registry = get_demo_registry()
    generator = PlayerGenerator(registry=registry)
    class_gen = DraftClassGenerator(generator)

    print("⏳ Generating draft class...")
    draft_class = class_gen.generate_draft_class(year=2025)
    print(f"✓ Generated {len(draft_class)} players\n")

    # Show first 10 picks
    print("TOP 10 PICKS:")
    print("-" * 80)
    for i, player in enumerate(draft_class[:10], 1):
        print(f"{i:2d}. {player.name:<25} {player.position:<6} Overall: {player.true_overall:2d}  ({player.archetype_id})")

    # Show statistics
    print("\n" + "=" * 80)
    print("DRAFT CLASS STATISTICS")
    print("=" * 80 + "\n")

    # Overall distribution
    overalls = [p.true_overall for p in draft_class]
    avg_overall = sum(overalls) / len(overalls)
    min_overall = min(overalls)
    max_overall = max(overalls)

    print(f"Overall Ratings:")
    print(f"  Average: {avg_overall:.1f}")
    print(f"  Range: {min_overall} - {max_overall}")

    # Elite players (85+)
    elite_players = [p for p in draft_class if p.true_overall >= 85]
    print(f"  Elite players (85+): {len(elite_players)}")

    # Position distribution
    print(f"\nPosition Distribution:")
    position_counts = {}
    for player in draft_class:
        position_counts[player.position] = position_counts.get(player.position, 0) + 1

    for pos in sorted(position_counts.keys()):
        count = position_counts[pos]
        bar = "█" * (count // 2)
        print(f"  {pos:<6} {count:3d}  {bar}")

    # Round distribution
    print(f"\nPlayers per Round:")
    for round_num in range(1, 8):
        round_players = [p for p in draft_class if p.draft_round == round_num]
        avg_round_overall = sum(p.true_overall for p in round_players) / len(round_players)
        print(f"  Round {round_num}: {len(round_players)} players (avg overall: {avg_round_overall:.1f})")

    # Show some elite prospects
    if elite_players:
        print(f"\nELITE PROSPECTS ({len(elite_players)} total):")
        print("-" * 80)
        for player in elite_players[:5]:
            print(f"  {player.name:<25} {player.position:<6} Overall: {player.true_overall:2d}  (Round {player.draft_round}, Pick {player.draft_pick})")


def demo_name_generator():
    """Demonstrate name generation."""
    print_header("DEMO 5: Name Generation System")

    print("Generating unique player names...\n")

    names = NameGenerator.generate_unique_names(10)
    print(f"Generated {len(names)} unique names:")
    for i, name in enumerate(names, 1):
        print(f"  {i:2d}. {name}")

    print(f"\n✓ All names are unique: {len(names) == len(set(names))}")


def demo_attribute_generator():
    """Demonstrate attribute generation and correlation."""
    print_header("DEMO 6: Attribute Generation and Position Weights")

    print("Demonstrating position-weighted overall calculation...\n")

    # Create a sample attribute set
    sample_attrs_qb = {
        "accuracy": 90,
        "arm_strength": 85,
        "awareness": 88,
        "speed": 70,
        "agility": 72,
        "strength": 75
    }

    sample_attrs_rb = {
        "speed": 92,
        "agility": 88,
        "strength": 80,
        "carrying": 85,
        "elusiveness": 87,
        "vision": 82
    }

    qb_overall = AttributeGenerator.calculate_overall(sample_attrs_qb, "QB")
    rb_overall = AttributeGenerator.calculate_overall(sample_attrs_rb, "RB")

    print("QB Attributes:")
    for attr, rating in sample_attrs_qb.items():
        print(f"  {attr.replace('_', ' ').title():<20} {rating}")
    print(f"  → Overall Rating: {qb_overall}")

    print("\nRB Attributes:")
    for attr, rating in sample_attrs_rb.items():
        print(f"  {attr.replace('_', ' ').title():<20} {rating}")
    print(f"  → Overall Rating: {rb_overall}")

    print("\nNote: Different positions use different attribute weights for overall calculation.")


def demo_generation_contexts():
    """Demonstrate different generation contexts (Draft, UDFA, etc.)."""
    print_header("DEMO 7: Generation Contexts")

    print("Generating players in different contexts...\n")

    registry = get_demo_registry()
    generator = PlayerGenerator(registry=registry)

    # NFL Draft
    draft_config = GenerationConfig(
        context=GenerationContext.NFL_DRAFT,
        position="WR",
        draft_round=1,
        draft_pick=10,
        draft_year=2025
    )
    draft_player = generator.generate_player(draft_config)

    print(f"NFL DRAFT (Round 1):")
    print(f"  {draft_player.name} - Overall: {draft_player.true_overall}")
    print(f"  Player ID: {draft_player.player_id}")
    print(f"  Expected range: 75-95\n")

    # UDFA
    udfa_config = GenerationConfig(
        context=GenerationContext.UDFA,
        position="WR"
    )
    udfa_player = generator.generate_player(udfa_config)

    print(f"UNDRAFTED FREE AGENT:")
    print(f"  {udfa_player.name} - Overall: {udfa_player.true_overall}")
    print(f"  Player ID: {udfa_player.player_id}")
    print(f"  Expected range: 50-68 (UDFA ceiling)\n")

    print("✓ Different contexts produce appropriately rated players")


def interactive_menu():
    """Interactive demo menu."""
    while True:
        print("\n" + "=" * 80)
        print("  PLAYER GENERATOR DEMO - INTERACTIVE MENU")
        print("=" * 80)
        print("\n1. Generate Single Player")
        print("2. Compare Positions")
        print("3. Draft Round Ranges")
        print("4. Complete Draft Class (224 players)")
        print("5. Name Generator")
        print("6. Attribute Calculation")
        print("7. Generation Contexts")
        print("8. Run All Demos")
        print("9. Exit")

        choice = input("\nSelect demo (1-9): ").strip()

        if choice == "1":
            demo_single_player_generation()
        elif choice == "2":
            demo_position_comparison()
        elif choice == "3":
            demo_draft_round_ranges()
        elif choice == "4":
            demo_complete_draft_class()
        elif choice == "5":
            demo_name_generator()
        elif choice == "6":
            demo_attribute_generator()
        elif choice == "7":
            demo_generation_contexts()
        elif choice == "8":
            demo_single_player_generation()
            demo_position_comparison()
            demo_draft_round_ranges()
            demo_complete_draft_class()
            demo_name_generator()
            demo_attribute_generator()
            demo_generation_contexts()
            print("\n" + "=" * 80)
            print("  ALL DEMOS COMPLETED")
            print("=" * 80)
        elif choice == "9":
            print("\nExiting demo. Thanks for exploring the player generation system!")
            break
        else:
            print("\n❌ Invalid choice. Please select 1-9.")


def main():
    """Main demo entry point."""
    print("\n" + "=" * 80)
    print("  NFL PLAYER GENERATOR SYSTEM - DEMONSTRATION")
    print("=" * 80)
    print("\n  Sprint 1: Core Infrastructure ✓")
    print("  Sprint 2: Basic Player Generation ✓")
    print("\n  This demo showcases:")
    print("    • Statistical attribute generation")
    print("    • Position-specific overall calculation")
    print("    • Draft round-based rating ranges")
    print("    • Complete 7-round draft class generation")
    print("    • Name generation system")
    print("    • Multiple generation contexts (Draft, UDFA)")
    print("=" * 80)

    interactive_menu()


if __name__ == "__main__":
    main()