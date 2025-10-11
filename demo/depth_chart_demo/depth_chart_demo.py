"""
Depth Chart API Interactive Demo

Terminal-based interactive demo for exploring all depth chart API methods.
"""

import sys
import os

# Add src to path
demo_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(demo_dir))
sys.path.insert(0, os.path.join(project_root, 'src'))

from depth_chart import DepthChartAPI
import sqlite3


class DepthChartDemo:
    """Interactive demo for depth chart API."""

    def __init__(self, db_path="demo.db"):
        """Initialize demo."""
        self.db_path = db_path
        self.api = DepthChartAPI(db_path)
        self.dynasty_id = "demo_dynasty"
        self.current_team_id = 9  # Detroit Lions
        self.team_names = {9: "Detroit Lions", 3: "Chicago Bears"}

    def run(self):
        """Run interactive demo loop."""
        self._check_database()

        while True:
            self._clear_screen()
            self._print_header()
            self._print_menu()

            choice = input("\nEnter choice (0-20): ").strip()

            if choice == "0":
                print("\n👋 Goodbye!")
                break

            self._handle_choice(choice)

    def _check_database(self):
        """Check if demo database exists."""
        if not os.path.exists(self.db_path):
            print("❌ Demo database not found!")
            print(f"\nPlease run: python demo_database_setup.py")
            print(f"This will create {self.db_path} with mock data.\n")
            sys.exit(1)

    def _clear_screen(self):
        """Clear terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _print_header(self):
        """Print demo header."""
        print("╔" + "=" * 60 + "╗")
        print("║" + " " * 10 + "DEPTH CHART API INTERACTIVE DEMO" + " " * 18 + "║")
        print("║" + " " * 60 + "║")
        print(f"║  Current Dynasty: {self.dynasty_id:<43}║")
        print(f"║  Current Team:    {self.team_names[self.current_team_id]:<43}║")
        print("╚" + "=" * 60 + "╝")

    def _print_menu(self):
        """Print menu options."""
        print("\n📋 CORE RETRIEVAL METHODS")
        print("  1. Get Position Depth Chart      (show QB, RB, WR, etc.)")
        print("  2. Get Full Depth Chart          (all positions)")
        print("  3. Get Starter                   (specific position)")
        print("  4. Get Backups                   (specific position)")

        print("\n✏️  MODIFICATION METHODS")
        print("  5. Set Starter                   (promote player to depth 1)")
        print("  6. Set Backup                    (assign backup depth)")
        print("  7. Swap Depth Positions          (swap two players)")
        print("  8. Reorder Position Depth        (complete reorder)")
        print("  9. Remove From Depth Chart       (set to 99)")

        print("\n🔄 BATCH OPERATIONS")
        print(" 10. Auto-Generate Depth Chart     (sort all by overall)")
        print(" 11. Reset Position Depth Chart    (reset single position)")
        print(" 12. Clear Depth Chart             (set all to 99)")

        print("\n✅ VALIDATION METHODS")
        print(" 13. Validate Depth Chart          (show errors/warnings)")
        print(" 14. Has Starter                   (check position)")
        print(" 15. Get Depth Chart Gaps          (find missing starters)")

        print("\n📊 POSITION CONSTRAINTS")
        print(" 16. Get Position Requirements     (min/recommended depth)")
        print(" 17. Check Depth Chart Compliance  (all positions)")

        print("\n⚙️  SETTINGS & UTILITIES")
        print(" 18. Switch Team                   (Lions ↔ Bears)")
        print(" 19. Reset Demo Database           (restore mock data)")
        print(" 20. View Database Stats           (player counts, etc.)")

        print("\n  0. Exit Demo")

    def _handle_choice(self, choice):
        """Handle menu choice."""
        handlers = {
            "1": self._get_position_depth_chart,
            "2": self._get_full_depth_chart,
            "3": self._get_starter,
            "4": self._get_backups,
            "5": self._set_starter,
            "6": self._set_backup,
            "7": self._swap_depth_positions,
            "8": self._reorder_position_depth,
            "9": self._remove_from_depth_chart,
            "10": self._auto_generate_depth_chart,
            "11": self._reset_position_depth_chart,
            "12": self._clear_depth_chart,
            "13": self._validate_depth_chart,
            "14": self._has_starter,
            "15": self._get_depth_chart_gaps,
            "16": self._get_position_requirements,
            "17": self._check_depth_chart_compliance,
            "18": self._switch_team,
            "19": self._reset_database,
            "20": self._view_database_stats,
        }

        handler = handlers.get(choice)
        if handler:
            handler()
        else:
            print("\n❌ Invalid choice")
            self._pause()

    # ==================
    # Core Retrieval Methods
    # ==================

    def _get_position_depth_chart(self):
        """Option 1: Get Position Depth Chart"""
        self._print_section_header("GET POSITION DEPTH CHART")

        position = self._prompt_position()
        if not position:
            return

        print(f"\n🔍 Fetching depth chart for position: {position}")
        print(f"   api.get_position_depth_chart(dynasty_id='{self.dynasty_id}', ")
        print(f"                                team_id={self.current_team_id}, position='{position}')\n")

        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if depth_chart:
            print(f"📊 {position.upper()} Depth Chart ({len(depth_chart)} players):\n")
            for p in depth_chart:
                depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
                print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2} | #{p['jersey_number']:>2}")
        else:
            print(f"⚠️  No players found for position '{position}'")

        self._pause()

    def _get_full_depth_chart(self):
        """Option 2: Get Full Depth Chart"""
        self._print_section_header("GET FULL DEPTH CHART")

        print(f"\n🔍 Fetching complete depth chart...")
        print(f"   api.get_full_depth_chart(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id})\n")

        full_depth = self.api.get_full_depth_chart(self.dynasty_id, self.current_team_id)

        print(f"📊 Full Depth Chart ({len(full_depth)} positions):\n")

        for position in sorted(full_depth.keys()):
            players = full_depth[position]
            print(f"  {position.upper()}: {len(players)} players")

            for p in players[:3]:  # Show first 3
                depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
                print(f"    {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2}")

            if len(players) > 3:
                print(f"    ... and {len(players) - 3} more")
            print()

        self._pause()

    def _get_starter(self):
        """Option 3: Get Starter"""
        self._print_section_header("GET STARTER")

        position = self._prompt_position()
        if not position:
            return

        print(f"\n🔍 Fetching starter for position: {position}")
        print(f"   api.get_starter(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id}, ")
        print(f"                   position='{position}')\n")

        starter = self.api.get_starter(self.dynasty_id, self.current_team_id, position)

        if starter:
            print(f"✅ STARTER for {position.upper()}:")
            print(f"   {starter['player_name']} (OVR {starter['overall']}, #{starter['jersey_number']})")
        else:
            print(f"⚠️  No starter assigned for position '{position}'")

        self._pause()

    def _get_backups(self):
        """Option 4: Get Backups"""
        self._print_section_header("GET BACKUPS")

        position = self._prompt_position()
        if not position:
            return

        print(f"\n🔍 Fetching backups for position: {position}")
        print(f"   api.get_backups(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id}, ")
        print(f"                   position='{position}')\n")

        backups = self.api.get_backups(self.dynasty_id, self.current_team_id, position)

        if backups:
            print(f"📊 BACKUPS for {position.upper()} ({len(backups)} players):\n")
            for p in backups:
                print(f"  #{p['depth_chart_order']:>2} | {p['player_name']:<25} | OVR {p['overall']:>2}")
        else:
            print(f"⚠️  No backups found for position '{position}'")

        self._pause()

    # ==================
    # Modification Methods
    # ==================

    def _set_starter(self):
        """Option 5: Set Starter"""
        self._print_section_header("SET STARTER")

        position = self._prompt_position()
        if not position:
            return

        # Show current depth chart
        print(f"\n📊 CURRENT {position.upper()} Depth Chart:\n")
        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if not depth_chart:
            print(f"⚠️  No players found for position '{position}'")
            self._pause()
            return

        for p in depth_chart:
            depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
            print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2} | Player ID: {p['player_id']}")

        # Prompt for player ID
        player_id = input(f"\nEnter player_id to make starter (or 'c' to cancel): ").strip()

        if player_id.lower() == 'c':
            return

        try:
            player_id = int(player_id)
        except ValueError:
            print("❌ Invalid player_id")
            self._pause()
            return

        # Execute
        print(f"\n⚙️  Executing: api.set_starter(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id},")
        print(f"                            player_id={player_id}, position='{position}')\n")

        success = self.api.set_starter(self.dynasty_id, self.current_team_id, player_id, position)

        if success:
            # Show after
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")
            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

            for p in depth_chart:
                depth_indicator = f"#{p['depth_chart_order']}"
                marker = " ← NEW STARTER" if p['player_id'] == player_id else ""
                print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2}{marker}")
        else:
            print("\n❌ Failed to set starter (check if player plays this position)")

        self._pause()

    def _set_backup(self):
        """Option 6: Set Backup"""
        self._print_section_header("SET BACKUP")

        position = self._prompt_position()
        if not position:
            return

        # Show current depth chart
        print(f"\n📊 CURRENT {position.upper()} Depth Chart:\n")
        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if not depth_chart:
            print(f"⚠️  No players found for position '{position}'")
            self._pause()
            return

        for p in depth_chart:
            depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
            print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2} | Player ID: {p['player_id']}")

        # Prompt for player ID
        player_id = input(f"\nEnter player_id to set as backup: ").strip()
        try:
            player_id = int(player_id)
        except ValueError:
            print("❌ Invalid player_id")
            self._pause()
            return

        # Prompt for backup order
        backup_order = input(f"Enter backup depth (2, 3, 4, etc. - default 2): ").strip()
        backup_order = int(backup_order) if backup_order else 2

        # Execute
        print(f"\n⚙️  Executing: api.set_backup(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id},")
        print(f"                           player_id={player_id}, position='{position}', backup_order={backup_order})\n")

        success = self.api.set_backup(self.dynasty_id, self.current_team_id, player_id, position, backup_order)

        if success:
            # Show after
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")
            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

            for p in depth_chart:
                depth_indicator = f"#{p['depth_chart_order']}"
                marker = f" ← SET TO #{backup_order}" if p['player_id'] == player_id else ""
                print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2}{marker}")
        else:
            print("\n❌ Failed to set backup")

        self._pause()

    def _swap_depth_positions(self):
        """Option 7: Swap Depth Positions"""
        self._print_section_header("SWAP DEPTH POSITIONS")

        position = self._prompt_position()
        if not position:
            return

        # Show current depth chart
        print(f"\n📊 CURRENT {position.upper()} Depth Chart:\n")
        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if len(depth_chart) < 2:
            print(f"⚠️  Need at least 2 players to swap")
            self._pause()
            return

        for p in depth_chart:
            depth_indicator = f"#{p['depth_chart_order']}"
            print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2} | Player ID: {p['player_id']}")

        # Prompt for player IDs
        player1_id = input(f"\nEnter first player_id: ").strip()
        player2_id = input(f"Enter second player_id: ").strip()

        try:
            player1_id = int(player1_id)
            player2_id = int(player2_id)
        except ValueError:
            print("❌ Invalid player_id")
            self._pause()
            return

        # Execute
        print(f"\n⚙️  Executing: api.swap_depth_positions(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id},")
        print(f"                                      player1_id={player1_id}, player2_id={player2_id})\n")

        success = self.api.swap_depth_positions(self.dynasty_id, self.current_team_id, player1_id, player2_id)

        if success:
            # Show after
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")
            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

            for p in depth_chart:
                depth_indicator = f"#{p['depth_chart_order']}"
                marker = " ← SWAPPED" if p['player_id'] in (player1_id, player2_id) else ""
                print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2}{marker}")
        else:
            print("\n❌ Failed to swap positions")

        self._pause()

    def _reorder_position_depth(self):
        """Option 8: Reorder Position Depth"""
        self._print_section_header("REORDER POSITION DEPTH")

        position = self._prompt_position()
        if not position:
            return

        # Show current depth chart
        print(f"\n📊 CURRENT {position.upper()} Depth Chart:\n")
        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if not depth_chart:
            print(f"⚠️  No players found for position '{position}'")
            self._pause()
            return

        for p in depth_chart:
            print(f"  {p['player_name']:<25} | OVR {p['overall']:>2} | Player ID: {p['player_id']}")

        # Prompt for new order
        print(f"\nEnter player_ids in desired order (comma-separated):")
        print(f"Example: {depth_chart[0]['player_id']},{depth_chart[1]['player_id']}")

        order_input = input("New order: ").strip()

        if not order_input:
            return

        try:
            ordered_ids = [int(pid.strip()) for pid in order_input.split(',')]
        except ValueError:
            print("❌ Invalid input")
            self._pause()
            return

        # Execute
        print(f"\n⚙️  Executing: api.reorder_position_depth(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id},")
        print(f"                                       position='{position}', ordered_player_ids={ordered_ids})\n")

        success = self.api.reorder_position_depth(self.dynasty_id, self.current_team_id, position, ordered_ids)

        if success:
            # Show after
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")
            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

            for p in depth_chart:
                print(f"  #{p['depth_chart_order']:>2} | {p['player_name']:<25} | OVR {p['overall']:>2}")
        else:
            print("\n❌ Failed to reorder depth chart")

        self._pause()

    def _remove_from_depth_chart(self):
        """Option 9: Remove From Depth Chart"""
        self._print_section_header("REMOVE FROM DEPTH CHART")

        position = self._prompt_position()
        if not position:
            return

        # Show current depth chart
        print(f"\n📊 CURRENT {position.upper()} Depth Chart:\n")
        depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if not depth_chart:
            print(f"⚠️  No players found for position '{position}'")
            self._pause()
            return

        for p in depth_chart:
            depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
            print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2} | Player ID: {p['player_id']}")

        # Prompt for player ID
        player_id = input(f"\nEnter player_id to remove from depth chart: ").strip()

        try:
            player_id = int(player_id)
        except ValueError:
            print("❌ Invalid player_id")
            self._pause()
            return

        # Execute
        print(f"\n⚙️  Executing: api.remove_from_depth_chart(dynasty_id='{self.dynasty_id}', ")
        print(f"                                        team_id={self.current_team_id}, player_id={player_id})\n")

        success = self.api.remove_from_depth_chart(self.dynasty_id, self.current_team_id, player_id)

        if success:
            # Show after
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")
            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)

            for p in depth_chart:
                depth_indicator = "UNASSIGNED" if p['depth_chart_order'] == 99 else f"#{p['depth_chart_order']}"
                marker = " ← REMOVED" if p['player_id'] == player_id else ""
                print(f"  {depth_indicator:>12} | {p['player_name']:<25} | OVR {p['overall']:>2}{marker}")
        else:
            print("\n❌ Failed to remove from depth chart")

        self._pause()

    # ==================
    # Batch Operations
    # ==================

    def _auto_generate_depth_chart(self):
        """Option 10: Auto-Generate Depth Chart"""
        self._print_section_header("AUTO-GENERATE DEPTH CHART")

        print(f"\n⚠️  This will auto-assign depth chart orders for ALL positions based on overall ratings.")
        confirm = input(f"Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            return

        print(f"\n⚙️  Executing: api.auto_generate_depth_chart(dynasty_id='{self.dynasty_id}', ")
        print(f"                                          team_id={self.current_team_id})\n")

        success = self.api.auto_generate_depth_chart(self.dynasty_id, self.current_team_id)

        if success:
            print("\n✅ Depth chart auto-generated successfully!")
            print("\nSample positions after auto-generation:\n")

            for position in ['quarterback', 'running_back', 'wide_receiver']:
                depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)
                if depth_chart:
                    print(f"  {position.upper()}:")
                    for p in depth_chart[:3]:
                        print(f"    #{p['depth_chart_order']} | {p['player_name']:<25} | OVR {p['overall']:>2}")
                    print()
        else:
            print("\n❌ Failed to auto-generate depth chart")

        self._pause()

    def _reset_position_depth_chart(self):
        """Option 11: Reset Position Depth Chart"""
        self._print_section_header("RESET POSITION DEPTH CHART")

        position = self._prompt_position()
        if not position:
            return

        print(f"\n⚠️  This will reset {position.upper()} depth chart to auto-generated (by overall rating).")
        confirm = input(f"Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            return

        print(f"\n⚙️  Executing: api.reset_position_depth_chart(dynasty_id='{self.dynasty_id}', ")
        print(f"                                           team_id={self.current_team_id}, position='{position}')\n")

        success = self.api.reset_position_depth_chart(self.dynasty_id, self.current_team_id, position)

        if success:
            print(f"\n✅ {position.upper()} depth chart reset successfully!")
            print(f"\n📊 AFTER {position.upper()} Depth Chart:\n")

            depth_chart = self.api.get_position_depth_chart(self.dynasty_id, self.current_team_id, position)
            for p in depth_chart:
                print(f"  #{p['depth_chart_order']:>2} | {p['player_name']:<25} | OVR {p['overall']:>2}")
        else:
            print(f"\n❌ Failed to reset {position} depth chart")

        self._pause()

    def _clear_depth_chart(self):
        """Option 12: Clear Depth Chart"""
        self._print_section_header("CLEAR DEPTH CHART")

        print(f"\n⚠️  WARNING: This will set ALL players to UNASSIGNED (depth_chart_order = 99).")
        print(f"   You will lose all depth chart assignments!")
        confirm = input(f"\nAre you sure? (y/n): ").strip().lower()

        if confirm != 'y':
            return

        print(f"\n⚙️  Executing: api.clear_depth_chart(dynasty_id='{self.dynasty_id}', ")
        print(f"                                  team_id={self.current_team_id})\n")

        success = self.api.clear_depth_chart(self.dynasty_id, self.current_team_id)

        if success:
            print("\n✅ Depth chart cleared successfully!")
            print("\nAll players now have depth_chart_order = 99 (UNASSIGNED)")
        else:
            print("\n❌ Failed to clear depth chart")

        self._pause()

    # ==================
    # Validation Methods
    # ==================

    def _validate_depth_chart(self):
        """Option 13: Validate Depth Chart"""
        self._print_section_header("VALIDATE DEPTH CHART")

        print(f"\n🔍 Validating depth chart...")
        print(f"   api.validate_depth_chart(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id})\n")

        validation = self.api.validate_depth_chart(self.dynasty_id, self.current_team_id)

        if validation['errors']:
            print(f"❌ ERRORS ({len(validation['errors'])}):\n")
            for error in validation['errors']:
                print(f"  - {error}")
        else:
            print("✅ No errors found")

        print()

        if validation['warnings']:
            print(f"⚠️  WARNINGS ({len(validation['warnings'])}):\n")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        else:
            print("✅ No warnings")

        if validation['errors'] or validation['warnings']:
            print("\n💡 Tip: Use 'Auto-Generate Depth Chart' to fix these issues")

        self._pause()

    def _has_starter(self):
        """Option 14: Has Starter"""
        self._print_section_header("HAS STARTER")

        position = self._prompt_position()
        if not position:
            return

        print(f"\n🔍 Checking if {position.upper()} has starter...")
        print(f"   api.has_starter(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id}, ")
        print(f"                   position='{position}')\n")

        has_starter = self.api.has_starter(self.dynasty_id, self.current_team_id, position)

        if has_starter:
            starter = self.api.get_starter(self.dynasty_id, self.current_team_id, position)
            print(f"✅ YES - {position.upper()} has a starter:")
            print(f"   {starter['player_name']} (OVR {starter['overall']}, #{starter['jersey_number']})")
        else:
            print(f"❌ NO - {position.upper()} does not have a starter")

        self._pause()

    def _get_depth_chart_gaps(self):
        """Option 15: Get Depth Chart Gaps"""
        self._print_section_header("GET DEPTH CHART GAPS")

        print(f"\n🔍 Finding positions without starters...")
        print(f"   api.get_depth_chart_gaps(dynasty_id='{self.dynasty_id}', team_id={self.current_team_id})\n")

        gaps = self.api.get_depth_chart_gaps(self.dynasty_id, self.current_team_id)

        positions_with_gaps = {pos: gap for pos, gap in gaps.items() if gap > 0}

        if positions_with_gaps:
            print(f"⚠️  Found {len(positions_with_gaps)} position(s) missing starters:\n")
            for pos, gap in sorted(positions_with_gaps.items()):
                print(f"  - {pos.upper()}: Missing {gap} starter(s)")
        else:
            print("✅ All positions have starters assigned")

        self._pause()

    # ==================
    # Position Constraints
    # ==================

    def _get_position_requirements(self):
        """Option 16: Get Position Requirements"""
        self._print_section_header("GET POSITION REQUIREMENTS")

        print(f"\n📋 Position Requirements (Minimum / Recommended):\n")

        requirements = self.api.get_position_requirements()

        # Group by category
        categories = {
            'Offense': ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'],
            'Defense': ['DE', 'DT', 'NT', 'MIKE', 'SAM', 'WILL', 'ILB', 'OLB', 'CB', 'FS', 'SS'],
            'Special Teams': ['K', 'P', 'LS', 'H', 'KR', 'PR']
        }

        for category, positions in categories.items():
            print(f"  {category}:")
            for pos in positions:
                if pos in requirements:
                    req = requirements[pos]
                    print(f"    {pos:>6}: Min={req['minimum']}, Recommended={req['recommended']}")
            print()

        self._pause()

    def _check_depth_chart_compliance(self):
        """Option 17: Check Depth Chart Compliance"""
        self._print_section_header("CHECK DEPTH CHART COMPLIANCE")

        print(f"\n🔍 Checking depth chart compliance...")
        print(f"   api.check_depth_chart_compliance(dynasty_id='{self.dynasty_id}', ")
        print(f"                                     team_id={self.current_team_id})\n")

        compliance = self.api.check_depth_chart_compliance(self.dynasty_id, self.current_team_id)

        compliant = [pos for pos, status in compliance.items() if status]
        non_compliant = [pos for pos, status in compliance.items() if not status]

        if compliant:
            print(f"✅ Compliant Positions ({len(compliant)}):\n")
            for i, pos in enumerate(sorted(compliant), 1):
                print(f"  {pos}", end="")
                if i % 5 == 0:
                    print()
            print("\n")

        if non_compliant:
            print(f"❌ Non-Compliant Positions ({len(non_compliant)}):\n")
            for pos in sorted(non_compliant):
                print(f"  - {pos.upper()}")
        else:
            print("✅ All positions are compliant")

        self._pause()

    # ==================
    # Settings & Utilities
    # ==================

    def _switch_team(self):
        """Option 18: Switch Team"""
        self._print_section_header("SWITCH TEAM")

        other_team_id = 3 if self.current_team_id == 9 else 9

        print(f"\n🔄 Switch from {self.team_names[self.current_team_id]} → {self.team_names[other_team_id]}?")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm == 'y':
            self.current_team_id = other_team_id
            print(f"\n✅ Switched to {self.team_names[self.current_team_id]}")
        else:
            print("\nCancelled")

        self._pause()

    def _reset_database(self):
        """Option 19: Reset Demo Database"""
        self._print_section_header("RESET DEMO DATABASE")

        print(f"\n⚠️  WARNING: This will reset the demo database to original mock data.")
        print(f"   All changes will be lost!")
        confirm = input(f"\nAre you sure? (y/n): ").strip().lower()

        if confirm != 'y':
            return

        print(f"\n⚙️  Resetting database...")

        # Run setup script
        import demo_database_setup
        demo_database_setup.create_demo_database(self.db_path)

        # Recreate API instance
        self.api = DepthChartAPI(self.db_path)

        print(f"\n✅ Database reset successfully!")

        self._pause()

    def _view_database_stats(self):
        """Option 20: View Database Stats"""
        self._print_section_header("VIEW DATABASE STATS")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        print(f"\n📊 Database Statistics:\n")

        # Total players
        cursor.execute("SELECT COUNT(*) FROM players WHERE dynasty_id = ?", (self.dynasty_id,))
        total_players = cursor.fetchone()[0]
        print(f"  Total Players: {total_players}")

        # Players per team
        for team_id, team_name in self.team_names.items():
            cursor.execute("SELECT COUNT(*) FROM players WHERE dynasty_id = ? AND team_id = ?",
                         (self.dynasty_id, team_id))
            count = cursor.fetchone()[0]
            print(f"    {team_name}: {count} players")

        print()

        # Depth chart stats per team
        for team_id, team_name in self.team_names.items():
            cursor.execute("""
                SELECT COUNT(*)
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND depth_chart_order != 99
            """, (self.dynasty_id, team_id))
            assigned = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*)
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND depth_chart_order = 99
            """, (self.dynasty_id, team_id))
            unassigned = cursor.fetchone()[0]

            print(f"  {team_name} Depth Chart:")
            print(f"    Assigned: {assigned} players")
            print(f"    Unassigned: {unassigned} players")

        conn.close()

        self._pause()

    # ==================
    # Helper Methods
    # ==================

    def _print_section_header(self, title):
        """Print section header."""
        print("\n" + "=" * 62)
        print(f"  {title}")
        print("=" * 62)

    def _prompt_position(self):
        """Prompt user for position."""
        print("\nCommon positions:")
        print("  Offense: quarterback, running_back, wide_receiver, tight_end")
        print("  Defense: defensive_end, linebacker, cornerback, safety")
        print("  Special: kicker, punter")

        position = input("\nEnter position (or 'c' to cancel): ").strip().lower()

        if position == 'c':
            return None

        return position

    def _pause(self):
        """Pause for user input."""
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    demo = DepthChartDemo()
    demo.run()
