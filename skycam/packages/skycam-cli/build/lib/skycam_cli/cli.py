import typer
from rich import print
from typing import Optional

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
    
    if dry_run:
        print("🔍 Dry run mode - showing configuration:")
    
    # TODO: Implement actual capture logic
    print("📸 Capture configuration:")
    if template:
        print(f"  Template: {template}")
    if exposure:
        print(f"  Exposure: {exposure}s")
    if aperture:
        print(f"  Aperture: f/{aperture}")
    if delay:
        print(f"  Delay: {delay}s")
    if iso:
        print(f"  ISO: {iso}")
    if output_dir:
        print(f"  Output: {output_dir}")
    if max_exposures is not None:
        print(f"  Max exposures: {max_exposures}")

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
    print("  Camera: Not connected")
    print("  Active sessions: 0")
    
    # TODO: Implement actual status checking
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
