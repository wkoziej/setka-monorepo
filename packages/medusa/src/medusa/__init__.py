# ABOUTME: Main module entry point exposing core Medusa functionality
# ABOUTME: Provides MedusaCore class and common exceptions for media upload automation

# from .core import MedusaCore  # TODO: Uncomment when core.py is implemented
from .exceptions import MedusaError, UploadError, PublishError

__version__ = "0.1.0"
__all__ = [
    "MedusaError",
    "UploadError",
    "PublishError",
]  # "MedusaCore" will be added later
