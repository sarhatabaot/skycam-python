# Skycam Python Design Document

## Overview

This document outlines the design for the Skycam Python rewrite, which replaces the MATLAB-based system for DSLR camera control in astrophotography. The new system provides a modern CLI interface with template-based configuration management.

## Analysis of Existing MATLAB System

### Original Implementation Structure

The original MATLAB system (`old-matlab/`) provided:

#### Core Components
- **Main Class**: `Skycam` - Handles camera operations and state management
- **Connection Manager**: `connect.m` - Camera initialization and configuration
- **Capture Controller**: `start.m` - Initiates continuous capture mode
- **File Organizer**: `bin/checkfiles.sh` - Monitors and renames captured images
- **Exposure Logic**: `private/takeExposure.m` - Individual exposure handling

#### Supported Camera Types
1. **DSLR Cameras** (Canon, Nikon, etc.)
   - Backend: `gphoto2` via MATLAB wrapper
   - Format: RAW files (.nef)
   - Live View: Required plot window for proper operation
   - File Management: Bash script monitoring for `capt**.nef` files

2. **Astronomical Cameras** (QHY CCD)
   - Backend: `LAST_QHYccd` library
   - Control: Timer-based exposure system
   - Features: Temperature monitoring, direct integration

#### Key MATLAB Workflow
```matlab
% User workflow
P = Skycam;
P.CameraType = 'DSLR';
P.ExpTime = 8;
P.F_Number = 1.4;
P.Delay = 12;
P.connect;
P.start;  % Begin continuous capture
P.stop;   % Stop capture
P.disconnect;  % Clean shutdown
```

#### Limitations Identified
- Limited error handling and recovery mechanisms
- File naming race conditions in bash monitoring
- Complex MATLAB dependency requirements
- No template or configuration management
- Hard-coded file organization system

## New Python Architecture

### Design Principles

1. **Modern CLI Interface**: Clean, intuitive command-line experience
2. **Template System**: Reusable configuration profiles for different scenarios
3. **Configuration Management**: Persistent settings with user customization
4. **Robust Error Handling**: Comprehensive validation and recovery
5. **Future-Ready**: Extensible design for web UI integration

### Core Components

#### 1. CLI Interface (`skycam-cli`)
- **Framework**: Click or Typer for modern CLI experience
- **Commands**: 
  - `start` - Begin capture session
  - `stop` - Stop ongoing capture
  - `status` - Show current status
  - `templates` - Template management operations

#### 2. Camera Control Layer (`skycam-common`)
- **Library**: Python `gphoto2` bindings
- **Responsibilities**:
  - Camera detection and connection
  - Settings configuration and validation
  - Exposure control and timing
  - Live view management

#### 3. Configuration System
- **Format**: YAML for templates and settings
- **Locations**: User-configurable, default `~/.config/skycam/`
- **Features**: Default templates, custom overrides, validation

#### 4. Template Management
- **Storage**: YAML files with reusable configurations
- **Override System**: CLI flags can override template settings
- **Validation**: Camera capability checking with auto-adjustment warnings

## File Structure

### Configuration Layout
```
~/.config/skycam/
├── config.yml              # Main configuration
├── templates/              # Template directory
│   ├── default.yml         # Default template
│   ├── night-sky.yml
│   ├── milky-way.yml
│   └── aurora.yml
└── cache/                 # Runtime cache
    └── camera-caps.json   # Cached camera capabilities
```

### Template File Format

#### Template Structure (YAML)
```yaml
# ~/.config/skycam/templates/night-sky.yml
name: "Night Sky Photography"
description: "Long exposure settings for deep sky imaging"

# Camera Settings
aperture: 1.4
exposure: 8.0
delay: 12
iso: auto
quality: raw

# File Naming
filename_pattern: "SkyImage-{timestamp}"
timestamp_format: "YYYY-MM-DD_HH:MM:SS"

# Session Settings
max_exposures: 0          # 0 = unlimited
temperature_monitoring: false
```

#### Main Configuration
```yaml
# ~/.config/skycam/config.yml
default_template: "default"
templates_directory: "~/.config/skycam/templates"
output_directory: "~/Pictures/Skycam"
filename_pattern: "SkyImage-{timestamp}"
timestamp_format: "YYYY-MM-DD_HH:MM:SS"

# Camera Settings
auto_detect_camera: true
default_port: ""          # Empty = auto-detect

# Error Handling
auto_adjust_settings: true
warn_on_adjustment: true
max_retries: 3
```

## CLI Interface Design

### Command Structure

#### Primary Commands
```bash
# Start capture session
skycam-cli start [OPTIONS]

# Stop ongoing session
skycam-cli stop [OPTIONS]

# Check current status
skycam-cli status

# Template management
skycam-cli templates list
skycam-cli templates create <name>
skycam-cli templates edit <name>
skycam-cli templates delete <name>
skycam-cli templates show <name>

# Configuration
skycam-cli config init
skycam-cli config show
skycam-cli config edit
```

#### Start Command Options
```bash
# Use template
skycam-cli start --template night-sky
skycam-cli start --template /path/to/custom.yml

# Direct settings override
skycam-cli start --exposure 15 --aperture 2.8 --delay 20
skycam-cli start --iso 800 --quality raw

# Template with overrides
skycam-cli start --template night-sky --exposure 10

# Advanced options
skycam-cli start --max-exposures 100 --output-dir /custom/path
skycam-cli start --port /dev/ttyUSB0 --dry-run
```

## Technical Implementation Details

### Camera Control Flow

#### 1. Initialization
```python
# Query camera capabilities
camera = GPhoto2Camera()
capabilities = camera.get_capabilities()

# Load template and apply validation
settings = load_template('night-sky.yml')
validated_settings = validate_and_adjust_settings(settings, capabilities)
```

