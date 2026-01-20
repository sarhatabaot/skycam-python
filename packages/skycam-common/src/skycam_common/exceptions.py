"""Custom exceptions for skycam."""

from .camera import CameraError, CameraNotFoundError, CameraConnectionError

__all__ = [
    'CameraError',
    'CameraNotFoundError', 
    'CameraConnectionError'
]
