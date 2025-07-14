#!/usr/bin/env python3
"""
Skrypt do ekstrakcji wspólnego kodu z obsession do setka-common.
Automatyzuje przenoszenie i refaktoryzację kodu.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

def extract_code_blocks(file_path: Path) -> Dict[str, List[str]]:
    """Wydziela bloki kodu do przeniesienia."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Definicje bloków do wydzielenia
    blocks = {
        'MediaStructure': [],
        'StructureManager_base': [],
        'find_files': [],
        'to_keep': []  # Kod który zostaje w obsession
    }
    
    # Parsowanie pliku
    current_block = 'to_keep'
    class_depth = 0
    
    for i, line in enumerate(lines):
        # Detekcja klas i metod
        if line.startswith('class RecordingStructure'):
            current_block = 'MediaStructure'
            class_depth = 1
        elif line.startswith('class FileStructureManager'):
            current_block = 'StructureManager_base'
            class_depth = 1
        elif 'def find_audio_files' in line or 'def find_video_files' in line:
            current_block = 'find_files'
        elif 'def ensure_blender_dir' in line or 'def ensure_analysis_dir' in line:
            current_block = 'to_keep'
        
        # Śledzenie końca klas
        if current_block in ['MediaStructure', 'StructureManager_base']:
            if line.startswith('class ') and class_depth > 0:
                current_block = 'to_keep'
        
        blocks[current_block].append(line)
    
    return blocks

def create_common_structure(monorepo_path: Path):
    """Tworzy pliki w setka-common na podstawie wydzielonego kodu."""
    
    common_path = monorepo_path / 'packages' / 'common' / 'src' / 'setka_common'
    
    # base.py - MediaStructure i StructureManager
    base_content = '''"""
ABOUTME: Core file structure management for media projects
ABOUTME: Provides base classes for organizing media files and directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MediaStructure:
    """Universal structure for media projects."""
    
    project_dir: Path
    media_file: Path
    metadata_file: Path
    processed_dir: Path
    
    def exists(self) -> bool:
        """Check if structure exists in filesystem."""
        return (
            self.project_dir.exists()
            and self.media_file.exists()
            and self.processed_dir.exists()
        )
    
    def is_valid(self) -> bool:
        """Validate structure including metadata."""
        try:
            if not self.project_dir.exists():
                return False
            
            if not self.media_file.exists():
                return False
            
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    json.load(f)
            
            return True
        except (json.JSONDecodeError, IOError, OSError):
            return False


class StructureManager:
    """Base manager for media file structures."""
    
    METADATA_FILENAME = "metadata.json"
    PROCESSED_DIRNAME = "processed"
    
    @staticmethod
    def get_structure(media_path: Path, structure_type: str = "generic") -> MediaStructure:
        """Get structure for media file."""
        media_path = Path(media_path)
        project_dir = media_path.parent
        
        metadata_file = project_dir / StructureManager.METADATA_FILENAME
        processed_dir = project_dir / StructureManager.PROCESSED_DIRNAME
        
        return MediaStructure(
            project_dir=project_dir,
            media_file=media_path,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )
    
    @staticmethod
    def create_structure(media_path: Path) -> MediaStructure:
        """Create structure in filesystem."""
        structure = StructureManager.get_structure(media_path)
        
        structure.processed_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created structure: {structure.project_dir}")
        
        return structure
    
    @staticmethod
    def ensure_directory(base_path: Path, dirname: str) -> Path:
        """Ensure directory exists."""
        dir_path = base_path / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
'''
    
    # types.py - MediaType i stałe
    types_content = '''"""
ABOUTME: Media type definitions and file extensions
ABOUTME: Provides enums and constants for different media types
"""

from enum import Enum
from typing import List


class MediaType(Enum):
    """Types of media files."""
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"


class FileExtensions:
    """Common file extensions by type."""
    AUDIO = [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"]
    VIDEO = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"]
    IMAGE = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"]
    DOCUMENT = [".pdf", ".doc", ".docx", ".txt", ".md", ".odt"]
    
    @classmethod
    def get_for_type(cls, media_type: MediaType) -> List[str]:
        """Get extensions for media type."""
        return {
            MediaType.AUDIO: cls.AUDIO,
            MediaType.VIDEO: cls.VIDEO,
            MediaType.IMAGE: cls.IMAGE,
            MediaType.DOCUMENT: cls.DOCUMENT,
        }[media_type]
'''
    
    # utils/files.py - funkcje pomocnicze
    files_content = '''"""
ABOUTME: File discovery and manipulation utilities
ABOUTME: Provides functions for finding and organizing media files
"""

from pathlib import Path
from typing import List, Optional
import logging

from ..file_structure.types import MediaType, FileExtensions

logger = logging.getLogger(__name__)


def find_files_by_type(directory: Path, media_type: MediaType) -> List[Path]:
    """Find all files of given media type in directory."""
    extensions = FileExtensions.get_for_type(media_type)
    files = []
    
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return files
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            files.append(file_path)
    
    # Sort for consistency
    files.sort(key=lambda x: x.name)
    logger.debug(f"Found {len(files)} {media_type.value} files in {directory}")
    return files


def find_media_files(directory: Path) -> dict[MediaType, List[Path]]:
    """Find all media files grouped by type."""
    result = {}
    
    for media_type in MediaType:
        files = find_files_by_type(directory, media_type)
        if files:
            result[media_type] = files
    
    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility."""
    # Remove invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]
    
    return filename
'''
    
    # specialized/recording.py - dla obsession
    recording_content = '''"""
ABOUTME: Recording-specific file structure for obsession
ABOUTME: Extends base structure with recording-specific directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..base import MediaStructure, StructureManager


@dataclass
class RecordingStructure(MediaStructure):
    """Structure for OBS recording projects."""
    extracted_dir: Path
    analysis_dir: Optional[Path] = None
    blender_dir: Optional[Path] = None


class RecordingStructureManager(StructureManager):
    """Manager for recording-specific structures."""
    
    EXTRACTED_DIRNAME = "extracted"
    
    @staticmethod
    def get_structure(video_path: Path) -> RecordingStructure:
        """Get recording structure."""
        base = StructureManager.get_structure(video_path)
        extracted_dir = base.project_dir / RecordingStructureManager.EXTRACTED_DIRNAME
        
        return RecordingStructure(
            project_dir=base.project_dir,
            media_file=base.media_file,
            metadata_file=base.metadata_file,
            processed_dir=base.processed_dir,
            extracted_dir=extracted_dir,
        )
    
    @staticmethod
    def create_structure(video_path: Path) -> RecordingStructure:
        """Create recording structure."""
        structure = RecordingStructureManager.get_structure(video_path)
        
        # Create all directories
        structure.processed_dir.mkdir(parents=True, exist_ok=True)
        structure.extracted_dir.mkdir(parents=True, exist_ok=True)
        
        return structure
'''
    
    # Zapisz pliki
    files_to_create = [
        (common_path / 'file_structure' / '__init__.py', 
         'from .base import MediaStructure, StructureManager\nfrom .types import MediaType, FileExtensions\n\n__all__ = ["MediaStructure", "StructureManager", "MediaType", "FileExtensions"]'),
        (common_path / 'file_structure' / 'base.py', base_content),
        (common_path / 'file_structure' / 'types.py', types_content),
        (common_path / 'file_structure' / 'specialized' / '__init__.py', 
         'from .recording import RecordingStructure, RecordingStructureManager\n\n__all__ = ["RecordingStructure", "RecordingStructureManager"]'),
        (common_path / 'file_structure' / 'specialized' / 'recording.py', recording_content),
        (common_path / 'utils' / '__init__.py', ''),
        (common_path / 'utils' / 'files.py', files_content),
    ]
    
    for file_path, content in files_to_create:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created: {file_path}")

