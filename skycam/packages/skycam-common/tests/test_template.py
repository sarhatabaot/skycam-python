"""Tests for the template module."""

import pytest
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from unittest.mock import mock_open

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from skycam_common.template import Template, TemplateManager, ConfigManager
from skycam_common.camera import CameraSettings, CameraCapabilities


class TestTemplate:
    """Test Template dataclass."""
    
    def test_default_template(self):
        """Test default template creation."""
        template = Template(name="test-template")
        
        assert template.name == "test-template"
        assert template.description is None
        assert template.aperture is None
        assert template.exposure is None
        assert template.iso is None
        assert template.delay is None
        assert template.quality is None
        assert template.max_exposures is None
        assert template.filename_pattern is None
        assert template.timestamp_format is None
        assert template.temperature_monitoring is None
    
    def test_complete_template(self):
        """Test template with all fields populated."""
        template = Template(
            name="complete-template",
            description="A complete test template",
            aperture=2.8,
            exposure=15.0,
            iso="800",
            delay=10.0,
            quality="raw",
            max_exposures=50,
            filename_pattern="SkyImage-{timestamp}",
            timestamp_format="YYYY-MM-DD_HH:MM:SS",
            temperature_monitoring=True
        )
        
        assert template.name == "complete-template"
        assert template.description == "A complete test template"
        assert template.aperture == 2.8
        assert template.exposure == 15.0
        assert template.iso == "800"
        assert template.delay == 10.0
        assert template.quality == "raw"
        assert template.max_exposures == 50
        assert template.filename_pattern == "SkyImage-{timestamp}"
        assert template.timestamp_format == "YYYY-MM-DD_HH:MM:SS"
        assert template.temperature_monitoring is True
    
    def test_template_to_settings(self):
        """Test template conversion to CameraSettings."""
        template = Template(
            name="test-template",
            aperture=1.4,
            exposure=8.0,
            iso="auto",
            delay=12.0,
            quality="raw",
            max_exposures=0
        )
        
        settings = template.to_settings()
        
        assert isinstance(settings, CameraSettings)
        assert settings.exposure == 8.0
        assert settings.aperture == 1.4
        assert settings.iso == "auto"
        assert settings.delay == 12.0
        assert settings.quality == "raw"
        assert settings.max_exposures == 0
    
    def test_template_to_settings_with_defaults(self):
        """Test template conversion with missing values (uses defaults)."""
        template = Template(name="minimal-template")
        
        settings = template.to_settings()
        
        # Should use defaults for missing values
        assert settings.exposure == 8.0
        assert settings.aperture == 1.4
        assert settings.iso == "auto"
        assert settings.delay == 12.0
        assert settings.quality == "raw"
        assert settings.max_exposures == 0
    
    def test_template_validate_no_capabilities(self):
        """Test template validation without camera capabilities."""
        template = Template(
            name="test-template",
            aperture=2.8,
            exposure=15.0,
            iso="800",
            filename_pattern="SkyImage-{timestamp}"
        )
        
        warnings = template.validate()
        
        # Should only validate filename pattern without capabilities
        assert len(warnings) == 0
    
    def test_template_validate_with_capabilities(self):
        """Test template validation with camera capabilities."""
        capabilities = CameraCapabilities(
            exposure_times=[0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0],
            apertures=[1.4, 2.0, 2.8, 4.0, 5.6, 8.0],
            iso_values=["auto", "100", "200", "400", "800", "1600"]
        )
        
        # Template with exact matches
        template_exact = Template(
            name="exact-template",
            aperture=2.8,
            exposure=15.0,
            iso="800"
        )
        
        warnings = template_exact.validate(capabilities)
        assert len(warnings) == 0
        
        # Template with non-matching values
        template_adjust = Template(
            name="adjust-template",
            aperture=2.6,  # Not in capabilities, closest is 2.8
            exposure=12.0,  # Not in capabilities, closest is 15.0
            iso="600"  # Not in capabilities
        )
        
        warnings = template_adjust.validate(capabilities)
        assert len(warnings) == 3
        assert "Exposure 12.0s not available" in warnings[0]
        assert "Aperture f/2.6 not available" in warnings[1]
        assert "ISO 600 may not be supported" in warnings[2]
    
    def test_template_validate_filename_pattern(self):
        """Test template filename pattern validation."""
        template_good = Template(
            name="good-template",
            filename_pattern="SkyImage-{timestamp}"
        )
        
        warnings = template_good.validate()
        assert len(warnings) == 0
        
        template_bad = Template(
            name="bad-template",
            filename_pattern="SkyImage"  # Missing {timestamp}
        )
        
        warnings = template_bad.validate()
        assert len(warnings) == 1
        assert "filename_pattern should include {timestamp}" in warnings[0]
    
    def test_template_to_dict(self):
        """Test template serialization to dictionary."""
        template = Template(
            name="test-template",
            description="Test description",
            aperture=1.4,
            exposure=8.0,
            iso="auto"
        )
        
        template_dict = template.to_dict()
        
        assert isinstance(template_dict, dict)
        assert template_dict["name"] == "test-template"
        assert template_dict["description"] == "Test description"
        assert template_dict["aperture"] == 1.4
        assert template_dict["exposure"] == 8.0
        assert template_dict["iso"] == "auto"
    
    def test_template_from_dict(self):
        """Test template creation from dictionary."""
        template_dict = {
            "name": "from-dict-template",
            "description": "Created from dictionary",
            "aperture": 2.8,
            "exposure": 20.0,
            "iso": "400",
            "delay": 15.0,
            "quality": "raw",
            "max_exposures": 25
        }
        
        template = Template.from_dict(template_dict)
        
        assert template.name == "from-dict-template"
        assert template.description == "Created from dictionary"
        assert template.aperture == 2.8
        assert template.exposure == 20.0
        assert template.iso == "400"
        assert template.delay == 15.0
        assert template.quality == "raw"
        assert template.max_exposures == 25


