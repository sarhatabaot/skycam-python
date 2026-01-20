"""Template management system for skycam.

This module provides template loading, validation, and management functionality.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from .camera import CameraSettings, CameraCapabilities


@dataclass
class Template:
    """Template definition for camera settings."""
    name: str
    description: Optional[str] = None
    
    # Camera settings
    aperture: Optional[float] = None
    exposure: Optional[float] = None
    iso: Optional[str] = None
    delay: Optional[float] = None
    quality: Optional[str] = None
    max_exposures: Optional[int] = None
    
    # File naming
    filename_pattern: Optional[str] = None
    timestamp_format: Optional[str] = None
    
    # Session settings
    temperature_monitoring: Optional[bool] = None
    
    def to_settings(self) -> CameraSettings:
        """Convert template to CameraSettings."""
        return CameraSettings(
            exposure=self.exposure or 8.0,
            aperture=self.aperture or 1.4,
            iso=self.iso or "auto",
            delay=self.delay or 12.0,
            quality=self.quality or "raw",
            max_exposures=self.max_exposures or 0
        )
    
    def validate(self, capabilities: Optional[CameraCapabilities] = None) -> List[str]:
        """Validate template against camera capabilities.
        
        Returns:
            List of validation warnings
        """
        warnings = []
        
        if capabilities:
            # Validate exposure
            if self.exposure is not None:
                if self.exposure not in capabilities.exposure_times:
                    closest = min(capabilities.exposure_times,
                                 key=lambda x: abs(x - self.exposure))
                    warnings.append(f"Exposure {self.exposure}s not available, closest is {closest}s")
            
            # Validate aperture
            if self.aperture is not None:
                if self.aperture not in capabilities.apertures:
                    closest = min(capabilities.apertures,
                                 key=lambda x: abs(x - self.aperture))
                    warnings.append(f"Aperture f/{self.aperture} not available, closest is f/{closest}")
            
            # Validate ISO
            if self.iso is not None and self.iso != "auto":
                if self.iso not in capabilities.iso_values:
                    warnings.append(f"ISO {self.iso} may not be supported")
        
        # Validate filename pattern
        if self.filename_pattern:
            if "{timestamp}" not in self.filename_pattern:
                warnings.append("filename_pattern should include {timestamp} for proper file naming")
        
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create template from dictionary."""
        return cls(**data)


class TemplateManager:
    """Manages template loading, validation, and storage."""
    
    def __init__(self, templates_dir: Optional[str] = None, config_dir: Optional[str] = None):
        """Initialize template manager.
        
        Args:
            templates_dir: Directory containing template files
            config_dir: Configuration directory
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "skycam"
        
        if templates_dir is None:
            templates_dir = config_dir / "templates"
        
        self.config_dir = Path(config_dir)
        self.templates_dir = Path(templates_dir)
        
        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Default template path
        self.default_template_path = self.templates_dir / "default.yml"
    
    def load_template(self, name: str) -> Template:
        """Load a template by name.
        
        Args:
            name: Template name (without .yml extension) or path to file
            
        Returns:
            Template instance
            
        Raises:
            FileNotFoundError: If template not found
            ValueError: If template is invalid
        """
        # Check if name is a path
        if os.path.exists(name):
            template_path = Path(name)
        else:
            template_path = self.templates_dir / f"{name}.yml"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{name}' not found at {template_path}")
        
        try:
            with open(template_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ValueError(f"Template file {template_path} is empty or invalid")
            
            # Add name if not present
            if 'name' not in data:
                data['name'] = template_path.stem
            
            return Template.from_dict(data)
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in template {template_path}: {e}")
    
    def save_template(self, template: Template) -> None:
        """Save a template to file.
        
        Args:
            template: Template to save
        """
        template_path = self.templates_dir / f"{template.name}.yml"
        
        with open(template_path, 'w') as f:
            yaml.dump(template.to_dict(), f, default_flow_style=False, indent=2)
    
    def list_templates(self) -> List[str]:
        """List all available templates.
        
        Returns:
            List of template names
        """
        templates = []
        
        if self.templates_dir.exists():
            for file_path in self.templates_dir.glob("*.yml"):
                templates.append(file_path.stem)
        
        return sorted(templates)
    
    def create_default_template(self) -> Template:
        """Create and save a default template.
        
        Returns:
            Default template instance
        """
        default_template = Template(
            name="default",
            description="Default skycam template for general astrophotography",
            aperture=1.4,
            exposure=8.0,
            iso="auto",
            delay=12.0,
            quality="raw",
            max_exposures=0,
            filename_pattern="SkyImage-{timestamp}",
            timestamp_format="YYYY-MM-DD_HH:MM:SS",
            temperature_monitoring=False
        )
        
        self.save_template(default_template)
        return default_template
    
    def ensure_default_template(self) -> None:
        """Ensure default template exists, create if missing."""
        if not self.default_template_path.exists():
            self.create_default_template()
    
    def get_template(self, name: str) -> Template:
        """Get a template, creating default if not found and name is 'default'.
        
        Args:
            name: Template name
            
        Returns:
            Template instance
        """
        try:
            return self.load_template(name)
        except FileNotFoundError:
            if name == "default":
                self.ensure_default_template()
                return self.load_template("default")
            raise
    
    def validate_template(self, template: Template, capabilities: Optional[CameraCapabilities] = None) -> List[str]:
        """Validate a template.
        
        Args:
            template: Template to validate
            capabilities: Camera capabilities to validate against
            
        Returns:
            List of validation warnings
        """
        warnings = template.validate(capabilities)
        
        # Check required fields
        if not template.name or template.name.strip() == "":
            warnings.append("Template name is required")
        
        return warnings


class ConfigManager:
    """Manages configuration files and settings."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Configuration directory path
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "skycam"
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yml"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            'default_template': 'default',
            'templates_directory': str(self.config_dir / 'templates'),
            'output_directory': str(Path.home() / 'Pictures' / 'Skycam'),
            'filename_pattern': 'SkyImage-{timestamp}',
            'timestamp_format': 'YYYY-MM-DD_HH:MM:SS',
            'auto_detect_camera': True,
            'default_port': '',
            'auto_adjust_settings': True,
            'warn_on_adjustment': True,
            'max_retries': 3
        }
        
        if not self.config_file.exists():
            self.save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Merge with defaults for missing keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            
            return config
            
        except yaml.YAMLError as e:
            print(f"Warning: Invalid config file {self.config_file}: {e}")
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary
        """
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
    
    def get_template_manager(self) -> TemplateManager:
        """Get configured template manager.
        
        Returns:
            TemplateManager instance
        """
        config = self.load_config()
        templates_dir = config.get('templates_directory')
        return TemplateManager(templates_dir=templates_dir, config_dir=str(self.config_dir))
