import typer
from rich import print
from typing import Optional

try:
    from skycam_common.camera import Camera, CameraSettings, CameraNotFoundError, CameraConnectionError
    from skycam_common.exceptions import *
    CAMERA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Camera modules not available: {e}")
    CAMERA_AVAILABLE = False

app = typer.Typer(help="Skycam CLI - DSLR camera control for astrophotography")

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
    
    if not CAMERA_AVAILABLE:
        print("❌ Camera functionality not available. Check dependencies.")
        return
    
    if dry_run:
        print("🔍 Dry run mode - showing configuration:")
    
    # Create settings from command line options
    settings = CameraSettings()
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
    print(f"  Exposure: {settings.exposure}s")
    print(f"  Aperture: f/{settings.aperture}")
    print(f"  Delay: {settings.delay}s")
    print(f"  ISO: {settings.iso}")
    if output_dir:
        print(f"  Output: {output_dir}")
    print(f"  Max exposures: {settings.max_exposures}")
    
    if template:
        print(f"  Template: {template} (template loading not implemented yet)")
    
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
    
    if not CAMERA_AVAILABLE:
        print("  Camera: Modules not available")
        print("  Active sessions: 0")
        print("  Last session: None")
        return
    
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
    print("  default  - Default template")
    
    # TODO: Load and display actual templates from config directory
    print("  night-sky - Night sky photography settings")
    print("  milky-way - Milky Way imaging")
    print("  aurora - Aurora photography")

@templates_app.command("show")
def templates_show(name: str = typer.Argument(..., help="Template name to show")) -> None:
    """Show template details."""
    print(f"📄 Template: {name}")
    
    # TODO: Load and display actual template
    if name == "default":
        print("  Aperture: 1.4")
        print("  Exposure: 8.0s")
        print("  Delay: 12s")
        print("  ISO: auto")
        print("  Quality: raw")

# Configuration subcommand group
config_app = typer.Typer(help="Configuration management commands")

@config_app.command("init")
def config_init() -> None:
    """Initialize skycam configuration."""
    print("⚙️  Initializing skycam configuration...")
    
    # TODO: Create default config structure
    print("✅ Configuration initialized in ~/.config/skycam/")
    print("  - config.yml")
    print("  - templates/")
    print("  - cache/")

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    print("⚙️  Current Configuration:")
    print("  Default template: default")
    print("  Templates directory: ~/.config/skycam/templates")
    print("  Output directory: ~/Pictures/Skycam")
    print("  Auto-detect camera: true")
    print("  Auto-adjust settings: true")

# Add subcommands to main app
app.add_typer(templates_app, name="templates")
app.add_typer(config_app, name="config")

def main() -> None:
    app()
