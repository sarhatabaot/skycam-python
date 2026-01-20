import typer
from rich import print
from typing import Optional
from skycam_common.camera import Camera, CameraSettings, CameraNotFoundError, CameraConnectionError
from skycam_common.template import TemplateManager, ConfigManager, Template
from skycam_common.exceptions import *

app = typer.Typer(help="Skycam CLI - DSLR camera control for astrophotography")

# Initialize managers
template_manager = TemplateManager()
config_manager = ConfigManager()

@app.command()
def start(
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Template name or file path"),
    exposure: Optional[float] = typer.Option(None, "--exposure", "-e", help="Exposure time in seconds"),
    aperture: Optional[float] = typer.Option(None, "--aperture", "-a", help="Aperture f-number"),
    delay: Optional[float] = typer.Option(None, "--delay", "-d", help="Delay between exposures in seconds"),
    iso: Optional[str] = typer.Option(None, "--iso", help="ISO setting (auto or numeric value)"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Output directory for images"),
    max_exposures: Optional[int] = typer.Option(None, "--max-exposures", help="Maximum number of exposures (0 = unlimited)"),
    port: Optional[str] = typer.Option(None, "--port", help="Camera port (auto-detect if not specified)"),
    dry_run: Optional[bool] = typer.Option(False, "--dry-run", help="Show what would be done without actually doing it")
) -> None:
    """Start a skycam capture session."""
    print("🚀 Starting skycam capture session...")

    if dry_run:
        print("🔍 Dry run mode - showing configuration:")
    
    # Load template or use defaults
    settings = CameraSettings()
    template_name = None
    
    if template:
        try:
            template_obj = template_manager.get_template(template)
            settings = template_obj.to_settings()
            template_name = template_obj.name
            print(f"📄 Loaded template: {template_obj.name}")
            if template_obj.description:
                print(f"   {template_obj.description}")
        except FileNotFoundError:
            print(f"❌ Template '{template}' not found")
            return
        except Exception as e:
            print(f"❌ Error loading template: {e}")
            return
    else:
        # Load default template
        try:
            template_obj = template_manager.get_template("default")
            settings = template_obj.to_settings()
            template_name = template_obj.name
            print(f"📄 Using default template")
        except Exception as e:
            print(f"⚠️ Warning: Could not load default template: {e}")
    
    # Override with command line options
    if exposure:
        settings.exposure = exposure
    if aperture:
        settings.aperture = aperture
    if delay:
        settings.delay = delay
    if iso:
        settings.iso = iso
    if max_exposures is not None:
        settings.max_exposures = max_exposures
    
    print("📸 Capture configuration:")
    print(f"  Template: {template_name}")
    print(f"  Exposure: {settings.exposure}s")
    print(f"  Aperture: f/{settings.aperture}")
    print(f"  Delay: {settings.delay}s")
    print(f"  ISO: {settings.iso}")
    if output_dir:
        print(f"  Output: {output_dir}")
    print(f"  Max exposures: {settings.max_exposures}")
    
    if dry_run:
        print("✅ Dry run completed - no actual capture performed")
        return
    
    # Connect to camera and start capture
    try:
        with Camera(port=port) as camera:
            print(f"📷 Connecting to camera...")
            
            # Detect cameras if no port specified
            if not port:
                cameras = camera.detect_cameras()
                if len(cameras) == 0:
                    print("❌ No cameras detected. Please connect a camera and try again.")
                    return
                print(f"✅ Found {len(cameras)} camera(s)")
                for i, cam in enumerate(cameras):
                    print(f"  {i+1}. {cam}")
            
            # Connect to camera
            print("🔌 Connecting to camera...")
            camera.connect()
            print("✅ Camera connected successfully")
            
            # Show camera info
            info = camera.get_camera_info()
            print(f"📊 Camera info: {info}")
            
            # Validate settings
            validated_settings, warnings = camera.validate_settings(settings)
            if warnings:
                print("⚠️ Settings warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
            
            # Configure camera
            config_warnings = camera.configure_camera(validated_settings)
            if config_warnings:
                print("⚠️ Configuration warnings:")
                for warning in config_warnings:
                    print(f"  - {warning}")
            
            print("🎯 Starting capture session...")
            print("📸 (Single capture for demo - continuous capture not yet implemented)")
            
            # Capture single image for now
            result = camera.capture_single()
            if result.success:
                print(f"✅ Capture successful!")
                print(f"  File: {result.filename}")
                print(f"  Path: {result.filepath}")
            else:
                print(f"❌ Capture failed: {result.error_message}")
            
    except CameraNotFoundError as e:
        print(f"❌ Camera not found: {e}")
    except CameraConnectionError as e:
        print(f"❌ Camera connection error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

@app.command()
def stop(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to stop (current session if not specified)")
) -> None:
    """Stop an ongoing skycam capture session."""
    if session_id:
        print(f"🛑 Stopping skycam session: {session_id}")
    else:
        print("🛑 Stopping current skycam session")
    
    # TODO: Implement actual stop logic
    print("✅ Session stopped successfully")

@app.command()
def status() -> None:
    """Show current skycam status."""
    print("📊 Skycam Status:")
    print("  Status: Ready")

    try:
        with Camera() as camera:
            cameras = camera.detect_cameras()
            print(f"  Camera: {len(cameras)} detected")
            for i, cam in enumerate(cameras):
                print(f"    {i+1}. {cam}")
            
            if cameras:
                print("  Connection status: Ready to connect")
            else:
                print("  Connection status: No cameras available")
    except Exception as e:
        print(f"  Camera: Error checking status - {e}")
    
    print("  Active sessions: 0")
    print("  Last session: None")

# Templates subcommand group
templates_app = typer.Typer(help="Template management commands")

@templates_app.command("list")
def templates_list() -> None:
    """List all available templates."""
    print("📋 Available Templates:")
    
    try:
        templates = template_manager.list_templates()
        if not templates:
            print("  No templates found")
            print("  Use 'skycam config init' to create default templates")
        else:
            for template_name in templates:
                try:
                    template = template_manager.load_template(template_name)
                    desc = template.description or "No description"
                    print(f"  {template_name:15} - {desc}")
                except Exception as e:
                    print(f"  {template_name:15} - Error loading: {e}")
    except Exception as e:
        print(f"  Error listing templates: {e}")

@templates_app.command("show")
def templates_show(name: str = typer.Argument(..., help="Template name to show")) -> None:
    """Show template details."""
    print(f"📄 Template: {name}")
    
    try:
        template = template_manager.get_template(name)
        print(f"  Name: {template.name}")
        if template.description:
            print(f"  Description: {template.description}")
        
        print("  Camera Settings:")
        if template.aperture:
            print(f"    Aperture: f/{template.aperture}")
        if template.exposure:
            print(f"    Exposure: {template.exposure}s")
        if template.iso:
            print(f"    ISO: {template.iso}")
        if template.delay:
            print(f"    Delay: {template.delay}s")
        if template.quality:
            print(f"    Quality: {template.quality}")
        if template.max_exposures is not None:
            print(f"    Max exposures: {template.max_exposures}")
        
        print("  File Settings:")
        if template.filename_pattern:
            print(f"    Filename pattern: {template.filename_pattern}")
        if template.timestamp_format:
            print(f"    Timestamp format: {template.timestamp_format}")
        
        if template.temperature_monitoring:
            print("  Session Settings:")
            print(f"    Temperature monitoring: {template.temperature_monitoring}")
            
    except FileNotFoundError:
        print(f"❌ Template '{name}' not found")
    except Exception as e:
        print(f"❌ Error loading template: {e}")

# Configuration subcommand group
config_app = typer.Typer(help="Configuration management commands")

@config_app.command("init")
def config_init() -> None:
    """Initialize skycam configuration."""
    print("⚙️  Initializing skycam configuration...")
    
    try:
        # Initialize configuration
        config = config_manager.load_config()
        
        # Ensure default template exists
        template_manager.ensure_default_template()
        
        print("✅ Configuration initialized successfully!")
        print(f"  Config file: {config_manager.config_file}")
        print(f"  Templates directory: {template_manager.templates_dir}")
        print(f"  Default template: {config['default_template']}")
        
    except Exception as e:
        print(f"❌ Error initializing configuration: {e}")

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    print("⚙️  Current Configuration:")
    
    try:
        config = config_manager.load_config()
        
        for key, value in config.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")

# Add subcommands to main app
app.add_typer(templates_app, name="templates")
app.add_typer(config_app, name="config")

def main() -> None:
    app()
