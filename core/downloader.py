"""
Downloader Module
=================

This module provides file downloading capabilities for Canvas Bot, including:
- Filename derivation from various sources (API metadata, URLs, titles)
- Path construction with Windows compatibility
- Windows shortcut (.lnk) creation for inaccessible files
- The DownloaderMixin class for ContentExtractor

Architecture
------------
The downloader sits at the final stage of the content pipeline::

    ContentNode → derive_file_name() → path_constructor() → _download_file()
                                                                   ↓
                                                    ┌──────────────┴──────────────┐
                                                    ↓                             ↓
                                              Direct Download              Windows Shortcut
                                              (requests.get)              (for failed downloads)

Filename Derivation Priority
----------------------------
The `derive_file_name()` function uses this priority order:

1. Canvas Studio files → Use title + .mp4 extension
2. `display_name` attribute → Human-readable name from API
3. `file_name` attribute → Explicitly set filename
4. `filename` attribute → URL-decoded API filename
5. Title + mime_class → e.g., "Document.pdf"
6. Title + mime_type extension → From MIME type lookup
7. Derived from URL → Last path segment
8. Sanitized title → Fallback

Path Construction
-----------------
Paths are constructed to preserve course hierarchy::

    {root_directory}/
    └── {date}/
        └── {Module}/
            └── {Assignment}/
                └── {Documents}/
                    └── filename.pdf

Or flattened::

    {root_directory}/
    └── {date}/
        └── {Documents}/
            └── filename.pdf

Windows Compatibility
---------------------
- Paths longer than 260 characters are handled with `\\\\?\\` prefix
- Invalid filename characters are sanitized
- Shortcuts are created for files that cannot be downloaded

See Also
--------
- core.content_extractor.ContentExtractor : Uses DownloaderMixin
- tools.string_checking.url_cleaning : Filename sanitization utilities
- config.yaml_io : Download manifest management
"""

from __future__ import annotations

import logging
import os.path
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import unquote_plus

import requests
import win32com.client
from colorama import Fore, Style
from requests.exceptions import MissingSchema, InvalidURL

from config.yaml_io import read_config, read_download_manifest, write_to_download_manifest
from resource_nodes.base_content_node import BaseContentNode
from sorters.sorters import force_to_shortcut, file_name_extractor
from tools.string_checking.other_tools import (
    has_file_extension,
    create_long_path_file,
    get_extension_from_mime_type
)
from tools.string_checking.url_cleaning import sanitize_windows_filename, remove_trailing_path_segments

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor

# Module configuration
config = read_config()
user_agent = config['requests']['user-agent']
default_download_path = config['default_download_path']

log = logging.getLogger(__name__)


# =============================================================================
# Filename Derivation Functions
# =============================================================================

def derive_filename_from_url(contentnode: BaseContentNode) -> str:
    """
    Derive a filename from a content node's URL as a last resort.

    This is used when no other filename source is available (display_name,
    filename, file_name attributes). Extracts the last path segment from
    the URL after removing query parameters and trailing segments.

    Parameters
    ----------
    contentnode : BaseContentNode
        The content node to derive the filename from. Uses `download_url`
        if available, otherwise falls back to `url`.

    Returns
    -------
    str
        The derived filename. If extraction fails, returns a shortcut-forcing
        filename prefixed with "$$-" (first 20 chars of title).

    Notes
    -----
    The "$$-" prefix is a convention that signals to `_download_file()` that
    this file should be saved as a Windows shortcut rather than downloaded.

    Example
    -------
    >>> node.url = "https://example.com/files/document.pdf?token=abc"
    >>> derive_filename_from_url(node)
    'document.pdf'
    """
    url_to_search = contentnode.url if getattr(contentnode, "download_url", None) is None else contentnode.download_url

    remove_trailing = remove_trailing_path_segments(url_to_search)
    if remove_trailing:
        return remove_trailing.split('/')[-1]
    else:
        # Force to shortcut using $$- prefix when URL parsing fails
        return f"$$-{contentnode.title[:20]}"


