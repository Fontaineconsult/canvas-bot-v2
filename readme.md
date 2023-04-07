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
- Canvas API Access Token

## Installation

Please download the executable here. **[SF State CanvasBot Windows Executable](https://dprc-photos.s3.us-west-2.amazonaws.com/canvas_bot.exe)

This usage guide covers how to use this tool on the command line using the executable version available above. If you would like to use the source code, please close this repository. 

_TODO: Describe the installation process._

## Usage


### Scraping a single course. 


To scrape a single course, you will need to know the course ID. In command prompt or powershell, navigate to the directory where you downloaded the executable.

Run the following command:

    canvas_bot.exe --course_id 12345


### Scraping multiple courses
To scrape multiple courses, you will need to create a text file with a list of course IDs. Each course ID should be on a new line. In command prompt or powershell, navigate to the directory where you downloaded the executable.

    canvas_bot.exe --course_id_list course_ids.txt


### Downloading Files
To download files, you will need to specify a download folder. In command prompt or powershell, navigate to the directory where you downloaded the executable. Pass the flag `--download_folder` and the path to the download folder. Make sure to quote your path if it contains spaces.

    canvas_bot.exe --course_id 12345 --download_folder C:\Users\Downloads

By default, the program only downloads document like files, such as PDF and MS Word. If you want to download other file types, such as videos and images, you will need to pass the following flags:

    canvas_bot.exe --course_id 12345 --download_folder C:\Users\Downloads --include_video_files --include_audio_files --include_image_files


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

### Obtaining a Canvas API Access Token

Please contact your Canvas LMS campus administrator to enable your account to use the Canvas API.
Once your account has been enabled, you will need to obtain an API access token.
This token will be used to authenticate your account when using the SF State CanvasBot.

Canvas Integrations can be accessed in your account settings. <br> Go to Account > Settings > Approved Integrations.
Click on the New Access Token button to generate a new access token. <br>
![Canvas Integration](https://dprc-photos.s3.us-west-2.amazonaws.com/AddAPIToken.PNG)

Give a name to your token and click Generate Token. <br>
![New Access Token](https://dprc-photos.s3.us-west-2.amazonaws.com/NewAccessToken.PNG)

Copy the token. Once copied you won't be able to see it again. <br>
![Access Token Details](https://dprc-photos.s3.us-west-2.amazonaws.com/AccessTokenDetails.PNG)

Once the token has been generated, you will need to enter it into the SF State CanvasBot.
When you first run the program you will be prompted.<br>
![Access Token Details](https://dprc-photos.s3.us-west-2.amazonaws.com/EnterAccessToken.PNG)


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