def update_obsession_imports(obsession_path: Path):
    """Update imports in obsession to use setka-common."""
    
    # Pliki do zaktualizowania
    files_to_update = list(obsession_path.rglob("*.py"))
    
    # Mapowanie starych importów na nowe
    import_mappings = [
        (r'from \.file_structure import RecordingStructure',
         'from setka_common.file_structure.specialized import RecordingStructure'),
        (r'from \.file_structure import FileStructureManager',
         'from setka_common.file_structure.specialized import RecordingStructureManager as FileStructureManager'),
        (r'from core\.file_structure import',
         'from setka_common.file_structure.specialized import'),
        (r'from src\.core\.file_structure import',
         'from setka_common.file_structure.specialized import'),
    ]
    
    updated_count = 0
    for file_path in files_to_update:
        if 'file_structure.py' in str(file_path):
            continue  # Skip the file we're removing
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for old_import, new_import in import_mappings:
                content = re.sub(old_import, new_import, content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_count += 1
                print(f"Updated imports in: {file_path.relative_to(obsession_path)}")
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
    
    print(f"\nUpdated {updated_count} files")

def main():
    """Main extraction process."""
    print("=== Ekstrakcja kodu do setka-common ===\n")
    
    # Ścieżki
    monorepo_path = Path.home() / 'dev' / 'setka-monorepo'
    
    if not monorepo_path.exists():
        print(f"ERROR: Monorepo nie istnieje w {monorepo_path}")
        print("Najpierw uruchom: ./migrate-to-monorepo.sh")
        return
    
    # Krok 1: Utwórz strukturę setka-common
    print("1. Tworzę pliki w setka-common...")
    create_common_structure(monorepo_path)
    
    # Krok 2: Update importów w obsession
    print("\n2. Aktualizuję importy w obsession...")
    obsession_path = monorepo_path / 'packages' / 'obsession'
    update_obsession_imports(obsession_path)
    
    # Krok 3: Backup i usunięcie starego file_structure.py
    old_file = obsession_path / 'src' / 'core' / 'file_structure.py'
    if old_file.exists():
        backup_file = old_file.with_suffix('.py.backup')
        shutil.copy2(old_file, backup_file)
        print(f"\n3. Backup utworzony: {backup_file}")
        
        # Zakomentuj aby nie usuwać automatycznie
        # old_file.unlink()
        # print(f"   Usunięto: {old_file}")
    
    print("\n=== Ekstrakcja zakończona! ===")
    print("\nNastępne kroki:")
    print("1. cd ~/dev/setka-monorepo")
    print("2. uv sync")
    print("3. uv run pytest")
    print("4. Usuń packages/obsession/src/core/file_structure.py jeśli testy przechodzą")

if __name__ == "__main__":
    main()