def sort_by_date() -> str:
    """
    Generate a date string for organizing downloads into daily folders.

    Returns
    -------
    str
        Current date formatted as "DD-MM-YYYY" (e.g., "25-01-2026").

    Notes
    -----
    This date is used as a subfolder name to organize downloads by the
    date they were downloaded, preventing overwrites and enabling
    incremental downloads.
    """
    return datetime.now().strftime('%d-%m-%Y')


def derive_file_name(node: BaseContentNode) -> str:
    """
    Derive the best filename for a content node.

    Uses a priority-based approach to find the most appropriate filename
    from various node attributes. This is critical for ensuring downloaded
    files have meaningful, correct names.

    Parameters
    ----------
    node : BaseContentNode
        The content node to derive a filename for.

    Returns
    -------
    str
        The derived filename including extension.

    Priority Order
    --------------
    1. **Canvas Studio files**: Use title + ".mp4" extension
    2. **display_name**: Human-readable name from Canvas API (preferred)
    3. **file_name**: Explicitly set filename attribute
    4. **filename**: URL-decoded filename from API
    5. **Title + mime_class**: Construct from title and MIME class
    6. **Title + mime_type**: Construct from title and MIME type extension
    7. **URL-derived**: Extract from download URL
    8. **Sanitized title**: Final fallback

    Notes
    -----
    - Canvas API often provides both `display_name` (human-readable) and
      `filename` (URL-encoded). We prefer `display_name` for cleaner names.
    - URL-encoded filenames (with + or %20) are decoded automatically.
    - The returned filename is NOT sanitized - call `sanitize_windows_filename()`
      before using in file paths.

    Example
    -------
    >>> # Node with display_name
    >>> node.display_name = "Homework 1.docx"
    >>> node.filename = "Homework+1.docx"
    >>> derive_file_name(node)
    'Homework 1.docx'

    >>> # Node without display_name
    >>> node.display_name = None
    >>> node.filename = "Lecture+Notes.pdf"
    >>> derive_file_name(node)
    'Lecture Notes.pdf'
    """
    # Canvas Studio files: always use .mp4 extension
    if node.is_canvas_studio_file:
        if node.download_url_is_manifest:
            return f"{node.title}.mp4"
        if has_file_extension(node.title, "video_files"):
            return node.title
        else:
            return f"{node.title}.mp4"

    # Priority 1: display_name (human-readable, preferred)
    if getattr(node, "display_name", None):
        return node.display_name

    # Priority 2: file_name attribute
    if node.file_name:
        return node.file_name

    # Priority 3: filename attribute (URL-decode it)
    if getattr(node, "filename", None):
        return unquote_plus(getattr(node, "filename"))

    # Priority 4-6: Construct from title + MIME info
    if not has_file_extension(node.title):
        if getattr(node, "mime_class", None):
            return f"{node.title}.{node.mime_class}"

        if getattr(node, "mime_type", None):
            extension = get_extension_from_mime_type(node.mime_type)
            return f"{node.title}{extension}"

        # Priority 7: Derive from URL
        return derive_filename_from_url(node)

    # Priority 8: Extract filename from title
    try:
        filename = sanitize_windows_filename(file_name_extractor.match(node.title.split('/')[-1]).group(0))
    except AttributeError:
        filename = sanitize_windows_filename(node.title)

    return filename


# =============================================================================
# Path Construction Functions
# =============================================================================

