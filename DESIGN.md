# Skycam Python - Technical Design Document

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Module](#core-module)
4. [CLI Module](#cli-module)
5. [Web Module](#web-module)
6. [Monitoring & Prometheus](#monitoring--prometheus)
7. [Configuration](#configuration)
8. [Data Flow](#data-flow)
9. [Security](#security)
10. [Deployment](#deployment)
11. [Testing Strategy](#testing-strategy)

## Overview

Skycam is a Python-based automated night sky photography system that provides:
- **Dual Interface**: CLI for power users, Django web UI for monitoring
- **Hardware Support**: DSLR cameras via gphoto2, temperature sensors via serial
- **Real-time Monitoring**: Prometheus metrics with Grafana dashboards
- **Modular Design**: Core business logic shared between interfaces

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │   Web Layer     │    │  Monitoring     │
│                 │    │                 │    │                 │
│ • Click Commands│    │ • Django Views  │    │ • Prometheus    │
│ • Rich UI       │    │ • REST API      │    │ • Grafana       │
│ • Real-time     │    │ • WebSockets    │    │ • Alerting      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Core Module           │
                    │                            │
                    │ • Camera Manager          │
                    │ • Temperature Monitor     │
                    │ • Image Organizer         │
                    │ • Configuration Manager   │
                    │ • Event System            │
                    │ • Process Manager         │
                    └────────────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Hardware Layer       │
                    │                            │
                    │ • gphoto2 (DSLR)         │
                    │ • Serial Sensors         │
                    │ • File System            │
                    └────────────────────────────┘
```

## Core Module

### 1. Camera Manager (`core/camera/`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio

@dataclass
class CameraConfig:
    exposure_time: float = 8.0  # seconds
    f_number: float = 1.4
    delay: float = 12.0  # seconds between captures
    image_path: str = "/home/skycam/"
    port: Optional[str] = None

class CameraManager(ABC):
    @abstractmethod
    async def connect(self, config: CameraConfig) -> bool:
        """Connect to camera"""
        pass
    
    @abstractmethod
    async def start_capture(self) -> None:
        """Start continuous capture"""
        pass
    
    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop continuous capture"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get camera status"""
        pass

class DSLRManager(CameraManager):
    def __init__(self):
        self.gphoto_process = None
        self.config = None
        self.is_capturing = False
    
    async def connect(self, config: CameraConfig) -> bool:
        """Connect DSLR via gphoto2"""
        # Implementation details...
        pass
```

### 2. Temperature Monitor (`core/sensor/`)

```python
import serial
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class SensorConfig:
    sensor_type: str = "digitemp"  # or "arduino"
    port: Optional[str] = None
    baud_rate: int = 9600
    sampling_interval: float = 2.0

class TemperatureMonitor:
    def __init__(self, config: SensorConfig):
        self.config = config
        self.serial_connection: Optional[serial.Serial] = None
        self.callbacks: list[Callable] = []
        self.is_monitoring = False
    
    async def start_monitoring(self) -> None:
        """Start temperature monitoring"""
        # Implementation details...
        pass
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for temperature updates"""
        self.callbacks.append(callback)
```

### 3. Image Organizer (`core/image/`)

```python
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional

class ImageOrganizer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories"""
        today = datetime.now().strftime("%Y/%m/%d")
        self.image_dir = self.base_path / today / "raw"
        self.image_dir.mkdir(parents=True, exist_ok=True)
    
    def organize_new_files(self) -> List[str]:
        """Move and rename newly captured images"""
        # Implementation for file management...
        pass
```

### 4. Configuration Manager (`core/config/`)

```python
import yaml
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass, asdict

@dataclass
class SkycamConfig:
    camera: CameraConfig
    sensor: SensorConfig
    monitoring: Dict[str, Any]
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'SkycamConfig':
        """Load configuration from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file"""
        with open(path, 'w') as f:
            yaml.dump(asdict(self), f)

class ConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> SkycamConfig:
        """Load configuration with defaults"""
        # Implementation...
        pass
```

### 5. Prometheus Metrics (`core/monitoring/`)

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import asyncio
from typing import Dict, Any

class SkycamMetrics:
    def __init__(self):
        # Counters
        self.images_captured = Counter(
            'skycam_images_captured_total',
            'Total number of images captured'
        )
        
        self.capture_errors = Counter(
            'skycam_capture_errors_total',
            'Total number of capture errors',
            ['error_type']
        )
        
        # Gauges
        self.camera_temperature = Gauge(
            'skycam_camera_temperature_celsius',
            'Camera temperature in Celsius'
        )
        
        self.capture_duration = Histogram(
            'skycam_capture_duration_seconds',
            'Time taken for each capture'
        )
        
        self.sensor_temperature = Gauge(
            'skycam_sensor_temperature_celsius',
            'External sensor temperature'
        )
        
        self.active_captures = Gauge(
            'skycam_active_captures',
            'Number of active capture sessions'
        )
    
    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics HTTP server"""
        start_http_server(port)
```

## CLI Module

### Command Structure (`cli/commands/`)

```python
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from core.camera.dslr_manager import DSLRManager
from core.config.config_manager import ConfigManager

console = Console()

@click.group()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Skycam - Automated DSLR night sky photography"""
    ctx.ensure_object(dict)
    ctx.obj['config_manager'] = ConfigManager(config)
    ctx.obj['camera_manager'] = DSLRManager()

@cli.command()
@click.pass_context
def connect(ctx):
    """Connect to DSLR camera"""
    # Implementation...
    pass

@cli.command()
@click.option('--exposure', '-e', type=float, help='Exposure time in seconds')
@click.option('--delay', '-d', type=float, help='Delay between captures')
@click.option('--f-number', '-f', type=float, help='F-number')
@click.pass_context
def start(ctx, exposure, delay, f_number):
    """Start continuous capture"""
    # Implementation...
    pass

@cli.command()
def status():
    """Show current status"""
    table = Table(title="Skycam Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Add status rows...
    
    console.print(table)

@cli.command()
def stop():
    """Stop current capture session"""
    # Implementation...
    pass
```

## Web Module

### Django Project Structure

```
web/
├── manage.py
├── skycam_project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── skycam_web/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── consumers.py  # WebSocket consumers
├── api/
│   ├── __init__.py
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── gallery.html
    └── status.html
```

### API Views (`api/views.py`)

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CameraViewSet(viewsets.ViewSet):
    """Camera control endpoints"""
    
    @action(detail=False, methods=['post'])
    def connect(self, request):
        """Connect to camera"""
        # Implementation...
        pass
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start capture session"""
        # Implementation...
        pass
    
    @action(detail=False, methods=['post'])
    def stop(self, request):
        """Stop capture session"""
        # Implementation...
        pass
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current camera status"""
        # Implementation...
        pass

class CaptureConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time updates"""
    
    async def connect(self):
        await self.channel_layer.group_add(
            "captures",
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "captures",
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        
        if message_type == "capture_update":
            await self.send(text_data=json.dumps({
                'type': 'capture_update',
                'data': text_data_json['data']
            }))
```

### Dashboard Template (`templates/dashboard.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Skycam Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
    <div class="dashboard-container">
        <div class="status-panel">
            <h2>Camera Status</h2>
            <div id="camera-status">Loading...</div>
        </div>
        
        <div class="metrics-panel">
            <h2>Real-time Metrics</h2>
            <canvas id="temperature-chart"></canvas>
        </div>
        
        <div class="controls-panel">
            <h2>Controls</h2>
            <button id="start-capture">Start Capture</button>
            <button id="stop-capture">Stop Capture</button>
            <button id="connect-camera">Connect Camera</button>
        </div>
        
        <div class="gallery-panel">
            <h2>Recent Images</h2>
            <div id="image-gallery"></div>
        </div>
    </div>
    
    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8000/ws/captures/');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'capture_update') {
                updateCameraStatus(data.data);
                updateTemperatureChart(data.data.temperature);
                updateImageGallery(data.data.latest_image);
            }
        };
    </script>
</body>
</html>
```

## Monitoring & Prometheus

### Metrics Collection

```python
# core/monitoring/metrics_collector.py
import asyncio
import time
from prometheus_client import start_http_server
from .metrics import SkycamMetrics

class MetricsCollector:
    def __init__(self, camera_manager, sensor_monitor):
        self.camera_manager = camera_manager
        self.sensor_monitor = sensor_monitor
        self.metrics = SkycamMetrics()
        self.running = False
    
    async def start_collection(self):
        """Start collecting and publishing metrics"""
        self.running = True
        
        # Start Prometheus HTTP server
        self.metrics.start_metrics_server(8000)
        
        # Collect metrics every 5 seconds
        while self.running:
            try:
                # Camera metrics
                status = await self.camera_manager.get_status()
                if status.get('temperature'):
                    self.metrics.camera_temperature.set(status['temperature'])
                
                if status.get('is_capturing'):
                    self.metrics.active_captures.set(1)
                else:
                    self.metrics.active_captures.set(0)
                
                # Sensor metrics
                if self.sensor_monitor.is_monitoring:
                    temp = await self.sensor_monitor.get_latest_temperature()
                    if temp:
                        self.metrics.sensor_temperature.set(temp)
                
                await asyncio.sleep(5)
            except Exception as e:
                self.metrics.capture_errors.labels(error_type='metrics_collection').inc()
                await asyncio.sleep(5)
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.running = False
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Skycam Monitoring",
    "panels": [
      {
        "title": "Images Captured",
        "type": "stat",
        "targets": [
          {
            "expr": "skycam_images_captured_total",
            "legendFormat": "Total Images"
          }
        ]
      },
      {
        "title": "Camera Temperature",
        "type": "graph",
        "targets": [
          {
            "expr": "skycam_camera_temperature_celsius",
            "legendFormat": "Camera Temp"
          }
        ]
      },
      {
        "title": "Capture Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "skycam_capture_duration_seconds",
            "legendFormat": "Capture Time"
          }
        ]
      }
    ]
  }
}
```

## Configuration

### YAML Configuration File

```yaml
# config/skycam.yaml
camera:
  type: "dslr"  # or "astro"
  exposure_time: 8.0
  f_number: 1.4
  delay: 12.0
  image_path: "/home/skycam/images/"
  port: null  # null for auto-detect

sensor:
  type: "digitemp"  # or "arduino"
  port: null
  baud_rate: 9600
  sampling_interval: 2.0

monitoring:
  prometheus:
    enabled: true
    port: 8000
  grafana:
    enabled: true
    dashboard_path: "dashboards/skycam.json"

logging:
  level: "INFO"
  file: "/var/log/skycam.log"
  max_size: "10MB"
  backup_count: 5

web:
  host: "0.0.0.0"
  port: 8080
  debug: false
  secret_key: "${DJANGO_SECRET_KEY}"

cli:
  output_format: "rich"  # or "json"
  verbose: false
```

### Environment Variables

```bash
# .env file
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
PROMETHEUS_PORT=8000
WEB_PORT=8080
CAMERA_PORT=/dev/ttyUSB0
```

## Data Flow

### Capture Session Flow

```
1. User initiates capture via CLI/Web
   ↓
2. Core validates configuration
   ↓
3. Camera manager sets parameters
   ↓
4. Image organizer prepares directories
   ↓
5. Capture session starts
   ↓
6. Loop:
   - Camera captures image
   - Image organizer renames/saves
   - Metrics updated (Prometheus)
   - WebSocket notification sent
   - Wait for delay period
   ↓
7. Session stops (user command or error)
   ↓
8. Cleanup and final metrics update
```

### Real-time Update Flow

```
Hardware Event
     ↓
Core Module Event
     ↓
Metrics Update (Prometheus)
     ↓
WebSocket Broadcast
     ↓
Web UI Update
     ↓
User Notification
```

## Security

### Web Security

```python
# web/skycam_project/security.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# API Security
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

### CLI Security

```python
# cli/security.py
import click
from functools import wraps

def require_privileged_operation(f):
    """Decorator for operations requiring elevated privileges"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if os.geteuid() !=
