"""Data Migration Service — handles chunk-based data extraction, transformation, and loading.

This service provides the core data migration logic used by Lambda functions:
- Extract data from source database in chunks
- Transform data between different database types
- Load data to destination database
- Handle data type conversions
- Manage batch operations for performance
- Track progress and handle errors
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

from app.services.validators import get_validator
from app.services.schema_discovery_service import ColumnInfo, TableInfo

logger = logging.getLogger(__name__)


class DataMigrationService:
    """Service for chunk-based data migration between databases."""

    def __init__(self, chunk_size: int = 10000):
        """Initialize the data migration service.
        
        Args:
            chunk_size: Number of rows to process per chunk
        """
        self.chunk_size = chunk_size

    def migrate_chunk(
        self,
        source_config: Dict[str, Any],
        dest_config: Dict[str, Any],
        table_name: str,
        start_row: int,
        end_row: int,
        columns: List[ColumnInfo],
    ) -> Dict[str, Any]:
        """Migrate a single chunk of data from source to destination.
        
        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            table_name: Name of the table to migrate
            start_row: Starting row number for this chunk
            end_row: Ending row number for this chunk
            columns: Column information for the table
            
        Returns:
            Dictionary with migration results including rows_migrated, rows_failed, etc.
        """
        logger.info(
            "Migrating chunk for table %s: rows %d-%d",
            table_name, start_row, end_row
        )
        
        rows_migrated = 0
        rows_failed = 0
        errors = []
        
        source_validator = None
        dest_validator = None
        
        try:
            # Connect to source database
            source_validator = get_validator(
                source_config["database_type"],
                source_config["host"],
                source_config["port"],
                source_config["username"],
                source_config["password"],
                source_config["database_name"],
                timeout=600
            )
            source_validator.connect()
            
            # Connect to destination database
            dest_validator = get_validator(
                dest_config["database_type"],
                dest_config["host"],
                dest_config["port"],
                dest_config["username"],
                dest_config["password"],
                dest_config["database_name"],
                timeout=600
            )
            dest_validator.connect()
            
            # Extract data from source
            data = self._extract_data(
                source_validator, table_name, start_row, end_row, columns, source_config["database_type"]
            )
            
            if not data:
                logger.info("No data found for chunk %s: rows %d-%d", table_name, start_row, end_row)
                return {
                    "rows_migrated": 0,
                    "rows_failed": 0,
                    "errors": [],
                }
            
            # Transform data if needed
            transformed_data = self._transform_data(
                data, columns, source_config["database_type"], dest_config["database_type"]
            )
            
            # Load data to destination
            load_result = self._load_data(
                dest_validator, table_name, transformed_data, columns, dest_config["database_type"]
            )
            
            rows_migrated = load_result["rows_loaded"]
            rows_failed = load_result["rows_failed"]
            errors = load_result["errors"]
            
            logger.info(
                "Chunk migration completed: %s rows migrated, %s rows failed",
                rows_migrated, rows_failed
            )
            
            return {
                "rows_migrated": rows_migrated,
                "rows_failed": rows_failed,
                "errors": errors,
            }
            
        except Exception as exc:
            logger.error("Chunk migration failed: %s", exc)
            errors.append(str(exc))
            return {
                "rows_migrated": rows_migrated,
                "rows_failed": rows_failed + 1,
                "errors": errors,
            }
        finally:
            if source_validator:
                source_validator.close()
            if dest_validator:
                dest_validator.close()

    def _extract_data(
        self,
        validator: Any,
        table_name: str,
        start_row: int,
        end_row: int,
        columns: List[ColumnInfo],
        database_type: str,
    ) -> List[Tuple[Any, ...]]:
        """Extract data from source database for a chunk."""
        column_names = [col.name for col in columns]
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT {', '.join([f'`{col}`' for col in column_names])}
                    FROM `{table_name}`
                    LIMIT {end_row - start_row + 1}
                    OFFSET {start_row}
                """
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT {', '.join([f'"{col}"' for col in column_names])}
                    FROM "{table_name}"
                    LIMIT {end_row - start_row + 1}
                    OFFSET {start_row}
                """
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
            
            with validator.connection.cursor() as cursor:
                cursor.execute(query)
                data = cursor.fetchall()
                logger.debug("Extracted %d rows from source", len(data))
                return data
                
        except Exception as exc:
            logger.error("Failed to extract data: %s", exc)
            raise

    def _transform_data(
        self,
        data: List[Tuple[Any, ...]],
        columns: List[ColumnInfo],
        source_type: str,
        dest_type: str,
    ) -> List[Tuple[Any, ...]]:
        """Transform data between different database types if needed."""
        if source_type.lower() == dest_type.lower():
            # No transformation needed if same database type
            return data
        
        transformed = []
        
        for row in data:
            transformed_row = []
            for i, (value, column) in enumerate(zip(row, columns)):
                transformed_value = self._transform_value(value, column, source_type, dest_type)
                transformed_row.append(transformed_value)
            
            transformed.append(tuple(transformed_row))
        
        return transformed

    def _transform_value(
        self,
        value: Any,
        column: ColumnInfo,
        source_type: str,
        dest_type: str,
    ) -> Any:
        """Transform a single value between database types."""
        if value is None:
            return None
        
        # Handle JSON data
        if column.type.lower() == "json":
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value
        
        # Handle datetime conversions
        if column.type.lower() in ["datetime", "timestamp", "date"]:
            if isinstance(value, str):
                return value  # Keep as string, let database handle parsing
            return str(value)
        
        # Handle boolean conversions
        if column.type.lower() == "boolean":
            if isinstance(value, int):
                return bool(value)
            return value
        
        return value

    def _load_data(
        self,
        validator: Any,
        table_name: str,
        data: List[Tuple[Any, ...]],
        columns: List[ColumnInfo],
        database_type: str,
    ) -> Dict[str, Any]:
        """Load data to destination database."""
        if not data:
            return {"rows_loaded": 0, "rows_failed": 0, "errors": []}
        
        column_names = [col.name for col in columns]
        rows_loaded = 0
        rows_failed = 0
        errors = []
        
        try:
            with validator.connection.cursor() as cursor:
                # Build INSERT statement
                if database_type.lower() == "mysql":
                    placeholders = ', '.join(['%s'] * len(column_names))
                    columns_str = ', '.join([f'`{col}`' for col in column_names])
                    query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
                elif database_type.lower() == "postgresql":
                    placeholders = ', '.join(['%s'] * len(column_names))
                    columns_str = ', '.join([f'"{col}"' for col in column_names])
                    query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
                else:
                    raise ValueError(f"Unsupported database type: {database_type}")
                
                # Execute batch insert
                try:
                    cursor.executemany(query, data)
                    validator.connection.commit()
                    rows_loaded = len(data)
                    logger.debug("Loaded %d rows to destination", rows_loaded)
                except Exception as exc:
                    validator.connection.rollback()
                    logger.error("Batch insert failed, trying individual inserts: %s", exc)
                    
                    # Fall back to individual inserts
                    for row in data:
                        try:
                            cursor.execute(query, row)
                            validator.connection.commit()
                            rows_loaded += 1
                        except Exception as row_exc:
                            validator.connection.rollback()
                            rows_failed += 1
                            errors.append(f"Row failed: {str(row_exc)}")
                            logger.error("Individual row insert failed: %s", row_exc)
            
            return {
                "rows_loaded": rows_loaded,
                "rows_failed": rows_failed,
                "errors": errors,
            }
            
        except Exception as exc:
            logger.error("Failed to load data: %s", exc)
            return {
                "rows_loaded": rows_loaded,
                "rows_failed": rows_failed + len(data),
                "errors": [str(exc)],
            }

    def verify_chunk(
        self,
        source_config: Dict[str, Any],
        dest_config: Dict[str, Any],
        table_name: str,
        start_row: int,
        end_row: int,
        columns: List[ColumnInfo],
    ) -> Dict[str, Any]:
        """Verify that data was migrated correctly.
        
        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            table_name: Name of the table to verify
            start_row: Starting row number for this chunk
            end_row: Ending row number for this chunk
            columns: Column information for the table
            
        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying chunk for table %s: rows %d-%d", table_name, start_row, end_row)
        
        source_validator = None
        dest_validator = None
        
        try:
            # Connect to both databases
            source_validator = get_validator(
                source_config["database_type"],
                source_config["host"],
                source_config["port"],
                source_config["username"],
                source_config["password"],
                source_config["database_name"],
                timeout=600
            )
            source_validator.connect()
            
            dest_validator = get_validator(
                dest_config["database_type"],
                dest_config["host"],
                dest_config["port"],
                dest_config["username"],
                dest_config["password"],
                dest_config["database_name"],
                timeout=600
            )
            dest_validator.connect()
            
            # Get row counts for comparison
            source_count = self._get_chunk_row_count(
                source_validator, table_name, start_row, end_row, source_config["database_type"]
            )
            dest_count = self._get_chunk_row_count(
                dest_validator, table_name, start_row, end_row, dest_config["database_type"]
            )
            
            # Sample data comparison (check first and last rows)
            source_sample = self._get_sample_rows(
                source_validator, table_name, start_row, columns, source_config["database_type"]
            )
            dest_sample = self._get_sample_rows(
                dest_validator, table_name, start_row, columns, dest_config["database_type"]
            )
            
            is_verified = (source_count == dest_count and 
                          len(source_sample) == len(dest_sample))
            
            return {
                "verified": is_verified,
                "source_row_count": source_count,
                "dest_row_count": dest_count,
                "mismatch": source_count != dest_count,
            }
            
        except Exception as exc:
            logger.error("Verification failed: %s", exc)
            return {
                "verified": False,
                "error": str(exc),
            }
        finally:
            if source_validator:
                source_validator.close()
            if dest_validator:
                dest_validator.close()

    def _get_chunk_row_count(
        self,
        validator: Any,
        table_name: str,
        start_row: int,
        end_row: int,
        database_type: str,
    ) -> int:
        """Get row count for a specific chunk."""
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT COUNT(*) FROM `{table_name}`
                    WHERE (SELECT COUNT(*) FROM `{table_name}` LIMIT 1) > 0
                """
            elif database_type.lower() == "postgresql":
                query = f'SELECT COUNT(*) FROM "{table_name}"'
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
            
            with validator.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as exc:
            logger.error("Failed to get chunk row count: %s", exc)
            return 0

    def _get_sample_rows(
        self,
        validator: Any,
        table_name: str,
        start_row: int,
        columns: List[ColumnInfo],
        database_type: str,
        limit: int = 5,
    ) -> List[Tuple[Any, ...]]:
        """Get sample rows for verification."""
        column_names = [col.name for col in columns]
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT {', '.join([f'`{col}`' for col in column_names])}
                    FROM `{table_name}`
                    LIMIT {limit}
                    OFFSET {start_row}
                """
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT {', '.join([f'"{col}"' for col in column_names])}
                    FROM "{table_name}"
                    LIMIT {limit}
                    OFFSET {start_row}
                """
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
            
            with validator.connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
                
        except Exception as exc:
            logger.error("Failed to get sample rows: %s", exc)
            return []
