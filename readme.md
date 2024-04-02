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

The SF State CanvasBot is a
Windows-only command-line tool that allows you
to download all files from your Canvas LMS courses,
including documents, videos, and images.
It also categorizes all URLs it finds into different
types of instructional materials and allows you to
export this information into a JSON file.
The primary target audience for this tool are
accessible media coordinators and instructional designers at universities.


There are currently 10 different content types:

<ul>
<li>Documents</li>
<li>Image Files</li> 
<li>Audio Files</li>
<li>Video Files</li>
<li>Video Websites</li>
<li>Audio Websites</li>
<li>File Storage Sites</li>
<li>Digital Textbooks</li>
<li>Document Site</li>
<li>Unsorted</li>
</ul>




## Requirements

- Windows operating system
- Canvas API Access Token

## Installation

Please download the v0.1.0-alpha executable here. [SF State CanvasBot Windows Executable](https://github.com/Fontaineconsult/canvas-bot-v2/releases/download/v0.1.1-alpha/canvas_bot.exe)

This usage guide covers how to use this tool on the command line using the executable version available above. If you would like to use the source code, please close this repository. 

This is a standalone executable. You do not need to install Python or any other dependencies.

### Configuration


CanvasBot requires three pieces of information to run:

- Canvas API Access Token
- Canvas Page Course Root
- Canvas API URL

#### Canvas API Access Token

The Access Token is a unique string of characters that allows you to access the Canvas API. Please see the obtaining an access token section below for more information.

#### Canvas Page Course Root

The Canvas Page Course Root is the URL of the page that lists all of your courses. This is the page that you see when you log into Canvas. The URL will look something like this:

    https://school.instructure.com/courses

#### Canvas API URL

The Canvas API Url is the URL of the Canvas API. This is the URL that you use to access the Canvas API. The URL will look something like this:

    https://school.instructure.com/api/v1

Please consult with your Canvas administrator if you are unsure of the Canvas API URL.

### Permission Requirements

The CanvasBot only requires read access to a canvas course. It does not require any write access. As a Canvas LMS account holder who is likely providing support services for Faculty, we recommend that you advocate for the creation of a Canvas LMS account that is granted read access to all courses. This account should not be granted write access to any courses.


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

    canvas_bot.exe --course_id 12345 --download_folder "C:\Users\Downloads"


By default, the program only downloads document-like files, such as PDF and MS Word. If you want to download other file types, such as videos and images, you will need to pass the following flags:

    canvas_bot.exe --course_id 12345 --download_folder C:\Users\Downloads --include_video_files --include_audio_files --include_image_files

#### Download Manifest

The bot will track which files have been successfully downloaded. This is done by creating a file called `download_manifest.json` in the same directory as the course specified by `--download_folder`.
This file contains a list of all the files that have been downloaded. If you want to download all files again, you will need to delete the course folder. The workflow that inspired this project comes
from student workers. We want the students to be able to run the bot every day any only work on files that have been added since the last time they ran the bot. Consequently, each time the bot runs, a new folder is created with the current date. The bot will only download files that are not in the download manifest.
If there are no new files to download, the bot will not create a new folder.


#### Shortcuts

If for any reason the bot was unable to successfully download a file,
it will create a shortcut to the URI where the file was found.
The user can investigate why the resource was unavailable.


### Flattening the Course Structure

By default, the program will download files into a folder structure that matches the course structure.
If you want to download all files into a single folder, you will need to pass the `--flatten` flag.

    canvas_bot.exe --course_id 12345 --download_folder C:\Users\Downloads --flatten

Flattening the course structure makes it easier to work with all the files in a course. 

### Export Course Data as JSON

All course data can be exported as a JSON file. This file contains all the URLs found in the course,
categorized by content type.

    canvas_bot.exe --course_id 12345 --output_as_json "C:\Users\Downloads"


The following is an example of a JSON file:

    {
        "course_id": 12345,
        "course_name": "Course Name",
        "course_url": "https://canvas.instructure.com/courses/12345",
        "content": {
            "documents": [
                {
                    "file_type": "pdf",
                    "is_hidden": false,
                    "order": 3,
                    "scan_date": "2023-04-05 10:57:11.526804",
                    "source_page_type": "Page",
                    "source_page_url": "https://sfsu.instructure.com/courses/17899/pages/a-course-page",
                    "title": "a_pdf_file_in_a_course.pdf",
                    "url": "https://school.instructure.com/files/134695/download?download_frd=1&verifier=3t2tg2tg4g4g34g34g43g"

                }
            ]
            "videos":
                "video_sites": [
                    {
                    "is_hidden": false,
                    "order": 17,
                    "scan_date": "2023-04-05 10:57:11.527797",
                    "source_page_type": "Discussion",
                    "source_page_url": "https://sfsu.instructure.com/courses/17899/discussion_topics/94137",
                    "title": "How A Folk Singer\u2019s Murder Forced Chile to Confront Its Past",
                    "url": "https://www.youtube.com/watch?v=j-8nhA-j2yo"
    
                    }
                ]
                "video_files": [
                    {
                        "file_type": "mp4",
                        "is_hidden": false,
                        "order": 3,
                        "scan_date": "2023-04-05 10:57:11.526804",
                        "source_page_type": "Page",
                        "source_page_url": "https://sfsu.instructure.com/courses/17899/pages/a-course-page",
                        "title": "a_video_file_in_a_course.mp4",
                        "url": "https://school.instructure.com/files/1213695/download?download_frd=1&verifier=3t2tg2tg4g4g34g34g43g"
    
                    }
            ]

        }
    }

The ability to export a course's instructional material content in JSON is a usefull feature. You can use this data to
easily build your own accessible media integrations. 


### Course Content Tree

The SF State CanvasBot will generate a visual content tree of the course you are downloading.
This tree will show you the structure of the course and the files that are included in each module, page etc.
The following is an example of a course content tree:


![Canvas Tree](https://dprc-photos.s3.us-west-2.amazonaws.com/CourseTree.PNG)


### Logging

The SF State CanvasBot will generate a log file of the course you are downloading. Errors and warnings will be logged to this file.


### Excel File

The SF State CanvasBot will generate a macro enabled Excel file of the course you are downloading. You will need to enable
macro support in Excel to use this feature.

Content is divided into sheets by type:

* Documents
* Document Sites
* Image Files
* Video Files
* Video Sites
* Audio Files
* Audio Sites
* Unsorted

The Excel file can use the save path of files you download as hyperlinks, making it easy to directly inspect documents.


### Video Caption Inspection.

Currently this only supports the YouTube API. setting the `'--check_video_site_caption_status'` flag will tell the bot
to check if a YouTube vide is captioned. 


### Program Flags

| Flag                                | Description                                                                                       | Default |
|-------------------------------------|---------------------------------------------------------------------------------------------------|---------|
| `--course_id TEXT`                  | The course ID to scrape                                                                           |         |
| `--course_id_list TEXT`             | Text file containing a list of course IDs to scrape (one per line)                                |         |
| `--download_folder TEXT`            | The location to download files to                                                                 |         |
| `--output_as_json TEXT`             | Output the content tree as a JSON file (pass the directory to save the file to)                   |         |
| `--output_as_excel TEXT`            | Outputs course content into an excel file sorted by type (pass the directory to save the file to) | False   |
| `--include_video_files`             | Include video files in download                                                                   | False   |
| `--include_audio_files`             | Include audio files in download                                                                   | False   |
| `--include_image_files`             | Include image files in download                                                                   | False   |
| `--flatten`                         | Excludes course structure and downloads all files to the same directory                           | False   |
| `--flush_after_download`            | Deletes all files after download                                                                  | False   |
| `--download_hidden_files`           | Downloads files hidden from students                                                              | False   |
| `--show_content_tree`               | Prints a content tree of the course to the console                                                | False   |
| `--reset_params`                    | Resets API Token and config file                                                                  | False   |
| `--check_video_site_caption_status` | Checks if a video has captions (currently only YouTube)                                           | False   |
| `--reset_canvas_studio_params`      | Deletes Canvas Studio Client ID and Secret and re-initialized the auth flow                       | INFO    |

### Obtaining a Canvas API Access Token

Please contact your Canvas LMS campus administrator to enable your account to use the Canvas API.
Once your account has been enabled, you will need to obtain an API access token.
This token will be used to authenticate your account when using the SF State CanvasBot.

The API Token is stored as an encrypted password using Windows Credential Vault. 

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

If you've entered the wrong token, you can reset the token by running the program with the `--reset_params` flag.

    canvasbot.exe --reset_params

## Support

This tool is a work in progress. Please contact me at <fontaine@sfsu.edu> if you have any questions, suggestions or bug reports.



### Version History

#### 0.1.2

* Added support for macro enabled excel workbook to help view all content in a course. 
* YouTube API added for video caption inspection.
* Logging Added


#### 0.1.5

* Many bug fixes
* Added support for canvas studio


#### 0.1.6

* Many more bug fixes
* Added a way to find embeded canvas studio videos rather than relying only on videos uploaded directly to Canvas Studio.


### Future Features

- [ ] Add GUI interface for easier use
- [ ] Add the ability to easily customize the filters for what content is tracked.
- [ ] Add better support scraping Box, DropBox, Google Drive, etc.

### Known Issues

- [ ] Windows is finicky about the directory paths used to create shortcuts. I'm still testing to work out the best way to handle this.
- [ ] Directory paths can also be very long depending on the title of courses and modules. This can cause issues with Windows.


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