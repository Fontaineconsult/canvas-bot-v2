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


### Course Content Tree

The SF State CanvasBot will generate a content tree of the course you are downloading.
This tree will show you the structure of the course and the files that are included in each module.
The tree will also show you the type of file that is included in each module.
The following is an example of a course content tree:


![Canvas Tree](https://dprc-photos.s3.us-west-2.amazonaws.com/CourseTree.PNG)




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

### Export Course Data as JSON

_TODO: Describe how to export the organized data into a JSON file._

## Support

This tool is a work in progress. Please contact me at <fontaine@sfsu.edu> if you have any questions or suggestions.

## License

MIT License

Copyright (c) 2023 Daniel Fontaine

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.