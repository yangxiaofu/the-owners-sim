"""
Proposal Generator Factory

Provides centralized creation of proposal generators with parameter validation.
Ensures required parameters are present and validates types before instantiation,
failing fast with clear error messages.
"""

from typing import Dict, Any, Type, List
from dataclasses import dataclass
import logging

# Import all generators - handle missing generators gracefully
from game_cycle.models.proposal_enums import ProposalType

_generators_available = {}

try:
    from game_cycle.services.proposal_generators.resigning_generator import ResigningProposalGenerator
    _generators_available['resigning'] = ResigningProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.restructure_generator import RestructureProposalGenerator
    _generators_available['restructure'] = RestructureProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.franchise_tag_generator import FranchiseTagProposalGenerator
    _generators_available['franchise_tag'] = FranchiseTagProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.fa_signing_generator import FASigningProposalGenerator
    _generators_available['fa_signing'] = FASigningProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.trade_generator import TradeProposalGenerator
    _generators_available['trade'] = TradeProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.draft_generator import DraftProposalGenerator
    _generators_available['draft'] = DraftProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.cuts_generator import RosterCutsProposalGenerator
    _generators_available['cuts'] = RosterCutsProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.waiver_generator import WaiverProposalGenerator
    _generators_available['waiver'] = WaiverProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.coach_cuts_generator import CoachCutsProposalGenerator
    _generators_available['coach_cuts'] = CoachCutsProposalGenerator
except ImportError:
    pass

try:
    from game_cycle.services.proposal_generators.early_cuts_generator import EarlyCutsProposalGenerator
    _generators_available['early_cuts'] = EarlyCutsProposalGenerator
except ImportError:
    pass


@dataclass
class GeneratorSpec:
    """Specification for a proposal generator."""
    generator_class: Type
    required_params: List[str]
    optional_params: List[str]