#### 2. Connection Process
```python
# Auto-detect or specified port
camera.connect(port=config.get('default_port'))

# Configure camera
camera.set_config({
    'shutterspeed': validated_settings['exposure'],
    'aperture': validated_settings['aperture'],
    'iso': validated_settings['iso'],
    'imagequality': validated_settings['quality']
})

# Start live view (required for DSLR)
camera.start_live_view()
```

#### 3. Capture Loop
```python
# Continuous capture with file monitoring
with FileMonitor(output_dir) as monitor:
    for i in range(max_exposures):
        camera.capture()
        monitor.wait_for_new_file(timeout=120)
        rename_with_timestamp(monitor.latest_file, settings)
        
        # Delay between exposures
        time.sleep(validated_settings['delay'])
```

### File Management System

#### Naming Convention
- **Pattern**: Configurable template with timestamp substitution
- **Supported Tokens**:
  - `{timestamp}` → `2026-01-20_09-55-29`
  - `{date}` → `2026-01-20`
  - `{time}` → `09-55-29`
  - `{sequence}` → `001`, `002`, etc.
  - `{name}` → Template name

#### Directory Organization
```
~/Pictures/Skycam/
├── 2026-01-20/
│   ├── SkyImage-2026-01-20_09-55-29.nef
│   ├── SkyImage-2026-01-20_10-07-31.nef
│   └── session.log
├── 2026-01-21/
│   └── SkyImage-2026-01-21_20-15-42.nef
└── templates/
    └── backup/
```

### Validation and Error Handling

#### Settings Validation
```python
def validate_and_adjust_settings(settings, capabilities):
    validated = {}
    warnings = []
    
    # Check exposure time
    if settings['exposure'] in capabilities['exposure_times']:
        validated['exposure'] = settings['exposure']
    else:
        closest = find_closest_value(settings['exposure'], 
                                   capabilities['exposure_times'])
        validated['exposure'] = closest
        warnings.append(f"Exposure adjusted from {settings['exposure']}s to {closest}s")
    
    # Check aperture
    if settings['aperture'] in capabilities['apertures']:
        validated['aperture'] = settings['aperture']
    else:
        closest = find_closest_value(settings['aperture'], 
                                   capabilities['apertures'])
        validated['aperture'] = closest
        warnings.append(f"Aperture adjusted from f/{settings['aperture']} to f/{closest}")
    
    return validated, warnings
```

#### Error Recovery
- **Connection Timeout**: Retry with exponential backoff
- **Camera Busy**: Wait and retry with configurable timeout
- **File System Errors**: Graceful handling with user notification
- **Temperature Monitoring**: Optional sensor integration with warnings

### Integration Points

#### Web UI Future Compatibility
```python
# API-ready design for future web interface
class SkycamService:
    def start_session(self, template_name, overrides=None):
        # Returns session ID for web UI tracking
        
    def stop_session(self, session_id):
        # Graceful stop with cleanup
        
    def get_status(self, session_id):
        # Real-time status updates
```

#### Docker Considerations
- **CLI**: Runs natively (USB camera access required)
- **Web Service**: Container-ready for future web UI
- **Configuration**: Volume mount for persistent templates/settings

## Migration from MATLAB

### Feature Parity
| MATLAB Feature | Python Implementation |
|---------------|----------------------|
| `P.CameraType = 'DSLR'` | Automatic detection, manual override |
| `P.ExpTime = 8` | `--exposure 8` or template setting |
| `P.F_Number = 1.4` | `--aperture 1.4` or template setting |
| `P.Delay = 12` | `--delay 12` or template setting |
| `P.connect` | Automatic in `skycam-cli start` |
| `P.start` | `skycam-cli start` command |
| `P.stop` | `skycam-cli stop` command |
| `P.disconnect` | Automatic cleanup |

### Improvements Over MATLAB
1. **No MATLAB Dependency**: Pure Python implementation
2. **Template System**: Reusable configurations vs. manual property setting
3. **Better Error Handling**: Comprehensive validation and recovery
4. **Modern CLI**: Intuitive command-line interface
5. **Configuration Management**: Persistent settings vs. session-only
6. **File Organization**: Structured directories vs. flat bash script
7. **Cross-Platform**: Works on Linux, macOS, Windows (with drivers)

## Development Roadmap

### Phase 1: Core Implementation
- [x] Basic CLI structure with start/stop commands
- [x] GPhoto2 integration and camera detection
- [x] Template loading and validation system

### Phase 2: Advanced Features
- [ ] Configuration management system
- [ ] Template creation and editing commands
- [ ] Comprehensive error handling and recovery
- [ ] Progress tracking and status reporting

### Phase 3: Polish and Integration
- [ ] Temperature sensor integration (optional)
- [ ] Web API preparation
- [ ] Documentation and user guides
- [ ] Testing and validation

### Future Enhancements
- [ ] Web UI interface
- [ ] Cloud storage integration
- [ ] Advanced image processing pipeline
- [ ] Multi-camera support

## Dependencies

### Core Libraries
- **Camera Control**: `gphoto2` Python bindings
- **CLI Framework**: Click or Typer
- **Configuration**: PyYAML
- **File Monitoring**: watchdog
- **Date/Time**: python-dateutil

### Development Tools
- **Testing**: pytest
- **Code Quality**: black, flake8, mypy
- **Documentation**: Sphinx

## Conclusion

The Python rewrite provides a modern, maintainable replacement for the MATLAB system while preserving all functionality and adding significant improvements in usability, error handling, and extensibility. The template-based approach makes it particularly user-friendly for different types of astrophotography sessions, while the robust CLI interface provides professional-grade camera control capabilities.