class TestTemplateManager:
    """Test TemplateManager class."""
    
    def test_init_default_paths(self):
        """Test TemplateManager initialization with default paths."""
        manager = TemplateManager()
        
        expected_config_dir = Path.home() / ".config" / "skycam"
        expected_templates_dir = expected_config_dir / "templates"
        
        assert manager.config_dir == expected_config_dir
        assert manager.templates_dir == expected_templates_dir
        assert manager.default_template_path == expected_templates_dir / "default.yml"
    
    def test_init_custom_paths(self):
        """Test TemplateManager initialization with custom paths."""
        custom_config = "/tmp/custom/config"
        custom_templates = "/tmp/custom/templates"
        
        manager = TemplateManager(
            templates_dir=custom_templates,
            config_dir=custom_config
        )
        
        assert manager.config_dir == Path(custom_config)
        assert manager.templates_dir == Path(custom_templates)
        assert manager.default_template_path == Path(custom_templates) / "default.yml"
    
    def test_save_template(self):
        """Test template save operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TemplateManager(templates_dir=tmp_dir)
            
            template = Template(
                name="test-save-template",
                description="Template for testing save/load",
                aperture=1.8,
                exposure=12.0,
                iso="auto"
            )
            
            # Save template
            manager.save_template(template)
            
            # Verify file was created
            template_file = Path(tmp_dir) / "test-save-template.yml"
            assert template_file.exists()
            
            # Verify content
            with open(template_file, 'r') as f:
                content = f.read()
            
            assert "test-save-template" in content
            assert "Template for testing save/load" in content
            assert "aperture: 1.8" in content
            assert "exposure: 12.0" in content
    
    def test_load_template_not_found(self):
        """Test loading non-existent template."""
        manager = TemplateManager()
        
        with pytest.raises(FileNotFoundError, match="Template 'nonexistent' not found"):
            manager.load_template("nonexistent")
    
    def test_load_template_file_path(self):
        """Test loading template from file path."""
        template_content = {
            "name": "file-template",
            "description": "Loaded from file",
            "aperture": 2.0,
            "exposure": 10.0
        }
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp_file:
            yaml.dump(template_content, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            manager = TemplateManager()
            template = manager.load_template(tmp_file_path)
            
            assert template.name == "file-template"
            assert template.description == "Loaded from file"
            assert template.aperture == 2.0
            assert template.exposure == 10.0
        finally:
            os.unlink(tmp_file_path)
    
    def test_load_template_invalid_yaml(self):
        """Test loading template with invalid YAML."""
        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp_file:
            tmp_file.write("invalid: yaml: content: [")
            tmp_file_path = tmp_file.name
        
        try:
            manager = TemplateManager()
            with pytest.raises(ValueError, match="Invalid YAML"):
                manager.load_template(tmp_file_path)
        finally:
            os.unlink(tmp_file_path)
    
    def test_list_templates_empty(self):
        """Test listing templates when directory is empty."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TemplateManager(templates_dir=tmp_dir)
            templates = manager.list_templates()
            
            assert templates == []
    
    def test_list_templates_with_files(self):
        """Test listing templates with actual files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create some template files
            template1 = Path(tmp_dir) / "template1.yml"
            template2 = Path(tmp_dir) / "template2.yml"
            
            template1.write_text("name: template1")
            template2.write_text("name: template2")
            
            # Also create a non-template file
            non_template = Path(tmp_dir) / "readme.txt"
            non_template.write_text("This is not a template")
            
            manager = TemplateManager(templates_dir=tmp_dir)
            templates = manager.list_templates()
            
            assert sorted(templates) == ["template1", "template2"]
    
    def test_create_default_template(self):
        """Test creating default template."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            default_template = manager.create_default_template()
            
            assert default_template.name == "default"
            assert default_template.description == "Default skycam template for general astrophotography"
            assert default_template.aperture == 1.4
            assert default_template.exposure == 8.0
            assert default_template.iso == "auto"
            assert default_template.delay == 12.0
            assert default_template.quality == "raw"
            assert default_template.max_exposures == 0
            
            # Verify file was created
            assert (tmp_path / "default.yml").exists()
    
    def test_ensure_default_template_exists(self):
        """Test ensuring default template exists when it doesn't."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            
            # File doesn't exist initially
            assert not (tmp_path / "default.yml").exists()
            
            manager.ensure_default_template()
            
            # File should now exist
            assert (tmp_path / "default.yml").exists()
    
    def test_ensure_default_template_already_exists(self):
        """Test ensuring default template when it already exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            
            # Create existing template
            existing_template = Template(name="default", exposure=5.0)
            manager.save_template(existing_template)
            
            # Ensure it exists (should not overwrite)
            manager.ensure_default_template()
            
            # Load and verify it wasn't overwritten
            template = manager.load_template("default")
            assert template.exposure == 5.0  # Original value preserved
    
    def test_get_template_existing(self):
        """Test getting existing template."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            
            # Create a template
            original_template = Template(
                name="existing-template",
                description="Already exists",
                aperture=2.8,
                exposure=15.0
            )
            manager.save_template(original_template)
            
            # Get the template
            retrieved_template = manager.get_template("existing-template")
            
            assert retrieved_template.name == "existing-template"
            assert retrieved_template.description == "Already exists"
            assert retrieved_template.aperture == 2.8
            assert retrieved_template.exposure == 15.0
    
    def test_get_template_default_creates(self):
        """Test getting default template creates it if missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            
            # Don't create default template
            assert not (tmp_path / "default.yml").exists()
            
            # Get default template (should create it)
            default_template = manager.get_template("default")
            
            assert default_template.name == "default"
            assert (tmp_path / "default.yml").exists()
    
    def test_validate_template(self):
        """Test template validation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manager = TemplateManager(templates_dir=str(tmp_path))
            
            # Create a template with missing name
            template = Template(
                name="",  # Invalid - empty name
                aperture=2.8,
                exposure=15.0
            )
            
            capabilities = CameraCapabilities(
                exposure_times=[0.5, 1.0, 2.0, 4.0, 8.0, 15.0],
                apertures=[1.4, 2.0, 2.8, 4.0],
                iso_values=["auto", "100", "200", "400", "800"]
            )
            
            warnings = manager.validate_template(template, capabilities)
            
            # Should have warnings for empty name
            assert len(warnings) >= 1
            assert any("Template name is required" in w for w in warnings)


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_init_default_config_dir(self):
        """Test ConfigManager initialization with default config directory."""
        manager = ConfigManager()
        
        expected_config_dir = Path.home() / ".config" / "skycam"
        expected_config_file = expected_config_dir / "config.yml"
        
        assert manager.config_dir == expected_config_dir
        assert manager.config_file == expected_config_file
    
    def test_init_custom_config_dir(self):
        """Test ConfigManager initialization with custom config directory."""
        custom_config_dir = "/tmp/custom/config"
        
        manager = ConfigManager(config_dir=custom_config_dir)
        
        assert manager.config_dir == Path(custom_config_dir)
        assert manager.config_file == Path(custom_config_dir) / "config.yml"
    
    def test_load_config_new_file(self):
        """Test loading config when file doesn't exist (creates default)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = ConfigManager(config_dir=tmp_dir)
            
            # File doesn't exist
            config_file = Path(tmp_dir) / "config.yml"
            assert not config_file.exists()
            
            # Load config (should create default)
            config = manager.load_config()
            
            # Verify default config structure
            assert config["default_template"] == "default"
            assert "templates_directory" in config
            assert "output_directory" in config
            assert "filename_pattern" in config
            assert "timestamp_format" in config
            assert "auto_detect_camera" in config
            
            # Verify file was created
            assert config_file.exists()
    
    def test_load_config_existing_file(self):
        """Test loading config from existing file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yml"
            
            # Create custom config
            custom_config = {
                "default_template": "custom",
                "output_directory": "/custom/output",
                "auto_detect_camera": False
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(custom_config, f)
            
            manager = ConfigManager(config_dir=tmp_dir)
            config = manager.load_config()
            
            # Should load custom values
            assert config["default_template"] == "custom"
            assert config["output_directory"] == "/custom/output"
            assert config["auto_detect_camera"] is False
            
            # Should merge with defaults for missing keys
            assert "templates_directory" in config
            assert "filename_pattern"