class ProposalGeneratorFactory:
    """
    Factory for creating proposal generators with validation.

    Ensures required parameters are present and validates types
    before instantiation, failing fast with clear error messages.

    Usage:
        generator = ProposalGeneratorFactory.create(
            ProposalType.EXTENSION,
            db_path="/path/to/db",
            dynasty_id="abc123",
            season=2025,
            team_id=1,
            directives=owner_directives,
            cap_space=50000000,
            gm_archetype={"cap_management": 0.5}
        )
    """

    _logger = logging.getLogger(__name__)

    # Registry of generator specifications
    # Maps ProposalType to GeneratorSpec with required/optional params
    REGISTRY: Dict[ProposalType, GeneratorSpec] = {}

    @classmethod
    def _build_registry(cls) -> None:
        """Build the registry dynamically based on available generators."""
        if cls.REGISTRY:
            # Already built
            return

        # EXTENSION (ResigningProposalGenerator)
        if 'resigning' in _generators_available:
            cls.REGISTRY[ProposalType.EXTENSION] = GeneratorSpec(
                generator_class=_generators_available['resigning'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=["cap_space", "gm_archetype"]
            )

        # RESTRUCTURE (RestructureProposalGenerator)
        if 'restructure' in _generators_available:
            cls.REGISTRY[ProposalType.RESTRUCTURE] = GeneratorSpec(
                generator_class=_generators_available['restructure'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives", "gm_archetype"],
                optional_params=[]
            )

        # FRANCHISE_TAG (FranchiseTagProposalGenerator)
        if 'franchise_tag' in _generators_available:
            cls.REGISTRY[ProposalType.FRANCHISE_TAG] = GeneratorSpec(
                generator_class=_generators_available['franchise_tag'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # SIGNING (FASigningProposalGenerator)
        if 'fa_signing' in _generators_available:
            cls.REGISTRY[ProposalType.SIGNING] = GeneratorSpec(
                generator_class=_generators_available['fa_signing'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # TRADE (TradeProposalGenerator)
        if 'trade' in _generators_available:
            cls.REGISTRY[ProposalType.TRADE] = GeneratorSpec(
                generator_class=_generators_available['trade'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # DRAFT_PICK (DraftProposalGenerator)
        if 'draft' in _generators_available:
            cls.REGISTRY[ProposalType.DRAFT_PICK] = GeneratorSpec(
                generator_class=_generators_available['draft'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # CUT (RosterCutsProposalGenerator)
        if 'cuts' in _generators_available:
            cls.REGISTRY[ProposalType.CUT] = GeneratorSpec(
                generator_class=_generators_available['cuts'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # WAIVER_CLAIM (WaiverProposalGenerator)
        if 'waiver' in _generators_available:
            cls.REGISTRY[ProposalType.WAIVER_CLAIM] = GeneratorSpec(
                generator_class=_generators_available['waiver'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=[]
            )

        # Special generators not directly mapped to ProposalType
        # These are accessed via create_special() method
        cls._SPECIAL_GENERATORS = {}

        if 'coach_cuts' in _generators_available:
            cls._SPECIAL_GENERATORS['coach_cuts'] = GeneratorSpec(
                generator_class=_generators_available['coach_cuts'],
                required_params=["db_path", "dynasty_id", "season", "team_id", "directives"],
                optional_params=["coach_archetype_key", "coach_traits"]
            )

        if 'early_cuts' in _generators_available:
            cls._SPECIAL_GENERATORS['early_cuts'] = GeneratorSpec(
                generator_class=_generators_available['early_cuts'],
                required_params=["db_path", "dynasty_id", "season", "team_id"],
                optional_params=["cap_shortfall"]
            )

    @classmethod
    def create(
        cls,
        proposal_type: ProposalType,
        **params: Any
    ) -> Any:
        """
        Create and validate a proposal generator.

        Args:
            proposal_type: Type of proposal generator to create
            **params: Parameters to pass to generator constructor

        Returns:
            Instantiated generator

        Raises:
            ValueError: If proposal_type unknown or required parameters missing
            TypeError: If parameter types are invalid
        """
        cls._build_registry()

        spec = cls.REGISTRY.get(proposal_type)
        if not spec:
            raise ValueError(
                f"Unknown or unsupported proposal type: {proposal_type}. "
                f"Available types: {list(cls.REGISTRY.keys())}"
            )

        # Validate required parameters present
        missing = [p for p in spec.required_params if p not in params or params[p] is None]
        if missing:
            raise ValueError(
                f"{spec.generator_class.__name__} requires parameters: {missing}. "
                f"Required: {spec.required_params}. Got: {list(params.keys())}"
            )

        # Validate gm_archetype is dict if present
        if "gm_archetype" in params and params["gm_archetype"] is not None:
            # Check if it's a GMArchetype object (has to_dict method)
            if hasattr(params["gm_archetype"], 'to_dict'):
                raise TypeError(
                    f"gm_archetype must be dict, got GMArchetype object. "
                    f"Use gm_archetype.to_dict() to convert."
                )
            elif not isinstance(params["gm_archetype"], dict):
                raise TypeError(
                    f"gm_archetype must be dict, got {type(params['gm_archetype']).__name__}."
                )

        # Filter params to only those accepted by this generator
        all_accepted = set(spec.required_params) | set(spec.optional_params)
        filtered_params = {k: v for k, v in params.items() if k in all_accepted}

        cls._logger.debug(
            f"Creating {spec.generator_class.__name__} with params: {list(filtered_params.keys())}"
        )

        # Instantiate generator with validated parameters
        return spec.generator_class(**filtered_params)

    @classmethod
    def create_special(
        cls,
        generator_name: str,
        **params: Any
    ) -> Any:
        """
        Create a special generator not directly mapped to ProposalType.

        Args:
            generator_name: Name of special generator ('coach_cuts', 'early_cuts')
            **params: Parameters to pass to generator constructor

        Returns:
            Instantiated generator

        Raises:
            ValueError: If generator_name unknown or required parameters missing
            TypeError: If parameter types are invalid
        """
        cls._build_registry()

        if not hasattr(cls, '_SPECIAL_GENERATORS'):
            raise ValueError("No special generators available")

        spec = cls._SPECIAL_GENERATORS.get(generator_name)
        if not spec:
            raise ValueError(
                f"Unknown special generator: {generator_name}. "
                f"Available: {list(cls._SPECIAL_GENERATORS.keys())}"
            )

        # Validate required parameters present
        missing = [p for p in spec.required_params if p not in params or params[p] is None]
        if missing:
            raise ValueError(
                f"{spec.generator_class.__name__} requires parameters: {missing}. "
                f"Required: {spec.required_params}. Got: {list(params.keys())}"
            )

        # Filter params to only those accepted by this generator
        all_accepted = set(spec.required_params) | set(spec.optional_params)
        filtered_params = {k: v for k, v in params.items() if k in all_accepted}

        cls._logger.debug(
            f"Creating {spec.generator_class.__name__} with params: {list(filtered_params.keys())}"
        )

        # Instantiate generator with validated parameters
        return spec.generator_class(**filtered_params)

    @classmethod
    def get_required_params(cls, proposal_type: ProposalType) -> List[str]:
        """Get list of required parameters for a generator type."""
        cls._build_registry()
        spec = cls.REGISTRY.get(proposal_type)
        return spec.required_params if spec else []

    @classmethod
    def get_optional_params(cls, proposal_type: ProposalType) -> List[str]:
        """Get list of optional parameters for a generator type."""
        cls._build_registry()
        spec = cls.REGISTRY.get(proposal_type)
        return spec.optional_params if spec else []

    @classmethod
    def is_registered(cls, proposal_type: ProposalType) -> bool:
        """Check if a proposal type is registered in the factory."""
        cls._build_registry()
        return proposal_type in cls.REGISTRY

    @classmethod
    def get_available_types(cls) -> List[ProposalType]:
        """Get list of all registered proposal types."""
        cls._build_registry()
        return list(cls.REGISTRY.keys())

    @classmethod
    def get_available_special_generators(cls) -> List[str]:
        """Get list of all registered special generators."""
        cls._build_registry()
        if hasattr(cls, '_SPECIAL_GENERATORS'):
            return list(cls._SPECIAL_GENERATORS.keys())
        return []
