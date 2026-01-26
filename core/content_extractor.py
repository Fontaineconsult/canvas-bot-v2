"""
Content Extractor Module
========================

This module provides the ContentExtractor class, which serves as the primary interface
for extracting, categorizing, and exporting content discovered within a Canvas LMS course.

The ContentExtractor operates on a Manifest of content nodes that have been collected
during course traversal, providing methods to:
- Filter content by type (documents, videos, audio, images, etc.)
- Export content metadata to JSON or Excel formats
- Download files to local storage
- Generate content statistics

Architecture
------------
The ContentExtractor sits at the output stage of the Canvas Bot pipeline:

    Canvas API → Course Tree → Content Nodes → Manifest → ContentExtractor → Output
                                                              ↓
                                            ┌─────────────────┼─────────────────┐
                                            ↓                 ↓                 ↓
                                         JSON Export     Excel Export     File Downloads

The class inherits from DownloaderMixin to gain file download capabilities while
maintaining separation of concerns between content extraction and file I/O.

Content Types
-------------
The extractor categorizes content into these types (from content_nodes.py):

    - Document: Downloadable document files (PDF, DOCX, PPTX, etc.)
    - DocumentSite: Cloud document platforms (Google Docs, OneDrive)
    - VideoFile: Downloadable video files (MP4, MOV, MKV)
    - VideoSite: Video hosting platforms (YouTube, Vimeo, Zoom)
    - AudioFile: Downloadable audio files (MP3, M4A, WAV)
    - AudioSite: Audio/podcast platforms
    - ImageFile: Image files (JPG, PNG, GIF)
    - FileStorageSite: Cloud storage (Box, Google Drive)
    - DigitalTextbook: E-textbook platforms (Cengage, McGraw-Hill)
    - CanvasStudioEmbed: Canvas Studio video embeds
    - CanvasMediaEmbed: Canvas native media embeds
    - Unsorted: Unclassified links

Usage Example
-------------
    from core.course_root import CanvasCourseRoot

    # Build course content tree
    course = CanvasCourseRoot(course_id="12345")

    # Get content extractor from course
    extractor = course.content_extractor

    # Export to JSON
    extractor.save_content_as_json("/output/json", "/downloads")

    # Export to Excel
    extractor.save_content_as_excel("/output/excel", download_folder="/downloads")

    # Download all documents
    extractor.download_files("/downloads", include_video_files=True)

See Also
--------
- core.manifest.Manifest: Storage for discovered content nodes
- core.content_scaffolds: Helper functions for building content dictionaries
- core.downloader.DownloaderMixin: File download capabilities
- resource_nodes.content_nodes: Content node class definitions
"""

import json
import os
import shutil

from config.yaml_io import create_download_manifest
from core.content_scaffolds import *
from core.manifest import Manifest
from resource_nodes.content_nodes import *
from core.downloader import DownloaderMixin
from tools.export_to_excel import save_as_excel