def path_constructor(root_directory: str, node: BaseContentNode, flatten: bool) -> str:
    """
    Construct the full file path for saving a downloaded file.

    Builds a path that either preserves the Canvas course hierarchy
    (modules, assignments, etc.) or flattens everything into type-based
    folders organized by date.

    Parameters
    ----------
    root_directory : str
        Base directory for downloads (e.g., "C:/Downloads/CourseName - 12345").

    node : BaseContentNode
        The content node being downloaded.

    flatten : bool
        If True, ignore course hierarchy and organize by content type only.
        If False, preserve the full folder structure from Canvas.

    Returns
    -------
    str
        Full path where the file should be saved, including filename.

    Path Structures
    ---------------
    **Hierarchical (flatten=False)**::

        {root}/
        └── 25-01-2026/
            └── Module 1/
                └── Week 1 Assignment/
                    └── Documents/
                        └── syllabus.pdf

    **Flattened (flatten=True)**::

        {root}/
        └── 25-01-2026/
            └── Documents/
                └── syllabus.pdf

    Notes
    -----
    - Paths exceeding 260 characters (Windows limit) are automatically
      shortened by truncating the filename to 20 characters.
    - Folder names are sanitized to remove invalid Windows characters.
    - Content type pluralization is automatic (Document → Documents).

    See Also
    --------
    derive_file_name : Generates the filename portion
    sanitize_windows_filename : Cleans invalid characters
    """
    from core.content_scaffolds import build_path

    filename = sanitize_windows_filename(derive_file_name(node))
    node_path = build_path(node, ignore_root=True)
    paths = []

    if flatten:
        # Flattened structure: just date and content type
        return os.path.join(root_directory, sort_by_date(), f"{node.__class__.__name__}s", filename)

    # Hierarchical structure: build path from course tree
    for node_ in node_path:
        if hasattr(node_, 'is_resource'):
            folder_name = sanitize_windows_filename(node_.title[:50], folder=True).rstrip() if node_.title else str(node_.__class__.__name__)
            paths.append(folder_name)

    constructed_path = os.path.join(root_directory, sort_by_date(), *paths[::-1], f"{node.__class__.__name__}s", filename)

    # Handle Windows 260 character path limit
    if len(constructed_path) > 260:
        filename_, extension = os.path.splitext(filename)
        if len(extension) > 5:
            extension = extension[:5]
        shortened_filename = f"{filename_[:20]}{extension}"
        constructed_path = constructed_path.replace(filename, shortened_filename)

    return constructed_path


# =============================================================================
# Windows Shortcut Creation
# =============================================================================

def create_windows_shortcut_from_url(url: str, shortcut_path: str) -> str:
    """
    Create a Windows shortcut (.lnk) file pointing to a URL.

    Used when a file cannot be downloaded directly (authentication required,
    unavailable, etc.). The shortcut allows users to manually access the
    resource by double-clicking.

    Parameters
    ----------
    url : str
        The URL the shortcut should point to.

    shortcut_path : str
        The intended file path. The extension will be replaced with ".lnk".

    Returns
    -------
    str
        The actual path where the shortcut was saved.

    Raises
    ------
    Exception
        If shortcut creation fails (logged before re-raising).

    Notes
    -----
    - Non-ASCII characters in the path are stripped to avoid encoding issues.
    - The original file extension is replaced with ".lnk".
    - Uses Windows Script Host (WScript.Shell) COM object.

    Example
    -------
    >>> create_windows_shortcut_from_url(
    ...     "https://example.com/protected.pdf",
    ...     "C:/Downloads/protected.pdf"
    ... )
    'C:/Downloads/protected.lnk'
    """
    # Strip non-ASCII characters and change extension to .lnk
    encode_path_to_ascii = shortcut_path.encode('ascii', errors='ignore').decode('ascii')
    shortcut_path = encode_path_to_ascii.split(".")[0] + ".lnk"

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = url
        shortcut.save()
        return shortcut_path
    except Exception as exc:
        log.exception(f"Failed to create shortcut for {url} at {shortcut_path}: {exc}")
        raise



# =============================================================================
# DownloaderMixin Class
# =============================================================================

