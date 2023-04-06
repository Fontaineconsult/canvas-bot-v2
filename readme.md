# SF State CanvasBot

A command-line tool for downloading and organizing files from the Canvas LMS platform.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Export Data](#export-data)
- [Support](#support)
- [License](#license)

## Overview

The Simple Canvas LMS Downloader is a
Windows-only command-line tool that allows you
to download all files from your Canvas LMS courses,
including documents, videos, and images.
It also categorizes all URLs it finds into different
types of instructional materials and allows you to
export this information into a JSON file.
The primary target audience for this tool are
accessible media coordinators and instructional designers at universities.

## Requirements

- Windows operating system
- Canvas API key

## Installation

_TODO: Describe the installation process._

## Usage

_TODO: Describe how to use the command-line tool, including any necessary flags or options._

### Program Flags

<ul>
<li>--course_id TEXT The course ID to scrape</li>
<li>--course_id_list TEXT Text file containing a list of course IDs to
scrape. One per line.</li>
<li>--download_folder TEXT The Location to download files to.</li>
<li>--output_as_json TEXT Output the content tree as a JSON file. Pass the
directory to save the file to.</li>
<li>--include_video_files Include video files in download. Default is False</li>
<li>--include_audio_files Include audio files in download. Default is False</li>
<li>--include_image_files Include image files in download. Default is False</li>
<li>--flatten Excludes course structure and downloads all files
to the same directory. Default is False</li>
<li>--flush_after_download Deletes all files after download. Default is False</li>
<li>--download_hidden_files Downloads files hidden from students. Default is
False</li>
<li>--show_content_tree Prints a content tree of the course to the console.
Default is False</li>
<li>--reset_params Resets API key and config file. Default is False</li>
</ul>

### Obtaining a Canvas API key

_TODO: Provide instructions on how to obtain a Canvas API key._

## Export Data

_TODO: Describe how to export the organized data into a JSON file._

## Support

_TODO: Provide contact information for support or assistance._

## License

_TODO: Specify the license for the tool._