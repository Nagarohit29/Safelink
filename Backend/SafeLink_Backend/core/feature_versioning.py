"""
Feature Versioning System

Tracks feature extraction schema changes, maintains compatibility,
and supports A/B testing with multiple feature versions.
"""

import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FeatureSchema:
    """Feature extraction schema definition."""
    version: str
    name: str
    description: str
    features: List[str]
    feature_types: Dict[str, str]
    created_at: str
    checksum: str
    metadata: Dict[str, Any]


class FeatureVersionManager:
    """
    Manages multiple versions of feature extraction schemas.
    
    Features:
    - Version tracking and storage
    - Schema compatibility checks
    - Migration utilities
    - A/B testing support
    """
    
    def __init__(self, schema_dir: str = "models/feature_schemas"):
        """
        Initialize feature version manager.
        
        Args:
            schema_dir: Directory to store schema files
        """
        self.schema_dir = Path(schema_dir)
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        
        self.schemas: Dict[str, FeatureSchema] = {}
        self.extractors: Dict[str, Callable] = {}
        
        self._load_all_schemas()
        logger.info(f"FeatureVersionManager initialized: {len(self.schemas)} schemas loaded")
    
    def _compute_checksum(self, features: List[str]) -> str:
        """Compute checksum for feature list."""
        feature_str = "|".join(sorted(features))
        return hashlib.sha256(feature_str.encode()).hexdigest()[:16]
    
    def _load_all_schemas(self):
        """Load all schema files from disk."""
        for schema_file in self.schema_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                schema = FeatureSchema(**schema_data)
                self.schemas[schema.version] = schema
                logger.debug(f"Loaded schema: {schema.version}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file}: {e}")
    
    def register_schema(self, version: str, name: str, features: List[str],
                       feature_types: Dict[str, str], description: str = "",
                       metadata: Optional[Dict] = None) -> FeatureSchema:
        """
        Register a new feature schema version.
        
        Args:
            version: Version string (e.g., "1.0.0", "2.1.0")
            name: Schema name
            features: List of feature names
            feature_types: Dict mapping feature names to types
            description: Schema description
            metadata: Additional metadata
            
        Returns:
            FeatureSchema object
        """
        if version in self.schemas:
            logger.warning(f"Schema version {version} already exists, overwriting")
        
        checksum = self._compute_checksum(features)
        
        schema = FeatureSchema(
            version=version,
            name=name,
            description=description,
            features=features,
            feature_types=feature_types,
            created_at=datetime.now().isoformat(),
            checksum=checksum,
            metadata=metadata or {}
        )
        
        # Save to disk
        schema_file = self.schema_dir / f"schema_{version}.json"
        with open(schema_file, 'w') as f:
            json.dump(asdict(schema), f, indent=2)
        
        self.schemas[version] = schema
        logger.info(f"Registered schema {version}: {len(features)} features")
        
        return schema
    
    def register_extractor(self, version: str, extractor_func: Callable):
        """
        Register feature extraction function for a version.
        
        Args:
            version: Schema version
            extractor_func: Function that extracts features
        """
        if version not in self.schemas:
            raise ValueError(f"Schema version {version} not found")
        
        self.extractors[version] = extractor_func
        logger.info(f"Registered extractor for version {version}")
    
    def get_schema(self, version: str) -> Optional[FeatureSchema]:
        """Get schema by version."""
        return self.schemas.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """Get latest schema version."""
        if not self.schemas:
            return None
        
        # Sort versions (assumes semantic versioning)
        versions = sorted(self.schemas.keys(), 
                         key=lambda v: tuple(map(int, v.split('.'))),
                         reverse=True)
        return versions[0]
    
    def list_versions(self) -> List[str]:
        """List all schema versions."""
        return sorted(self.schemas.keys(), 
                     key=lambda v: tuple(map(int, v.split('.'))))
    
    def check_compatibility(self, version1: str, version2: str) -> Dict:
        """
        Check compatibility between two schema versions.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            Compatibility report
        """
        schema1 = self.schemas.get(version1)
        schema2 = self.schemas.get(version2)
        
        if not schema1 or not schema2:
            return {"compatible": False, "error": "Schema not found"}
        
        features1 = set(schema1.features)
        features2 = set(schema2.features)
        
        added = features2 - features1
        removed = features1 - features2
        common = features1 & features2
        
        # Check type compatibility for common features
        type_changes = []
        for feat in common:
            if schema1.feature_types.get(feat) != schema2.feature_types.get(feat):
                type_changes.append({
                    "feature": feat,
                    "old_type": schema1.feature_types.get(feat),
                    "new_type": schema2.feature_types.get(feat)
                })
        
        report = {
            "compatible": len(removed) == 0 and len(type_changes) == 0,
            "version1": version1,
            "version2": version2,
            "features_added": list(added),
            "features_removed": list(removed),
            "features_common": list(common),
            "type_changes": type_changes,
            "backward_compatible": len(removed) == 0
        }
        
        return report
    
    def migrate_features(self, data: Dict, from_version: str, 
                        to_version: str) -> Dict:
        """
        Migrate feature data from one version to another.
        
        Args:
            data: Feature data dictionary
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            Migrated feature data
        """
        compat = self.check_compatibility(from_version, to_version)
        
        if not compat.get("backward_compatible"):
            logger.warning(f"Migration from {from_version} to {to_version} "
                          f"may lose data: {compat['features_removed']}")
        
        schema_to = self.schemas[to_version]
        migrated = {}
        
        # Copy common features
        for feat in compat["features_common"]:
            if feat in data:
                migrated[feat] = data[feat]
        
        # Add default values for new features
        for feat in compat["features_added"]:
            feat_type = schema_to.feature_types.get(feat, "float")
            if feat_type in ["int", "int64"]:
                migrated[feat] = 0
            elif feat_type in ["float", "float64"]:
                migrated[feat] = 0.0
            else:
                migrated[feat] = None
        
        return migrated
    
    def extract_features(self, packet, version: Optional[str] = None) -> Dict:
        """
        Extract features using specified version.
        
        Args:
            packet: Scapy packet
            version: Schema version (uses latest if None)
            
        Returns:
            Extracted features dictionary
        """
        if version is None:
            version = self.get_latest_version()
        
        if version not in self.extractors:
            raise ValueError(f"No extractor registered for version {version}")
        
        extractor = self.extractors[version]
        return extractor(packet)
    
    def compare_extractions(self, packet, versions: List[str]) -> Dict:
        """
        Extract features using multiple versions for comparison.
        
        Args:
            packet: Scapy packet
            versions: List of schema versions to compare
            
        Returns:
            Dict mapping versions to extracted features
        """
        results = {}
        
        for version in versions:
            try:
                results[version] = self.extract_features(packet, version)
            except Exception as e:
                logger.error(f"Extraction failed for version {version}: {e}")
                results[version] = {"error": str(e)}
        
        return results
    
    def get_schema_diff(self, version1: str, version2: str) -> Dict:
        """
        Get detailed diff between two schemas.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            Detailed diff report
        """
        schema1 = self.schemas.get(version1)
        schema2 = self.schemas.get(version2)
        
        if not schema1 or not schema2:
            return {"error": "Schema not found"}
        
        return {
            "version1": version1,
            "version2": version2,
            "name_changed": schema1.name != schema2.name,
            "description_changed": schema1.description != schema2.description,
            "feature_count": {
                version1: len(schema1.features),
                version2: len(schema2.features)
            },
            "checksum": {
                version1: schema1.checksum,
                version2: schema2.checksum
            },
            "compatibility": self.check_compatibility(version1, version2)
        }
    
    def export_schema(self, version: str, output_path: str):
        """
        Export schema to file.
        
        Args:
            version: Schema version
            output_path: Output file path
        """
        schema = self.schemas.get(version)
        if not schema:
            raise ValueError(f"Schema {version} not found")
        
        with open(output_path, 'w') as f:
            json.dump(asdict(schema), f, indent=2)
        
        logger.info(f"Exported schema {version} to {output_path}")
    
    def import_schema(self, input_path: str) -> FeatureSchema:
        """
        Import schema from file.
        
        Args:
            input_path: Input file path
            
        Returns:
            Imported FeatureSchema
        """
        with open(input_path, 'r') as f:
            schema_data = json.load(f)
        
        schema = FeatureSchema(**schema_data)
        
        # Save to schema directory
        schema_file = self.schema_dir / f"schema_{schema.version}.json"
        with open(schema_file, 'w') as f:
            json.dump(asdict(schema), f, indent=2)
        
        self.schemas[schema.version] = schema
        logger.info(f"Imported schema {schema.version}")
        
        return schema
    
    def get_statistics(self) -> Dict:
        """Get version manager statistics."""
        return {
            "total_schemas": len(self.schemas),
            "total_extractors": len(self.extractors),
            "versions": self.list_versions(),
            "latest_version": self.get_latest_version(),
            "schema_dir": str(self.schema_dir)
        }


# Global instance
_version_manager = None


def get_version_manager() -> FeatureVersionManager:
    """Get singleton version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = FeatureVersionManager()
    return _version_manager
