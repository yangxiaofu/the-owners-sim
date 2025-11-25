"""
Draft Manager

Handles NFL Draft operations including:
- Draft class generation
- Draft board construction
- Pick selection and validation
- AI team draft simulation
"""

from typing import Optional, List, Dict, Any
from database.draft_class_api import DraftClassAPI
from database.draft_order_database_api import DraftOrderDatabaseAPI
from offseason.team_needs_analyzer import TeamNeedsAnalyzer
from team_management.gm_archetype import GMArchetype
from team_management.gm_archetype_factory import GMArchetypeFactory
from transactions.personality_modifiers import TeamContext, PersonalityModifiers
from transactions.team_context_service import TeamContextService


class DraftManager:
    """
    Manages the NFL Draft process.

    Responsibilities:
    - Generate realistic draft classes
    - Maintain draft board with player rankings
    - Execute user/AI draft selections
    - Validate draft picks and eligibility
    - Track compensatory picks
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        enable_persistence: bool = True
    ):
        """
        Initialize draft manager.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            enable_persistence: Whether to save draft actions to database
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.enable_persistence = enable_persistence

        # Initialize APIs
        self.draft_api = DraftClassAPI(database_path)
        self.draft_order_api = DraftOrderDatabaseAPI(database_path)
        self.needs_analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)

        # Initialize GM AI components
        self.gm_factory = GMArchetypeFactory()
        self.context_service = TeamContextService(database_path, dynasty_id)

        # Will be initialized when needed
        self.draft_class = None
        self.draft_order = None
        self.picks_made = []

    def generate_draft_class(self, size: int = 300) -> List[Dict[str, Any]]:
        """
        Generate a draft class of prospects.

        Args:
            size: Number of prospects to generate (default 300)

        Returns:
            List of prospect dictionaries with attributes
        """
        # Check if draft class already exists
        if self.draft_api.dynasty_has_draft_class(self.dynasty_id, self.season_year):
            print(f"Draft class for {self.season_year} already exists")
        else:
            # Generate new draft class
            draft_class_id = self.draft_api.generate_draft_class(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )
            print(f"✅ Generated draft class: {draft_class_id}")

        # Return all prospects for this dynasty/season
        return self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self.season_year
        )

    def get_draft_board(
        self,
        team_id: int,
        position_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get team-specific draft board.

        Args:
            team_id: Team ID (1-32)
            position_filter: Optional position to filter by
            limit: Maximum number of prospects to return

        Returns:
            List of prospects sorted by team's board ranking
        """
        # Get all available prospects
        prospects = self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self.season_year,
            available_only=True
        )

        # Apply position filter if specified
        if position_filter:
            prospects = [p for p in prospects if p['position'] == position_filter]

        # Sort by overall rating (descending)
        prospects.sort(key=lambda p: p['overall'], reverse=True)

        # Return top N prospects
        return prospects[:limit]

    def make_draft_selection(
        self,
        round_num: int,
        pick_num: int,
        player_id: int,
        team_id: int
    ) -> Dict[str, Any]:
        """
        Execute a draft pick.

        Args:
            round_num: Draft round (1-7)
            pick_num: Pick number within round (1-32+)
            player_id: ID of prospect being drafted (temporary ID)
            team_id: Team making the pick

        Returns:
            Dictionary with pick details including:
            - player_id: NEW roster player ID (different from prospect ID)
            - prospect_id: Original prospect ID (for draft history)
            - prospect: Full prospect data
            - round, pick, team_id: Draft pick metadata
        """
        # Store original prospect ID before conversion
        prospect_id = player_id

        # Mark prospect as drafted
        prospect = self.draft_api.mark_prospect_drafted(
            player_id=prospect_id,
            team_id=team_id,
            actual_round=round_num,
            actual_pick=pick_num,
            dynasty_id=self.dynasty_id
        )

        # Convert prospect to player in main roster
        # IMPORTANT: Returns a NEW player_id (different from prospect_id)
        final_player_id = self.draft_api.convert_prospect_to_player(
            player_id=prospect_id,  # Pass prospect's temporary ID
            team_id=team_id,
            dynasty_id=self.dynasty_id
        )

        # TODO: Create rookie contract (future integration with salary cap system)
        # TODO: Trigger DraftPickEvent (future integration with event system)

        return {
            'player_id': final_player_id,  # NEW roster player ID
            'prospect_id': prospect_id,    # Original prospect ID (for history)
            'prospect': prospect,
            'round': round_num,
            'pick': pick_num,
            'team_id': team_id
        }

    def _evaluate_prospect(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        pick_position: int,
        gm: Optional[GMArchetype] = None,
        team_context: Optional[TeamContext] = None
    ) -> float:
        """
        Evaluate prospect value for a specific team.

        If gm and team_context provided: Uses GM personality modifiers (Phase 2B)
        If not provided: Uses objective need-based bonuses (Phase 2A - backward compatible)

        Args:
            prospect: Prospect dictionary with position and overall
            team_needs: List of team needs with urgency scores
            pick_position: Overall pick number (1-224)
            gm: Optional GM archetype for personality modifiers
            team_context: Optional team context for GM evaluation

        Returns:
            Adjusted value score for this prospect/team combination
        """
        if gm is not None and team_context is not None:
            # Phase 2B: GM-driven evaluation
            base_value = PersonalityModifiers.apply_draft_modifier(
                prospect=prospect,
                draft_position=pick_position,
                gm=gm,
                team_context=team_context
            )
        else:
            # Phase 2A: Objective need-based evaluation
            base_value = prospect['overall']

            # Find position urgency
            position_urgency = 0
            for need in team_needs:
                if need['position'] == prospect['position']:
                    position_urgency = need['urgency_score']
                    break

            # Apply need-based bonus
            need_boost = 0
            if position_urgency >= 5:  # CRITICAL
                need_boost = 15
            elif position_urgency >= 4:  # HIGH
                need_boost = 8
            elif position_urgency >= 3:  # MEDIUM
                need_boost = 3

            base_value += need_boost

        # Reach penalty (applied regardless of GM modifiers)
        projected_min = prospect.get('projected_pick_min', 1)
        if pick_position < projected_min - 20:
            base_value -= 5

        return base_value

    def simulate_draft(
        self,
        user_team_id: int,
        user_picks: Optional[Dict[int, str]] = None,
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Simulate entire draft with AI teams using needs-based selection.

        AI teams evaluate prospects by:
        1. Base value = prospect overall rating
        2. Need boost = +15 (CRITICAL), +8 (HIGH), +3 (MEDIUM)
        3. Position fit penalty = -5 if reaching too far above projection

        Args:
            user_team_id: User's team ID (1-32)
            user_picks: Optional dict of {overall_pick_number: player_id} for manual selections
            verbose: If True, print pick-by-pick results

        Returns:
            List of all draft picks made (up to 224 picks for 7 rounds)

        Example:
            # Let AI draft for all teams
            results = manager.simulate_draft(user_team_id=22)

            # User makes picks 1 and 15, AI does rest
            results = manager.simulate_draft(
                user_team_id=22,
                user_picks={1: 'player_123', 15: 'player_456'}
            )
        """
        if verbose:
            print(f"\n🏈 Starting {self.season_year} NFL Draft Simulation\n")
            print("=" * 80)

        # Get draft order from database
        all_picks = self.draft_order_api.get_draft_order(
            dynasty_id=self.dynasty_id,
            season=self.season_year
        )

        if not all_picks:
            raise ValueError(
                f"No draft order found for dynasty '{self.dynasty_id}' "
                f"season {self.season_year}. Generate draft order first."
            )

        # Check if draft_classes parent record exists first
        draft_class_info = self.draft_api.get_draft_class_info(
            dynasty_id=self.dynasty_id,
            season=self.season_year
        )

        if not draft_class_info:
            raise ValueError(
                f"No draft_classes record found for dynasty '{self.dynasty_id}' "
                f"season {self.season_year}. The draft class metadata is missing. "
                f"Run draft class generation or check database integrity."
            )

        # Get available prospects
        available_prospects = self.draft_api.get_all_prospects(
            dynasty_id=self.dynasty_id,
            season=self.season_year,
            available_only=True
        )

        if not available_prospects:
            raise ValueError(
                f"Draft class exists for dynasty '{self.dynasty_id}' season {self.season_year} "
                f"but has no available prospects. All prospects may be drafted already, "
                f"or the draft class may have been generated with 0 prospects."
            )

        if verbose:
            print(f"📋 Draft Order: {len(all_picks)} picks")
            print(f"🎓 Draft Class: {len(available_prospects)} prospects")
            print("=" * 80 + "\n")

        # Cache GM archetypes and team contexts for all teams (32 teams)
        if verbose:
            print("🧠 Initializing GM personalities and team contexts...")

        # Ensure all teams have salary cap initialized for this season
        from salary_cap.cap_database_api import CapDatabaseAPI
        cap_db = CapDatabaseAPI(self.database_path)
        league_cap = cap_db.get_salary_cap_for_season(self.season_year)

        if not league_cap:
            raise ValueError(
                f"No salary cap defined for season {self.season_year}. "
                f"Cannot initialize team caps."
            )

        if verbose:
            print(f"💰 Initializing salary caps for all 32 teams (${league_cap:,})...")

        initialized_count = 0
        failed_teams = []

        for team_id in range(1, 33):
            try:
                existing = cap_db.get_team_cap_summary(team_id, self.season_year, self.dynasty_id)
                if not existing:
                    cap_db.initialize_team_cap(
                        team_id, self.season_year, self.dynasty_id, league_cap, 0
                    )
                    initialized_count += 1
            except Exception as e:
                failed_teams.append((team_id, str(e)))
                if verbose:
                    print(f"  ❌ Failed to initialize cap for team {team_id}: {e}")

        if verbose:
            print(f"  ✅ Initialized {initialized_count} teams")

        # Validate ALL teams have caps
        missing_teams = []
        for team_id in range(1, 33):
            if not cap_db.get_team_cap_summary(team_id, self.season_year, self.dynasty_id):
                missing_teams.append(team_id)

        if missing_teams:
            raise RuntimeError(
                f"Salary cap initialization incomplete. Missing caps for teams: "
                f"{missing_teams}. Failed teams: {failed_teams}"
            )

        team_gms = {}
        team_contexts = {}

        for team_id in range(1, 33):
            team_gms[team_id] = self.gm_factory.get_team_archetype(team_id)
            team_contexts[team_id] = self.context_service.build_team_context(
                team_id=team_id,
                season=self.season_year,
                needs_analyzer=self.needs_analyzer,
                is_offseason=True,
                roster_mode="offseason",
                completed_season=self.season_year - 1  # Use previous season for standings
            )

        if verbose:
            print("✅ GM personalities and contexts loaded for all 32 teams\n")

        results = []
        user_picks = user_picks or {}

        # Process each pick in order
        for pick in all_picks:
            if pick.is_executed:
                if verbose:
                    print(f"⏭️  Pick {pick.overall_pick} already executed, skipping...")
                continue

            team_id = pick.current_team_id
            pick_num = pick.overall_pick

            # Check if user team with manual selection
            if team_id == user_team_id and pick_num in user_picks:
                selected_prospect_id = user_picks[pick_num]

                if verbose:
                    print(f"👤 Pick {pick_num} (R{pick.round_number}.{pick.pick_in_round}): "
                          f"User manual selection - Prospect {selected_prospect_id}")

            else:
                # AI team selection based on needs
                team_needs = self.needs_analyzer.analyze_team_needs(
                    team_id=team_id,
                    season=self.season_year
                )

                # Evaluate all available prospects for this team
                best_prospect = None
                best_score = -1

                # Determine if we should use GM modifiers
                use_gm_modifiers = (team_id != user_team_id)

                for prospect in available_prospects:
                    if use_gm_modifiers:
                        # AI team: Use GM personality evaluation
                        score = self._evaluate_prospect(
                            prospect=prospect,
                            team_needs=team_needs,
                            pick_position=pick_num,
                            gm=team_gms[team_id],
                            team_context=team_contexts[team_id]
                        )
                    else:
                        # User team (auto-pick): Use objective evaluation
                        score = self._evaluate_prospect(
                            prospect=prospect,
                            team_needs=team_needs,
                            pick_position=pick_num
                        )

                    if score > best_score:
                        best_score = score
                        best_prospect = prospect

                if not best_prospect:
                    if verbose:
                        print(f"\n⚠️  No more prospects available! Draft ended at pick {pick_num}")
                    break

                selected_prospect_id = best_prospect['player_id']

                if verbose:
                    top_need = team_needs[0]['position'] if team_needs else 'Unknown'
                    print(f"🤖 Pick {pick_num} (R{pick.round_number}.{pick.pick_in_round}): "
                          f"Team {team_id} selects {best_prospect.get('first_name', '')} "
                          f"{best_prospect.get('last_name', 'Unknown')} "
                          f"({best_prospect['position']}, {best_prospect['overall']} OVR) "
                          f"[Top Need: {top_need}, Score: {best_score:.1f}]")

            # Execute the draft pick
            try:
                result = self.make_draft_selection(
                    round_num=pick.round_number,
                    pick_num=pick.pick_in_round,
                    player_id=selected_prospect_id,  # Prospect's temporary ID
                    team_id=team_id
                )

                # Add pick metadata to result
                result['overall_pick'] = pick_num
                results.append(result)

                # Log ID transformation if verbose
                if verbose and result.get('prospect_id') != result.get('player_id'):
                    print(f"   → Prospect ID {result['prospect_id']} → Player ID {result['player_id']}")

                # Remove drafted prospect from available pool
                available_prospects = [
                    p for p in available_prospects
                    if p['player_id'] != selected_prospect_id  # Match against prospect ID
                ]

            except Exception as e:
                print(f"\n❌ Error executing pick {pick_num}: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
                # Continue with next pick
                continue

        if verbose:
            print("\n" + "=" * 80)
            print(f"✅ Draft Complete! {len(results)} picks executed")
            print("=" * 80 + "\n")

        return results