class ContentExtractor(DownloaderMixin):
    """
    Extracts, categorizes, and exports content from a Canvas LMS course.

    ContentExtractor is the primary class for working with discovered course content.
    It provides a high-level interface to filter content by type, export to various
    formats (JSON, Excel), and download files to local storage.

    The class operates on a Manifest object containing all ContentNode objects
    discovered during course traversal. Each getter method filters the manifest
    to return specific content types, while export methods transform the content
    into structured output formats suitable for accessibility auditing.

    Attributes
    ----------
    manifest : Manifest
        The manifest containing all discovered content nodes from the course.
        Populated during course tree traversal by CanvasCourseRoot.

    course_id : str
        The Canvas course ID (e.g., "12345").

    course_url : str
        The full URL to the course (e.g., "https://school.instructure.com/courses/12345").

    course_name : str
        The human-readable course name/title.

    exists : bool
        Whether the course exists and was successfully loaded.
        When False, export and download operations are skipped.

    Inheritance
    -----------
    Inherits from DownloaderMixin which provides:
        - download(): Orchestrates downloading of content nodes
        - _download_file(): Downloads individual files with error handling

    Methods Summary
    ---------------
    Content Getters:
        get_document_objects() -> List[Document]
        get_video_file_objects() -> List[VideoFile|CanvasStudioEmbed|CanvasMediaEmbed]
        get_video_site_objects() -> List[VideoSite]
        get_audio_file_objects() -> List[AudioFile]
        get_audio_site_objects() -> List[AudioSite]
        get_image_file_objects() -> List[ImageFile]
        get_document_site_objects() -> List[DocumentSite]
        get_digital_textbook_objects() -> List[DigitalTextbook]
        get_file_storage_site_objects() -> List[FileStorageSite]
        get_unsorted_objects() -> List[Unsorted]

    Dictionary Builders:
        build_documents_dict(file_download_directory, flatten) -> dict
        build_videos_dict(file_download_directory, flatten, check_caption_status) -> dict
        build_audio_dict(file_download_directory, flatten) -> dict
        build_images_dict(file_download_directory, flatten) -> dict
        build_unsorted_dict() -> dict

    Export Methods:
        get_all_content(file_download_directory, **params) -> dict
        get_all_content_as_json(file_download_directory, **params) -> str
        save_content_as_json(json_save_directory, file_download_directory, **params) -> str
        save_content_as_excel(excel_directory, **params) -> None

    Download Methods:
        download_files(directory, **params) -> None
        clear_folder_contents(directory) -> None

    Statistics:
        count_content() -> dict

    Example
    -------
    >>> extractor = ContentExtractor(manifest, "12345", "https://...", "Biology 101", True)

    >>> # Get all documents
    >>> docs = extractor.get_document_objects()
    >>> print(f"Found {len(docs)} documents")

    >>> # Export to JSON
    >>> json_path = extractor.save_content_as_json("/output", "/downloads")

    >>> # Download with video files included
    >>> extractor.download_files("/downloads", include_video_files=True, flatten=True)

    Notes
    -----
    - All export/download operations check `self.exists` before proceeding
    - File downloads track progress in a manifest to avoid re-downloading
    - Hidden content (unpublished, locked) is tracked but excluded from downloads by default
    - The `flatten` parameter controls whether files preserve course folder structure
    """

    def __init__(self, manifest: Manifest, course_id: str, course_url: str,
                 course_name: str, exists: bool):
        """
        Initialize a ContentExtractor for a Canvas course.

        Parameters
        ----------
        manifest : Manifest
            The manifest containing all discovered content nodes. This is typically
            populated by CanvasCourseRoot during course tree traversal.

        course_id : str
            The Canvas course ID (numeric string, e.g., "12345").

        course_url : str
            The full URL to the course homepage
            (e.g., "https://school.instructure.com/courses/12345").

        course_name : str
            The human-readable course name/title as displayed in Canvas.

        exists : bool
            Whether the course exists and was successfully loaded from the API.
            When False, all export and download operations will be skipped.
        """
        self.manifest = manifest
        self.course_id = course_id
        self.course_url = course_url
        self.course_name = course_name
        self.exists = exists

    # =========================================================================
    # Content Getter Methods
    # =========================================================================
    # These methods filter the manifest to return specific content types.
    # Each returns a list of content nodes matching the specified type(s).

    def get_document_objects(self) -> list:
        """
        Get all downloadable document content nodes.

        Returns a list of Document nodes representing downloadable files like
        PDFs, Word documents, PowerPoints, Excel spreadsheets, and other
        document formats.

        Returns
        -------
        list[Document]
            List of Document content nodes. May be empty if no documents found.

        Example
        -------
        >>> docs = extractor.get_document_objects()
        >>> for doc in docs:
        ...     print(f"{doc.title}: {doc.url}")
        """
        return [item for item in self.manifest.content_list() if isinstance(item, Document)]

    def get_video_file_objects(self) -> list:
        """
        Get all downloadable video content nodes.

        Returns a list of video-related nodes including:
        - VideoFile: Direct video files (MP4, MOV, MKV, etc.)
        - CanvasStudioEmbed: Canvas Studio embedded videos
        - CanvasMediaEmbed: Canvas native media embeds

        These are grouped together because they all represent downloadable
        video content, as opposed to VideoSite which represents external
        video platforms (YouTube, Vimeo).

        Returns
        -------
        list[VideoFile | CanvasStudioEmbed | CanvasMediaEmbed]
            List of video content nodes. May be empty if no videos found.

        See Also
        --------
        get_video_site_objects : For external video platform links (YouTube, etc.)
        """
        return [item for item in self.manifest.content_list() if isinstance(item, VideoFile)
                or isinstance(item, CanvasStudioEmbed) or isinstance(item, CanvasMediaEmbed)]

    def get_video_site_objects(self) -> list:
        """
        Get all external video site content nodes.

        Returns a list of VideoSite nodes representing links to external
        video platforms such as YouTube, Vimeo, Zoom recordings, TikTok, etc.

        These are distinct from VideoFile because they cannot be directly
        downloaded - they require visiting the external platform.

        Returns
        -------
        list[VideoSite]
            List of VideoSite content nodes. May be empty if none found.

        See Also
        --------
        get_video_file_objects : For downloadable video files
        """
        return [item for item in self.manifest.content_list() if isinstance(item, VideoSite)]

    def get_audio_file_objects(self) -> list:
        """
        Get all downloadable audio content nodes.

        Returns a list of AudioFile nodes representing downloadable audio
        files like MP3, M4A, WAV, OGG, etc.

        Returns
        -------
        list[AudioFile]
            List of AudioFile content nodes. May be empty if none found.

        See Also
        --------
        get_audio_site_objects : For external audio/podcast platform links
        """
        return [item for item in self.manifest.content_list() if isinstance(item, AudioFile)]

    def get_audio_site_objects(self) -> list:
        """
        Get all external audio site content nodes.

        Returns a list of AudioSite nodes representing links to external
        audio/podcast platforms.

        Returns
        -------
        list[AudioSite]
            List of AudioSite content nodes. May be empty if none found.

        See Also
        --------
        get_audio_file_objects : For downloadable audio files
        """
        return [item for item in self.manifest.content_list() if isinstance(item, AudioSite)]

    def get_image_file_objects(self) -> list:
        """
        Get all image content nodes.

        Returns a list of ImageFile nodes representing image files like
        JPG, PNG, GIF, SVG, WebP, etc.

        Returns
        -------
        list[ImageFile]
            List of ImageFile content nodes. May be empty if none found.
        """
        return [item for item in self.manifest.content_list() if isinstance(item, ImageFile)]

    def get_document_site_objects(self) -> list:
        """
        Get all cloud document site content nodes.

        Returns a list of DocumentSite nodes representing links to cloud
        document platforms like Google Docs, Google Sheets, Google Slides,
        OneDrive, SharePoint, etc.

        These are distinct from Document because they cannot be directly
        downloaded - they require visiting the external platform.

        Returns
        -------
        list[DocumentSite]
            List of DocumentSite content nodes. May be empty if none found.

        See Also
        --------
        get_document_objects : For downloadable document files
        """
        return [item for item in self.manifest.content_list() if isinstance(item, DocumentSite)]

    def get_digital_textbook_objects(self) -> list:
        """
        Get all digital textbook content nodes.

        Returns a list of DigitalTextbook nodes representing links to
        e-textbook platforms like Cengage, McGraw-Hill Connect, Pearson,
        VitalSource, etc.

        Returns
        -------
        list[DigitalTextbook]
            List of DigitalTextbook content nodes. May be empty if none found.
        """
        return [item for item in self.manifest.content_list() if isinstance(item, DigitalTextbook)]

    def get_file_storage_site_objects(self) -> list:
        """
        Get all cloud file storage content nodes.

        Returns a list of FileStorageSite nodes representing links to
        cloud storage platforms like Box, Dropbox, Google Drive folders, etc.

        Returns
        -------
        list[FileStorageSite]
            List of FileStorageSite content nodes. May be empty if none found.
        """
        return [item for item in self.manifest.content_list() if isinstance(item, FileStorageSite)]

    def get_unsorted_objects(self) -> list:
        """
        Get all unclassified content nodes.

        Returns a list of Unsorted nodes representing links that didn't
        match any known content type pattern. These may be:
        - Custom institutional tools
        - Uncommon file types
        - External websites
        - Links requiring manual review

        Returns
        -------
        list[Unsorted]
            List of Unsorted content nodes. May be empty if all content
            was successfully classified.
        """
        return [item for item in self.manifest.content_list() if isinstance(item, Unsorted)]

    # =========================================================================
    # Dictionary Builder Methods
    # =========================================================================
    # These methods transform content nodes into dictionaries suitable for
    # JSON/Excel export. They use helper functions from content_scaffolds.py.

    def build_documents_dict(self, file_download_directory: str, flatten: bool) -> dict:
        """
        Build a dictionary containing all document content.

        Transforms Document and DocumentSite content nodes into serializable
        dictionaries using helper functions from content_scaffolds.py.

        Parameters
        ----------
        file_download_directory : str or None
            Base directory where files will be downloaded. When provided,
            each document dict will include a 'save_path' field with the
            full path where the file would be saved. Pass None to omit paths.

        flatten : bool
            If True, save paths ignore course folder structure and place
            all files in date-based folders by type. If False, preserve
            the hierarchical folder structure from Canvas.

        Returns
        -------
        dict
            Dictionary with two keys:
            - "documents": List of document dicts (downloadable files)
            - "document_sites": List of document site dicts (cloud platforms)

            Each document dict contains: title, url, source_page_type,
            source_page_url, scan_date, is_hidden, file_type, order, path,
            and optionally save_path.
        """
        return {
            "documents": [document_dict(document, file_download_directory, flatten) for document in self.get_document_objects()],
            "document_sites": [document_site_dict(document_site) for document_site in self.get_document_site_objects()],
        }

    def build_videos_dict(self, file_download_directory: str, flatten: bool,
                          check_video_site_caption_status: bool) -> dict:
        """
        Build a dictionary containing all video content.

        Transforms VideoFile, CanvasStudioEmbed, CanvasMediaEmbed, and
        VideoSite content nodes into serializable dictionaries.

        Parameters
        ----------
        file_download_directory : str or None
            Base directory where video files will be downloaded. When provided,
            video file dicts include a 'save_path' field. Pass None to omit.

        flatten : bool
            If True, ignore course folder structure in save paths.
            If False, preserve hierarchical structure.

        check_video_site_caption_status : bool
            If True, check YouTube videos for caption availability using
            the YouTube API. This adds a 'caption_status' field to video
            site dicts. Requires YouTube API credentials to be configured.

        Returns
        -------
        dict
            Dictionary with two keys:
            - "video_sites": List of video site dicts (YouTube, Vimeo, etc.)
            - "video_files": List of video file dicts (downloadable videos)

            Video file dicts include: title, file_name, url, source_page_type,
            source_page_url, scan_date, is_hidden, file_type, order, is_captioned,
            download_url, path, class, and optionally canvas_media_id, save_path,
            canvas_studio_id, machine_captioned.
        """
        return {
            "video_sites": [video_site_dict(video_site, check_video_site_caption_status)
                            for video_site in self.get_video_site_objects()],
            "video_files": [video_file_dict(video_file, file_download_directory, flatten) for video_file in
                            self.get_video_file_objects()],
        }

    def build_audio_dict(self, file_download_directory: str, flatten: bool) -> dict:
        """
        Build a dictionary containing all audio content.

        Transforms AudioFile and AudioSite content nodes into serializable
        dictionaries.

        Parameters
        ----------
        file_download_directory : str or None
            Base directory where audio files will be downloaded. When provided,
            audio file dicts include a 'save_path' field. Pass None to omit.

        flatten : bool
            If True, ignore course folder structure in save paths.
            If False, preserve hierarchical structure.

        Returns
        -------
        dict
            Dictionary with two keys:
            - "audio_sites": List of audio site dicts (podcast platforms, etc.)
            - "audio_files": List of audio file dicts (downloadable audio)
        """
        return {
            "audio_sites": [audio_site_dict(audio_site) for audio_site in self.get_audio_site_objects()],
            "audio_files": [audio_file_dict(audio_file, file_download_directory, flatten) for audio_file in
                            self.get_audio_file_objects()],
        }

    def build_images_dict(self, file_download_directory: str, flatten: bool) -> dict:
        """
        Build a dictionary containing all image content.

        Transforms ImageFile content nodes into serializable dictionaries.

        Parameters
        ----------
        file_download_directory : str or None
            Base directory where image files will be downloaded. When provided,
            image file dicts include a 'save_path' field. Pass None to omit.

        flatten : bool
            If True, ignore course folder structure in save paths.
            If False, preserve hierarchical structure.

        Returns
        -------
        dict
            Dictionary with one key:
            - "image_files": List of image file dicts
        """
        return {
            "image_files": [image_file_dict(image_file, file_download_directory, flatten) for image_file in
                            self.get_image_file_objects()],
        }

    def build_unsorted_dict(self) -> dict:
        """
        Build a dictionary containing all unclassified content.

        Transforms Unsorted content nodes into serializable dictionaries.
        Unsorted content represents links that didn't match any known
        content type pattern.

        Returns
        -------
        dict
            Dictionary with one key:
            - "unsorted": List of unsorted content dicts
        """
        return {
            "unsorted": [unsorted_dict(unsorted) for unsorted in self.get_unsorted_objects()],
        }

    # =========================================================================
    # Content Aggregation Methods
    # =========================================================================

    def get_all_content(self, file_download_directory: str = None, **params) -> dict:
        """
        Build a complete dictionary of all course content.

        Aggregates all content types into a single structured dictionary
        containing course metadata and categorized content. This is the
        primary method for getting a complete content inventory.

        Parameters
        ----------
        file_download_directory : str, optional
            Base directory where files will be downloaded. When provided,
            file content dicts include 'save_path' fields. Pass None to omit.

        **params : dict
            Additional parameters passed to build methods:

            flatten : bool, default False
                If True, ignore course folder structure in save paths.

            check_video_site_caption_status : bool, default False
                If True, check YouTube videos for caption availability.

        Returns
        -------
        dict
            Complete content inventory with structure::

                {
                    "course_id": "12345",
                    "course_url": "https://...",
                    "course_name": "Biology 101",
                    "content": {
                        "documents": {...},  # from build_documents_dict()
                        "videos": {...},     # from build_videos_dict()
                        "audio": {...},      # from build_audio_dict()
                        "images": {...},     # from build_images_dict()
                        "unsorted": {...}    # from build_unsorted_dict()
                    }
                }

        Example
        -------
        >>> content = extractor.get_all_content("/downloads", flatten=True)
        >>> print(f"Found {len(content['content']['documents']['documents'])} documents")
        """
        flatten = params.get("flatten", False)
        check_video_site_caption_status = params.get("check_video_site_caption_status", False)
        content_dict = {
            "course_id": self.course_id,
            "course_url": self.course_url,
            "course_name": self.course_name,
            "content": {
                "documents": self.build_documents_dict(file_download_directory, flatten),
                "videos": self.build_videos_dict(file_download_directory, flatten, check_video_site_caption_status),
                "audio": self.build_audio_dict(file_download_directory, flatten),
                "images": self.build_images_dict(file_download_directory, flatten),
                "unsorted": self.build_unsorted_dict()
            }
        }
        return content_dict

    def get_all_content_as_json(self, file_download_directory: str = None, **params) -> str:
        """
        Get all course content as a JSON string.

        Serializes the complete content inventory to a formatted JSON string.
        Useful for API responses or programmatic processing.

        Parameters
        ----------
        file_download_directory : str, optional
            Base directory for file save paths. Pass None to omit paths.

        **params : dict
            Parameters passed to get_all_content() (flatten, check_video_site_caption_status).

        Returns
        -------
        str
            Pretty-printed JSON string (4-space indent, sorted keys).
            Datetime objects are converted to strings.

        See Also
        --------
        get_all_content : Returns dict instead of JSON string
        save_content_as_json : Saves JSON to file
        """
        return json.dumps(self.get_all_content(file_download_directory, **params), indent=4, sort_keys=True, default=str)

    # =========================================================================
    # Export Methods
    # =========================================================================

    def save_content_as_json(self, json_save_directory: str, file_download_directory: str = None,
                             **params) -> str:
        """
        Save all course content to a JSON file.

        Exports the complete content inventory to a JSON file named after
        the course ID. Creates the output directory if it doesn't exist.

        Parameters
        ----------
        json_save_directory : str
            Directory where the JSON file will be saved. If None, uses
            the default output/json directory in the project.

        file_download_directory : str, optional
            Base directory for file save paths in the JSON. Pass None to omit.

        **params : dict
            Parameters passed to get_all_content_as_json():
            - flatten: bool - Flatten save paths
            - check_video_site_caption_status: bool - Check YouTube captions

        Returns
        -------
        str or None
            Full path to the saved JSON file, or None if course doesn't exist.

        Notes
        -----
        - Overwrites existing file if present
        - Only executes if self.exists is True
        - Creates parent directories as needed

        Example
        -------
        >>> path = extractor.save_content_as_json("/output/json", "/downloads")
        >>> print(f"Saved to: {path}")
        Saved to: /output/json/12345.json
        """
        if self.exists:
            dirname = os.path.abspath(__file__ + "/../../")
            full_path = os.path.join(dirname, rf'output\\json\\{self.course_id}.json')

            if json_save_directory:
                full_path = os.path.join(json_save_directory, rf"{self.course_id}.json")

            if os.path.exists(full_path):
                os.remove(full_path)

            if not os.path.exists(os.path.dirname(full_path)):
                os.makedirs(os.path.dirname(full_path))

            with open(full_path, 'w') as f:
                f.write(self.get_all_content_as_json(file_download_directory, **params))

            return full_path
        return None

    def save_content_as_excel(self, excel_directory: str, **params) -> None:
        """
        Save all course content to an Excel workbook.

        Exports the complete content inventory to a macro-enabled Excel
        workbook (.xlsm) with multiple sheets organized by content type.
        The workbook includes formatting, hyperlinks, and dropdown
        validation for accessibility tracking workflows.

        Parameters
        ----------
        excel_directory : str
            Directory where the Excel file and course folder will be created.
            A subfolder named "{course_name} - {course_id}" is created.

        **params : dict
            Additional parameters:

            download_folder : str, optional
                If provided, file paths in Excel will point to this location.

            download_hidden_files : bool, default False
                If True, include hidden/unpublished content in the export.

            flatten : bool, default False
                If True, use flattened file paths.

            check_video_site_caption_status : bool, default False
                If True, check YouTube caption availability.

        Notes
        -----
        - Creates course folder: {excel_directory}/{course_name} - {course_id}/
        - Excel file includes sheets: Documents, Videos, Audio, Images, Unsorted
        - Includes conditional formatting for hidden content
        - Only executes if self.exists is True

        See Also
        --------
        tools.export_to_excel.save_as_excel : The underlying Excel export function
        """
        file_download_directory = params.get("download_folder", None)
        download_hidden_files = params.get("download_hidden_files", False)

        if self.exists:
            root_download_directory = os.path.join(excel_directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")

            if file_download_directory:
                root_file_download_directory = os.path.join(file_download_directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                                                     rf"- {self.course_id}")
            else:
                root_file_download_directory = None

            if not os.path.exists(root_download_directory):
                os.makedirs(root_download_directory)
            json_data = json.loads(self.get_all_content_as_json(root_file_download_directory, **params))

            save_as_excel(json_data, root_download_directory, download_hidden_files)

    # =========================================================================
    # Download Methods
    # =========================================================================

    def download_files(self, directory: str, **params) -> None:
        """
        Download all course files to a local directory.

        Downloads document files (and optionally video, audio, image files)
        to an organized folder structure. Tracks downloaded files in a
        manifest to avoid re-downloading on subsequent runs.

        Parameters
        ----------
        directory : str
            Base directory for downloads. A subfolder named
            "{course_name} - {course_id}" is created within this directory.

        **params : dict
            Download options:

            include_video_files : bool, default False
                Include downloadable video files (MP4, Canvas Studio, etc.).

            include_audio_files : bool, default False
                Include downloadable audio files (MP3, M4A, etc.).

            include_image_files : bool, default False
                Include image files (JPG, PNG, etc.).

            flatten : bool, default False
                If True, all files go to date-based folders by type.
                If False, preserve course folder hierarchy.

            download_hidden_files : bool, default False
                If True, include hidden/unpublished content.

            flush_after_download : bool, default False
                If True, delete all downloaded files after processing.
                Use with caution - this is destructive.

        Notes
        -----
        - Creates download_manifest.yaml in the course folder to track progress
        - Skips files already in the manifest
        - Creates Windows shortcuts (.lnk) for files that fail to download
        - Only executes if self.exists is True

        Example
        -------
        >>> extractor.download_files(
        ...     "/downloads",
        ...     include_video_files=True,
        ...     flatten=True
        ... )
        """
        flush_after_download = params.get("flush_after_download", False)

        if self.exists:
            root_download_directory = os.path.join(directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")
            create_download_manifest(root_download_directory)
            self.download(self, root_download_directory, **params)

            if flush_after_download:
                self.clear_folder_contents(directory)

    def clear_folder_contents(self, directory: str) -> None:
        """
        Delete all downloaded content for this course.

        Removes all files and subdirectories within the course download
        folder, then removes the folder itself.

        WARNING: This is a destructive operation that cannot be undone.
        Use with extreme caution.

        Parameters
        ----------
        directory : str
            The parent directory containing the course folder.
            The course folder "{course_name} - {course_id}" within this
            directory will be completely deleted.

        Notes
        -----
        - Only executes if self.exists is True
        - Walks the directory tree bottom-up to remove files then folders
        - Finally removes the root course folder with shutil.rmtree

        Raises
        ------
        PermissionError
            If files are locked or in use.
        FileNotFoundError
            If the directory doesn't exist.

        Notes
        -----
        Uses Windows long path prefix (\\\\?\\) to handle paths > 260 characters.
        """
        if self.exists:
            root_download_directory = os.path.join(directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")

            # Check if directory exists
            if not os.path.exists(root_download_directory):
                return

            # Walk and delete with long path support
            for root, dirs, files in os.walk(root_download_directory, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    # Handle Windows long paths (> 260 chars)
                    if os.name == 'nt' and len(file_path) > 260:
                        file_path = "\\\\?\\" + os.path.abspath(file_path)
                    try:
                        os.remove(file_path)
                    except (FileNotFoundError, OSError) as e:
                        # Log but continue - file may have been deleted already
                        pass

                for name in dirs:
                    dir_path = os.path.join(root, name)
                    # Handle Windows long paths
                    if os.name == 'nt' and len(dir_path) > 260:
                        dir_path = "\\\\?\\" + os.path.abspath(dir_path)
                    try:
                        os.rmdir(dir_path)
                    except (FileNotFoundError, OSError) as e:
                        # Log but continue - directory may have been deleted already
                        pass

            # Remove the root directory
            try:
                if os.name == 'nt' and len(root_download_directory) > 200:
                    # Use extended path for shutil.rmtree as well
                    extended_path = "\\\\?\\" + os.path.abspath(root_download_directory)
                    shutil.rmtree(extended_path, ignore_errors=True)
                else:
                    shutil.rmtree(root_download_directory, ignore_errors=True)
            except Exception:
                pass  # Best effort cleanup

    # =========================================================================
    # Statistics Methods
    # =========================================================================

    def count_content(self) -> dict:
        """
        Count content items by type and file format.

        Generates a summary of content counts organized by category and
        file type. Useful for quick statistics about course content.

        Returns
        -------
        dict
            Content counts with structure::

                {
                    "documents": {
                        "pdf": 12,
                        "doc": 5,
                        "pptx": 3,
                        ...
                    },
                    "videos": {
                        "video_sites": 8,
                        "video_files": 2
                    }
                }

        Notes
        -----
        - Document counts are broken down by file_type (MIME class)
        - Video counts distinguish between sites (YouTube, etc.) and files
        - Does not currently count audio, images, or unsorted content

        Example
        -------
        >>> counts = extractor.count_content()
        >>> print(f"PDFs: {counts['documents'].get('pdf', 0)}")
        >>> print(f"YouTube videos: {counts['videos'].get('video_sites', 0)}")
        """
        content_counts = {
            "documents": {},
            "videos": {}
        }

        content = self.get_all_content()

        for document in content['content']['documents']['documents']:
            file_type = document.get('file_type')
            if file_type not in content_counts['documents']:
                content_counts['documents'][file_type] = 1
            else:
                content_counts['documents'][file_type] += 1

        for _ in content['content']['videos']['video_sites']:
            if "video_sites" not in content_counts['videos']:
                content_counts['videos']["video_sites"] = 1
            else:
                content_counts['videos']["video_sites"] += 1

        for _ in content['content']['videos']['video_files']:
            if "video_files" not in content_counts['videos']:
                content_counts['videos']["video_files"] = 1
            else:
                content_counts['videos']["video_files"] += 1

        return content_counts