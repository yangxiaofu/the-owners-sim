"""
Quick Team Needs Analyzer Demo Runner

Simplified version that runs the demo with pre-existing data.
Run with: PYTHONPATH=src python run_team_needs_demo.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency
from depth_chart.depth_chart_api import DepthChartAPI

def main():
    """Run quick demo with Cleveland Browns."""
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "team_needs_demo"
    team_id = 7  # Cleveland Browns
    season = 2025

    print("=" * 70)
    print("TEAM NEEDS ANALYZER - Cleveland Browns Demo")
    print("=" * 70)

    # Ensure depth chart exists
    print("\n🔧 Checking depth chart...")
    depth_chart_api = DepthChartAPI(db_path)

    # Check if depth chart already exists
    full_depth = depth_chart_api.get_full_depth_chart(dynasty_id, team_id)

    if not full_depth or not any(players for players in full_depth.values()):
        print("   Generating depth chart for Cleveland Browns...")
        depth_chart_api.auto_generate_depth_chart(dynasty_id, team_id)
        print("   ✅ Depth chart generated")
    else:
        print("   ✅ Depth chart already exists")

    # Create analyzer
    analyzer = TeamNeedsAnalyzer(db_path, dynasty_id)

    # Analyze team needs
    print(f"\n📊 Analyzing Cleveland Browns (Team {team_id})...")
    all_needs = analyzer.analyze_team_needs(team_id, season, include_future_contracts=True)

    # Group by urgency
    critical_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.CRITICAL]
    high_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.HIGH]
    medium_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.MEDIUM]
    low_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.LOW]

    # Display results
    print("\n" + "=" * 70)
    print(f"CLEVELAND BROWNS - NEEDS ANALYSIS")
    print(f"Dynasty: {dynasty_id} | Season: {season}")
    print("=" * 70)

    if critical_needs:
        print(f"\n🔴 CRITICAL NEEDS ({len(critical_needs)}):")
        for i, need in enumerate(critical_needs, 1):
            print(f"  {i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall")
            print(f"     Depth: {need['depth_count']} backups (avg {need['avg_depth_overall']:.0f} OVR)")
            if need['starter_leaving']:
                print(f"     ⚠️  Contract expiring!")
            print(f"     Reason: {need['reason']}")
            print()

    if high_needs:
        print(f"\n🟠 HIGH NEEDS ({len(high_needs)}):")
        for i, need in enumerate(high_needs, 1):
            print(f"  {len(critical_needs) + i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall")
            print(f"     Depth: {need['depth_count']} backups (avg {need['avg_depth_overall']:.0f} OVR)")
            if need['starter_leaving']:
                print(f"     ⚠️  Contract expiring!")
            print(f"     Reason: {need['reason']}")
            print()

    if medium_needs:
        print(f"\n🟡 MEDIUM NEEDS ({len(medium_needs)}):")
        for i, need in enumerate(medium_needs, 1):
            offset = len(critical_needs) + len(high_needs)
            print(f"  {offset + i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall | Depth: {need['depth_count']} backups")
            print(f"     Reason: {need['reason']}")
            print()

    if low_needs:
        print(f"\n🟢 LOW PRIORITY NEEDS ({len(low_needs)}):")
        positions = ", ".join([n['position'].replace('_', ' ').title() for n in low_needs[:5]])
        if len(low_needs) > 5:
            positions += f" (+{len(low_needs) - 5} more)"
        print(f"  {positions}")
        print()

    # Display strong positions
    strong_positions = []
    for position, players in full_depth.items():
        if not players:
            continue

        players_sorted = sorted(players, key=lambda p: p['depth_order'])
        starter = next((p for p in players_sorted if p['depth_order'] == 1), None)

        if starter and starter['overall'] >= 85:
            strong_positions.append((position, starter['overall']))

    if strong_positions:
        print(f"\n✅ STRONG POSITIONS ({len(strong_positions)}):")
        strong_positions.sort(key=lambda x: x[1], reverse=True)
        for position, overall in strong_positions[:5]:
            print(f"  - {position.upper().replace('_', ' ')}: {overall} OVR starter")

    print("\n" + "=" * 70)
    print("\n📈 SUMMARY:")
    print(f"   Total positions analyzed: {len(critical_needs) + len(high_needs) + len(medium_needs) + len(low_needs)}")
    print(f"   Critical needs: {len(critical_needs)}")
    print(f"   High priority needs: {len(high_needs)}")
    print(f"   Medium priority needs: {len(medium_needs)}")
    print(f"   Low priority needs: {len(low_needs)}")
    print(f"   Strong positions: {len(strong_positions)}")
    print("=" * 70)

    print("\n✅ Team Needs Analyzer demo complete!")
    print(f"\nTo run the full interactive demo: PYTHONPATH=src python demo_team_needs_analyzer.py")


if __name__ == "__main__":
    main()