class DownloaderMixin:
    """
    Mixin class providing file download capabilities for ContentExtractor.

    This mixin adds the ability to download content files from Canvas to the
    local filesystem. It handles various edge cases including authentication
    failures, network errors, and Windows path limitations.

    The mixin is designed to be used with ContentExtractor, providing:
    - Batch downloading of multiple content types
    - Progress tracking via download manifest
    - Automatic shortcut creation for inaccessible files
    - Hidden content handling

    Methods
    -------
    download(content_extractor, root_directory, **params)
        Download all selected content types to the specified directory.

    _download_file(url, filename, force_to_shortcut)
        Download a single file from URL to local path.

    Usage
    -----
    This mixin is inherited by ContentExtractor::

        class ContentExtractor(DownloaderMixin):
            def download_files(self, directory, **params):
                self.download(self, root_directory, **params)

    Features
    --------
    - **Manifest Tracking**: Downloaded URLs are tracked to avoid re-downloading
    - **Graceful Degradation**: Failed downloads become Windows shortcuts
    - **Hidden Content**: Can optionally include unpublished/hidden content
    - **Content Type Filtering**: Select which types to download

    See Also
    --------
    core.content_extractor.ContentExtractor : Main class using this mixin
    """

    def download(self, content_extractor: ContentExtractor, root_directory: str, **params) -> None:
        """
        Download content files from Canvas to a local directory.

        Orchestrates the download of multiple content nodes, tracking progress
        in a manifest file and creating shortcuts for files that cannot be
        downloaded directly.

        Parameters
        ----------
        content_extractor : ContentExtractor
            The content extractor instance containing the content nodes.

        root_directory : str
            Base directory for downloads. Files are organized within this
            directory by date and course structure.

        **params : dict
            Download options:

            include_video_files : bool, default False
                Include VideoFile, CanvasStudioEmbed, CanvasMediaEmbed nodes.

            include_audio_files : bool, default False
                Include AudioFile nodes.

            include_image_files : bool, default False
                Include ImageFile nodes.

            flatten : bool, default False
                If True, organize by content type only (ignore course hierarchy).

            download_hidden_files : bool, default False
                If True, include content hidden from students.

        Notes
        -----
        - Documents are always included by default
        - Progress is saved to download_manifest.yaml after completion
        - Previously downloaded URLs (in manifest) are skipped
        - Hidden content is logged when included

        Example
        -------
        >>> mixin.download(
        ...     extractor,
        ...     "/downloads/Biology - 12345",
        ...     include_video_files=True,
        ...     flatten=True
        ... )
        """
        from core.content_scaffolds import is_hidden

        download_manifest = read_download_manifest(root_directory)['downloaded_files']
        log.info(f"Downloading files to {root_directory} with params: {params}")

        # Extract params
        include_video_files = params.get('include_video_files', False)
        include_audio_files = params.get('include_audio_files', False)
        include_image_files = params.get('include_image_files', False)
        flatten = params.get('flatten', False)
        download_hidden_files = params.get('download_hidden_files', False)

        if not root_directory:
            root_directory = os.path.dirname(os.path.abspath(__file__))
            print(f"{Fore.YELLOW}!{Style.RESET_ALL} Using default download path: {root_directory}")

        # Build list of nodes to download (documents always included)
        download_nodes = list(content_extractor.get_document_objects())

        if include_video_files:
            download_nodes.extend(content_extractor.get_video_file_objects())

        if include_audio_files:
            download_nodes.extend(content_extractor.get_audio_file_objects())

        if include_image_files:
            download_nodes.extend(content_extractor.get_image_file_objects())

        # Print download summary header
        total_count = len(download_nodes)
        print()
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Downloading {total_count} files{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")

        # Track statistics
        stats = {'downloaded': 0, 'skipped': 0, 'hidden': 0, 'shortcuts': 0, 'errors': 0}

        for idx, node in enumerate(download_nodes, 1):
            # Progress indicator
            progress = f"[{idx}/{total_count}]"

            # Check if hidden
            if is_hidden(node):
                if download_hidden_files:
                    stats['hidden'] += 1
                    print(f"{Fore.YELLOW}{progress}{Style.RESET_ALL} {Fore.MAGENTA}[hidden]{Style.RESET_ALL} {_truncate_title(node.title)}")
                else:
                    continue

            # Check if already downloaded
            if node.url in download_manifest:
                stats['skipped'] += 1
                print(f"{Fore.LIGHTBLACK_EX}{progress} [skip] {_truncate_title(node.title)} (already downloaded){Style.RESET_ALL}")
                continue

            # Build path and download
            full_file_path = path_constructor(root_directory, node, flatten)
            result = self._download_file(node.url, full_file_path, bool(force_to_shortcut.match(node.url)))

            # Track result
            if result:
                if result.endswith('.lnk'):
                    stats['shortcuts'] += 1
                else:
                    stats['downloaded'] += 1
                download_manifest.append(node.url)

        # Save manifest
        write_to_download_manifest(root_directory, "downloaded_files", download_manifest)

        # Print summary
        print()
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Download Complete{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}\u2713{Style.RESET_ALL} Downloaded:  {stats['downloaded']}")
        print(f"  {Fore.BLUE}\u2192{Style.RESET_ALL} Skipped:     {stats['skipped']}")
        if stats['hidden'] > 0:
            print(f"  {Fore.MAGENTA}\u25CF{Style.RESET_ALL} Hidden:      {stats['hidden']}")
        if stats['shortcuts'] > 0:
            print(f"  {Fore.YELLOW}\u26A0{Style.RESET_ALL} Shortcuts:   {stats['shortcuts']}")
        print()

    def _download_file(self, url: str, filename: str, force_shortcut: bool = False) -> str:
        """
        Download a single file from a URL to a local path.

        Handles the actual HTTP download with error handling, creating a
        Windows shortcut if the download fails or is forced.

        Parameters
        ----------
        url : str
            The URL to download from.

        filename : str
            The local path where the file should be saved.

        force_shortcut : bool, default False
            If True, create a shortcut instead of downloading.
            Used for URLs that are known to require authentication.

        Returns
        -------
        str or None
            The path where the file was saved, or None if download failed
            completely. Note: shortcut paths end with ".lnk".

        Error Handling
        --------------
        - HTTP 4xx errors: Creates shortcut, logs warning
        - Connection errors: Creates shortcut, logs error
        - Permission errors: Creates shortcut, logs error
        - Invalid URL: Logs error, returns None

        Notes
        -----
        - Creates parent directories if they don't exist
        - Uses Windows long path prefix (\\\\?\\) on Windows
        - Downloads in 8KB chunks for memory efficiency
        """
        # Handle Windows long path names
        if os.name == 'nt':
            filename = create_long_path_file(filename)

        # Create parent directories
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        # Force to shortcut if pattern matches
        if force_shortcut:
            print(f"  {Fore.YELLOW}\u26A0{Style.RESET_ALL} Creating shortcut: {_truncate_title(os.path.basename(filename))}")
            return create_windows_shortcut_from_url(url, filename)

        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)

            # Handle HTTP errors
            if response.status_code in [401, 402, 403, 404, 405, 406]:
                log.warning(f"HTTP {response.status_code} {response.reason}: {url}")
                print(f"  {Fore.RED}\u2717{Style.RESET_ALL} HTTP {response.status_code}: {_truncate_title(os.path.basename(filename))} {Fore.LIGHTBLACK_EX}(creating shortcut){Style.RESET_ALL}")
                return create_windows_shortcut_from_url(url, filename)

            # Download successfully
            try:
                display_name = _truncate_title(os.path.basename(filename), 45)
                print(f"  {Fore.GREEN}\u2193{Style.RESET_ALL} {display_name}")

                with open(filename, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            file.flush()
                            os.fsync(file.fileno())

                return filename

            except PermissionError as exc:
                log.exception(f"Permission Error: {exc}, {filename}")
                print(f"  {Fore.RED}\u2717{Style.RESET_ALL} Permission denied: {_truncate_title(os.path.basename(filename))} {Fore.LIGHTBLACK_EX}(creating shortcut){Style.RESET_ALL}")
                return create_windows_shortcut_from_url(url, filename)

        except requests.exceptions.ConnectionError as exc:
            log.exception(f"Connection Error: {exc}, {url}")
            print(f"  {Fore.RED}\u2717{Style.RESET_ALL} Connection error: {_truncate_title(os.path.basename(filename))} {Fore.LIGHTBLACK_EX}(creating shortcut){Style.RESET_ALL}")
            return create_windows_shortcut_from_url(url, filename)

        except MissingSchema as exc:
            log.exception(f"Missing Schema Error: {exc}, {url}")
            print(f"  {Fore.RED}\u2717{Style.RESET_ALL} Invalid URL (missing schema): {_truncate_title(str(url), 40)}")
            return None

        except InvalidURL as exc:
            log.exception(f"Invalid URL Error: {exc}, {url}")
            print(f"  {Fore.RED}\u2717{Style.RESET_ALL} Invalid URL: {_truncate_title(str(url), 40)}")
            return None


def _truncate_title(title: str, max_length: int = 50) -> str:
    """Truncate a title for display, adding ellipsis if needed."""
    if not title:
        return "(untitled)"
    title = str(title)
    if len(title) > max_length:
        return title[:max_length - 3] + "..."
    return title






