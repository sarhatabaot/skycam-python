"""Camera control module for skycam.

This module provides camera control functionality using gphoto2 bindings.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import gphoto2 as gp
except ImportError:
    gp = None


@dataclass
class CameraSettings:
    """Camera settings configuration."""
    exposure: float = 8.0
    aperture: float = 1.4
    iso: str = "auto"
    delay: float = 12.0
    quality: str = "raw"
    max_exposures: int = 0  # 0 = unlimited


@dataclass
class CameraCapabilities:
    """Camera capabilities and available settings."""
    exposure_times: List[float]
    apertures: List[float]
    iso_values: List[str]
    has_live_view: bool = True
    supports_bulb_mode: bool = False


@dataclass
class CaptureResult:
    """Result from a camera capture operation."""
    success: bool
    filename: Optional[str] = None
    filepath: Optional[str] = None
    error_message: Optional[str] = None


class CameraError(Exception):
    """Base exception for camera-related errors."""
    pass


class CameraNotFoundError(CameraError):
    """Raised when no camera is found."""
    pass


class CameraConnectionError(CameraError):
    """Raised when camera connection fails."""
    pass


class Camera:
    """Main camera control class."""
    
    def __init__(self, port: Optional[str] = None):
        """Initialize camera control.
        
        Args:
            port: Camera port (None for auto-detection)
        """
        if gp is None:
            raise ImportError("gphoto2 library not available. Install with: pip install gphoto2")
        
        self.port = port
        self.camera = None
        self.connected = False
        self.capabilities: Optional[CameraCapabilities] = None
        self.current_settings = CameraSettings()
        
    def detect_cameras(self) -> List[str]:
        """Detect available cameras.
        
        Returns:
            List of camera port strings
        """
        try:
            camera_list = gp.camera.Camera.autodetect()
            if camera_list is None:
                return []
            
            return [port for port, name in camera_list]
        except Exception as e:
            print(f"Warning: Could not detect cameras: {e}")
            return []
    
    def connect(self, auto_detect: bool = True) -> None:
        """Connect to camera.
        
        Args:
            auto_detect: Whether to auto-detect camera port
            
        Raises:
            CameraNotFoundError: If no camera found
            CameraConnectionError: If connection fails
        """
        try:
            if auto_detect and self.port is None:
                # Auto-detect camera
                camera_list = gp.camera.Camera.autodetect()
                if camera_list is None or len(camera_list) == 0:
                    raise CameraNotFoundError("No cameras detected")
                
                # Use first available camera
                self.port = camera_list[0][0]
                print(f"Auto-detected camera: {camera_list[0][1]} on port {self.port}")
            
            # Create camera instance
            self.camera = gp.Camera()
            
            if self.port:
                self.camera.init()
                self.connected = True
                print(f"Connected to camera on port: {self.port}")
                
                # Query capabilities
                self._query_capabilities()
                
            else:
                raise CameraConnectionError("No port specified and auto-detection failed")
                
        except gp.GPhoto2Error as e:
            if e.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                raise CameraNotFoundError(f"Camera not found on port {self.port}")
            else:
                raise CameraConnectionError(f"Failed to connect to camera: {e}")
        except Exception as e:
            raise CameraConnectionError(f"Unexpected error connecting to camera: {e}")
    
    def _query_capabilities(self) -> None:
        """Query camera capabilities and available settings."""
        try:
            # Get exposure times
            exposure_times = []
            try:
                exposure_config = self.camera.get_config('shutterspeed')
                choice_count = exposure_config.get_count()
                for i in range(choice_count):
                    choice = exposure_config.get_choice(i)
                    if choice and 's' in choice:
                        # Extract numeric value
                        value = float(choice.replace('s', ''))
                        exposure_times.append(value)
            except Exception:
                exposure_times = [0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0]  # Default values
            
            # Get apertures
            apertures = []
            try:
                aperture_config = self.camera.get_config('f-number')
                choice_count = aperture_config.get_count()
                for i in range(choice_count):
                    choice = aperture_config.get_choice(i)
                    if choice and 'f/' in choice:
                        # Extract numeric value
                        value = float(choice.replace('f/', ''))
                        apertures.append(value)
            except Exception:
                apertures = [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0]  # Default values
            
            # Get ISO values
            iso_values = []
            try:
                iso_config = self.camera.get_config('iso')
                choice_count = iso_config.get_count()
                for i in range(choice_count):
                    choice = iso_config.get_choice(i)
                    if choice:
                        iso_values.append(choice)
            except Exception:
                iso_values = ["auto", "100", "200", "400", "800", "1600", "3200", "6400"]  # Default values
            
            self.capabilities = CameraCapabilities(
                exposure_times=sorted(exposure_times),
                apertures=sorted(apertures),
                iso_values=iso_values
            )
            
            print(f"Camera capabilities detected:")
            print(f"  Exposure times: {len(exposure_times)} values")
            print(f"  Apertures: {len(apertures)} values")
            print(f"  ISO values: {len(iso_values)} values")
            
        except Exception as e:
            print(f"Warning: Could not query camera capabilities: {e}")
            # Use default capabilities
            self.capabilities = CameraCapabilities(
                exposure_times=[0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0],
                apertures=[1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0],
                iso_values=["auto", "100", "200", "400", "800", "1600", "3200", "6400"]
            )
    
    def disconnect(self) -> None:
        """Disconnect from camera and cleanup."""
        if self.camera and self.connected:
            try:
                self.camera.exit()
                self.connected = False
                print("Camera disconnected")
            except Exception as e:
                print(f"Warning: Error during camera disconnect: {e}")
            finally:
                self.camera = None
    
    def validate_settings(self, settings: CameraSettings) -> Tuple[CameraSettings, List[str]]:
        """Validate and adjust camera settings.
        
        Args:
            settings: Settings to validate
            
        Returns:
            Tuple of (validated_settings, warnings)
        """
        warnings = []
        
        if not self.capabilities:
            return settings, warnings
        
        validated = CameraSettings(
            exposure=settings.exposure,
            aperture=settings.aperture,
            iso=settings.iso,
            delay=settings.delay,
            quality=settings.quality,
            max_exposures=settings.max_exposures
        )
        
        # Validate exposure time
        if validated.exposure not in self.capabilities.exposure_times:
            closest = min(self.capabilities.exposure_times, 
                         key=lambda x: abs(x - validated.exposure))
            if closest != validated.exposure:
                warnings.append(f"Exposure adjusted from {validated.exposure}s to {closest}s")
                validated.exposure = closest
        
        # Validate aperture
        if validated.aperture not in self.capabilities.apertures:
            closest = min(self.capabilities.apertures,
                         key=lambda x: abs(x - validated.aperture))
            if closest != validated.aperture:
                warnings.append(f"Aperture adjusted from f/{validated.aperture} to f/{closest}")
                validated.aperture = closest
        
        # Validate ISO
        if validated.iso not in self.capabilities.iso_values:
            warnings.append(f"ISO value '{validated.iso}' may not be supported")
        
        return validated, warnings
    
    def configure_camera(self, settings: CameraSettings) -> List[str]:
        """Configure camera with validated settings.
        
        Args:
            settings: Camera settings to apply
            
        Returns:
            List of warnings
        """
        if not self.connected:
            raise CameraError("Camera not connected")
        
        warnings = []
        
        try:
            # Configure exposure time
            try:
                exposure_config = self.camera.get_config('shutterspeed')
                # Find closest exposure time
                closest_idx = 0
                closest_diff = float('inf')
                for i in range(exposure_config.get_count()):
                    choice = exposure_config.get_choice(i)
                    if choice and 's' in choice:
                        value = float(choice.replace('s', ''))
                        diff = abs(value - settings.exposure)
                        if diff < closest_diff:
                            closest_diff = diff
                            closest_idx = i
                
                exposure_config.set_value(closest_idx)
                self.camera.set_config(exposure_config)
            except Exception as e:
                warnings.append(f"Could not set exposure: {e}")
            
            # Configure aperture
            try:
                aperture_config = self.camera.get_config('f-number')
                # Find closest aperture
                closest_idx = 0
                closest_diff = float('inf')
                for i in range(aperture_config.get_count()):
                    choice = aperture_config.get_choice(i)
                    if choice and 'f/' in choice:
                        value = float(choice.replace('f/', ''))
                        diff = abs(value - settings.aperture)
                        if diff < closest_diff:
                            closest_diff = diff
                            closest_idx = i
                
                aperture_config.set_value(closest_idx)
                self.camera.set_config(aperture_config)
            except Exception as e:
                warnings.append(f"Could not set aperture: {e}")
            
            # Configure ISO
            try:
                if settings.iso != "auto":
                    iso_config = self.camera.get_config('iso')
                    iso_config.set_value(settings.iso)
                    self.camera.set_config(iso_config)
            except Exception as e:
                warnings.append(f"Could not set ISO: {e}")
            
            # Configure image quality to RAW
            try:
                quality_config = self.camera.get_config('imagequality')
                # Set to RAW format (highest quality)
                quality_config.set_value(7)  # This may vary by camera
                self.camera.set_config(quality_config)
            except Exception as e:
                warnings.append(f"Could not set image quality: {e}")
            
        except Exception as e:
            warnings.append(f"Error configuring camera: {e}")
        
        return warnings
    
    def capture_single(self, filename: Optional[str] = None) -> CaptureResult:
        """Capture a single image.
        
        Args:
            filename: Custom filename (without extension)
            
        Returns:
            CaptureResult with success status and file info
        """
        if not self.connected:
            return CaptureResult(success=False, error_message="Camera not connected")
        
        try:
            # Start live view (required for DSLR)
            try:
                self.camera.trigger_capture()
            except Exception as e:
                pass  # Live view might not be needed for all cameras
            
            # Capture image
            camera_file = self.camera.capture(gp.GP_CAPTURE_IMAGE)
            
            # Get file path and name
            filepath = camera_file.get_filepath()
            filename = camera_file.get_name()
            
            return CaptureResult(
                success=True,
                filename=filename,
                filepath=filepath
            )
            
        except Exception as e:
            return CaptureResult(
                success=False,
                error_message=f"Capture failed: {e}"
            )
    
    def start_live_view(self) -> bool:
        """Start live view (required for DSLR operation).
        
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        try:
            # This is implementation-specific and may vary by camera
            # For now, just return True to indicate live view capability
            return True
        except Exception as e:
            print(f"Warning: Could not start live view: {e}")
            return False
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Get information about the connected camera.
        
        Returns:
            Dictionary with camera information
        """
        info = {
            "connected": self.connected,
            "port": self.port,
            "has_capabilities": self.capabilities is not None
        }
        
        if self.capabilities:
            info.update({
                "exposure_times": len(self.capabilities.exposure_times),
                "apertures": len(self.capabilities.apertures),
                "iso_values": len(self.capabilities.iso_values)
            })
        
        return info
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
