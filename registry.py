"""
Plugin registry system for processors and writers.

Provides decorator-based registration for extensible processing pipelines.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Type, Any, Optional


class BaseRegistry:
    """Base class for plugin registries."""
    
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, plugin_class: Type = None, *, name: str = None):
        """
        Decorator to register a plugin class.
        
        Usage:
            @SomeRegistry.register
            class MyPlugin(BasePlugin):
                ...
            
            # Or with custom name:
            @SomeRegistry.register(name="custom_name")
            class MyPlugin(BasePlugin):
                ...
        """
        def decorator(klass: Type) -> Type:
            plugin_name = name or getattr(klass, 'name', None) or klass.__name__
            cls._registry[plugin_name] = klass
            return klass
        
        if plugin_class is not None:
            # Called without arguments: @SomeRegistry.register
            return decorator(plugin_class)
        else:
            # Called with arguments: @SomeRegistry.register(name="...")
            return decorator
    
    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        """Get a registered plugin by name."""
        return cls._registry.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Type]:
        """Get all registered plugins."""
        return cls._registry.copy()
    
    @classmethod
    def list_names(cls) -> List[str]:
        """List all registered plugin names."""
        return list(cls._registry.keys())
    
    @classmethod
    def clear(cls):
        """Clear all registered plugins (mainly for testing)."""
        cls._registry = {}


class ProcessorRegistry(BaseRegistry):
    """Registry for document processors."""
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def get_processor(cls, name: str) -> Optional[Any]:
        """Get and instantiate a processor by name."""
        processor_class = cls.get(name)
        if processor_class:
            return processor_class()
        return None
    
    @classmethod
    def get_processors(cls, names: List[str]) -> List[Any]:
        """Get and instantiate multiple processors by name."""
        processors = []
        for name in names:
            processor = cls.get_processor(name)
            if processor:
                processors.append(processor)
        return processors
    
    @classmethod
    def get_all_info(cls) -> Dict[str, Dict[str, str]]:
        """Get info about all registered processors."""
        info = {}
        for name, klass in cls._registry.items():
            info[name] = {
                'name': name,
                'description': getattr(klass, 'description', ''),
                'class': klass.__name__
            }
        return info


class WriterRegistry(BaseRegistry):
    """Registry for output writers."""
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def get_writer(cls, name: str) -> Optional[Any]:
        """Get and instantiate a writer by name."""
        writer_class = cls.get(name)
        if writer_class:
            return writer_class()
        return None
    
    @classmethod
    def get_all_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get info about all registered writers."""
        info = {}
        for name, klass in cls._registry.items():
            info[name] = {
                'name': name,
                'description': getattr(klass, 'description', ''),
                'extension': getattr(klass, 'extension', ''),
                'mime_type': getattr(klass, 'mime_type', 'application/octet-stream'),
                'class': klass.__name__
            }
        return info
    
    @classmethod
    def get_formats(cls) -> Dict[str, Dict[str, str]]:
        """Get available output formats for API response."""
        formats = {}
        for name, klass in cls._registry.items():
            formats[name] = {
                'name': name,
                'title': getattr(klass, 'title', name.upper()),
                'description': getattr(klass, 'description', ''),
                'extension': getattr(klass, 'extension', ''),
            }
        return formats
