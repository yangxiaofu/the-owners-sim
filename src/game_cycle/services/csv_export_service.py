"""
CSV Export Service for season-end statistics archival.

Exports game-level statistics to CSV files with streaming support for large datasets.
Includes manifest generation with checksums for validation before deletion.
"""

import csv
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.export_data_api import ExportDataAPI

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of exporting a single table to CSV."""
    table_name: str
    rows_exported: int
    file_path: str
    checksum: str
    file_size_bytes: int


@dataclass
class SeasonExportResult:
    """Result of exporting all tables for a season."""
    dynasty_id: str
    season: int
    exports: List[ExportResult] = field(default_factory=list)
    export_timestamp: str = ""
    total_rows: int = 0
    total_size_bytes: int = 0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "dynasty_id": self.dynasty_id,
            "season": self.season,
            "export_timestamp": self.export_timestamp,
            "total_rows": self.total_rows,
            "total_size_bytes": self.total_size_bytes,
            "success": self.success,
            "error_message": self.error_message,
            "exports": [asdict(e) for e in self.exports]
        }


class CSVExportService:
    """
    Service for exporting game-level statistics to CSV files.

    Features:
    - Streaming export for large datasets (5000 rows per batch)
    - Checksum generation for validation
    - Manifest file with export metadata
    - Dynasty-isolated directory structure

    Directory Structure:
        data/archives/{dynasty_id}/
            season_{year}/
                player_game_stats.csv
                player_game_grades.csv
                box_scores.csv
                manifest.json
    """

    BATCH_SIZE = 5000  # Rows per streaming batch
    TABLES_TO_EXPORT = ['player_game_stats', 'player_game_grades', 'box_scores']

    def __init__(self, db_path: str, archives_root: Optional[str] = None):
        """
        Initialize the export service.

        Args:
            db_path: Path to the game_cycle database
            archives_root: Root directory for archives (default: data/archives)
        """
        self.db_path = db_path
        self.db = GameCycleDatabase(db_path)
        self.export_api = ExportDataAPI(self.db)

        if archives_root:
            self.archives_root = Path(archives_root)
        else:
            # Default to data/archives relative to project root
            self.archives_root = Path(db_path).parent.parent.parent / "archives"

    def export_season(
        self,
        dynasty_id: str,
        season: int
    ) -> SeasonExportResult:
        """
        Export all game-level statistics for a season to CSV files.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year to export

        Returns:
            SeasonExportResult with export details
        """
        result = SeasonExportResult(
            dynasty_id=dynasty_id,
            season=season,
            export_timestamp=datetime.now().isoformat()
        )

        try:
            # Create export directory
            export_dir = self._get_export_dir(dynasty_id, season)
            export_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Exporting season {season} for dynasty {dynasty_id} to {export_dir}")

            # Export each table
            for table_name in self.TABLES_TO_EXPORT:
                export_result = self._export_table(
                    dynasty_id, season, table_name, export_dir
                )
                result.exports.append(export_result)
                result.total_rows += export_result.rows_exported
                result.total_size_bytes += export_result.file_size_bytes

            # Write manifest
            self._write_manifest(export_dir, result)

            logger.info(
                f"Export complete: {result.total_rows} rows, "
                f"{result.total_size_bytes / 1024:.1f} KB"
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            result.success = False
            result.error_message = str(e)

        return result

    def _export_table(
        self,
        dynasty_id: str,
        season: int,
        table_name: str,
        export_dir: Path
    ) -> ExportResult:
        """
        Export a single table to CSV.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            table_name: Name of table to export
            export_dir: Directory to write CSV to

        Returns:
            ExportResult with file details
        """
        file_path = export_dir / f"{table_name}.csv"
        columns = self.export_api.get_columns(table_name)

        # Get the appropriate streaming method
        stream_methods = {
            'player_game_stats': self.export_api.stream_player_game_stats,
            'player_game_grades': self.export_api.stream_player_game_grades,
            'box_scores': self.export_api.stream_box_scores,
        }
        stream_method = stream_methods[table_name]

        rows_written = 0
        hasher = hashlib.sha256()

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            header_line = ','.join(columns) + '\n'
            f.write(header_line)
            hasher.update(header_line.encode('utf-8'))

            # Stream and write data batches
            for batch in stream_method(dynasty_id, season, self.BATCH_SIZE):
                for row in batch:
                    # Convert row to CSV line
                    row_values = [str(v) if v is not None else '' for v in row]
                    line = ','.join(self._escape_csv_value(v) for v in row_values) + '\n'
                    f.write(line)
                    hasher.update(line.encode('utf-8'))
                    rows_written += 1

        file_size = file_path.stat().st_size
        checksum = hasher.hexdigest()

        logger.info(f"  Exported {table_name}: {rows_written} rows, {file_size / 1024:.1f} KB")

        return ExportResult(
            table_name=table_name,
            rows_exported=rows_written,
            file_path=str(file_path),
            checksum=checksum,
            file_size_bytes=file_size
        )

    def _escape_csv_value(self, value: str) -> str:
        """
        Escape a value for CSV output.

        Args:
            value: String value to escape

        Returns:
            Escaped value (quoted if contains comma, quote, or newline)
        """
        if ',' in value or '"' in value or '\n' in value:
            return '"' + value.replace('"', '""') + '"'
        return value

    def _write_manifest(self, export_dir: Path, result: SeasonExportResult) -> None:
        """
        Write manifest.json with export metadata.

        Args:
            export_dir: Export directory
            result: Export result to write
        """
        manifest_path = export_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)

    def _get_export_dir(self, dynasty_id: str, season: int) -> Path:
        """
        Get the export directory for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Path to export directory
        """
        return self.archives_root / dynasty_id / f"season_{season}"

    # -------------------- Validation Methods --------------------

    def validate_export(self, result: SeasonExportResult) -> bool:
        """
        Validate an export by checking file checksums and row counts.

        Args:
            result: Export result to validate

        Returns:
            True if all validations pass
        """
        if not result.success:
            logger.warning("Cannot validate failed export")
            return False

        for export in result.exports:
            # Validate file exists
            file_path = Path(export.file_path)
            if not file_path.exists():
                logger.error(f"Export file not found: {file_path}")
                return False

            # Validate checksum
            actual_checksum = self._calculate_file_checksum(file_path)
            if actual_checksum != export.checksum:
                logger.error(
                    f"Checksum mismatch for {export.table_name}: "
                    f"expected {export.checksum}, got {actual_checksum}"
                )
                return False

            # Validate row count (count lines minus header)
            with open(file_path, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f) - 1  # Subtract header
            if line_count != export.rows_exported:
                logger.error(
                    f"Row count mismatch for {export.table_name}: "
                    f"expected {export.rows_exported}, got {line_count}"
                )
                return False

        logger.info("Export validation passed")
        return True

    def validate_against_database(
        self,
        dynasty_id: str,
        season: int,
        result: SeasonExportResult
    ) -> bool:
        """
        Validate export row counts against database.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            result: Export result to validate

        Returns:
            True if row counts match database
        """
        for export in result.exports:
            db_count = self.export_api.get_row_count(
                export.table_name, dynasty_id, season
            )
            if db_count != export.rows_exported:
                logger.error(
                    f"Database row count mismatch for {export.table_name}: "
                    f"exported {export.rows_exported}, database has {db_count}"
                )
                return False

        logger.info("Export matches database row counts")
        return True

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA256 checksum
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    # -------------------- Utility Methods --------------------

    def get_export_path(self, dynasty_id: str, season: int) -> Path:
        """
        Get the path where a season's export would be stored.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Path to export directory
        """
        return self._get_export_dir(dynasty_id, season)

    def export_exists(self, dynasty_id: str, season: int) -> bool:
        """
        Check if an export already exists for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if manifest.json exists in export directory
        """
        export_dir = self._get_export_dir(dynasty_id, season)
        manifest_path = export_dir / "manifest.json"
        return manifest_path.exists()

    def load_manifest(self, dynasty_id: str, season: int) -> Optional[dict]:
        """
        Load the manifest for an existing export.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Manifest dict if exists, None otherwise
        """
        manifest_path = self._get_export_dir(dynasty_id, season) / "manifest.json"
        if not manifest_path.exists():
            return None

        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)