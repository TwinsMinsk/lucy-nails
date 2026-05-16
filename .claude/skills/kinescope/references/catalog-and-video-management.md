# Kinescope - Catalog-And-Video-Management

**Pages:** 10

---

## Advanced File Upload - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/advanced-file-upload/

**Contents:**
- Advanced File Upload
- Who this article is for
- Creating a project
- Upload options
  - Uploading one or multiple files
  - Uploading folders
  - File request
  - Upload by link
  - Uploading from cloud storage
  - Uploading via API

Uploading media files is the first and most important step in working with Kinescope. The platform supports several upload methods: drag-and-drop, upload by link, cloud storage integration, and others. Files are placed in projects that act as media libraries and allow applying bulk settings.

To start working with files, you need to create a project:

Click the “New project” button in the left menu of the “Catalog” section.

Creating a new project

In the dialog box that opens, enter a project name and configure parameters:

Enable encryption to protect files from downloading.

Specify default settings: player template and allowed domains for video embedding.

Project settings at creation

Kinescope supports six upload methods:

Drag files from your desktop to the project area, or select “New” → “Upload file”. Multiple files can be uploaded at the same time.

Uploading one or multiple files

To upload an entire folder, drag it to the project area or select “New” → “Upload folder”.

Request files from external users without giving them access to the platform:

Creating a file request

Add video from the internet:

Uploading video by link

Kinescope supports integration with Google Drive and Dropbox. The set of services may vary depending on the user’s geographic location.

Uploading files from cloud storage

API methods are available for developers to automate file uploads to Kinescope. Full documentation can be found in the developer guides section .

Kinescope works with most popular video formats, including MP4, MOV, WMV, AVI, and FLV. Video is displayed with the correct aspect ratio in any format.

Project files such as imovieproject and dvdproj, or other non-video files (such as MP3, JPG, or PNG), are not supported.

All videos uploaded to Kinescope are automatically converted to constant frame rate (CFR) format. This ensures videos play stably on any device and in the player without issues.

If the source file has a variable frame rate (VFR), problems may occur:

To avoid these errors, we recommend setting a constant frame rate in your editing software in advance.

The values below are recommendations for videos uploaded to Kinescope. Note that audio bitrate is not related to video resolution.

Recommended bitrate for SDR videos

After uploading files, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

---

## Analytics - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/analytics/

**Contents:**
- Analytics
- Who this article is for
- Accessing analytics
- Key metrics
- Report export
  - How to build a report
  - Period
  - Report fields
  - Things to keep in mind
- Advanced analytics for developers

Kinescope analytics collects data on the total number of views and player loads, watch depth, audience geography, platforms, OS, and browsers. This data helps you understand how your audience interacts with your content and optimize your video strategies.

Analytics is available both for individual videos and for the entire workspace:

Analytics for a specific video

For all videos in the workspace

Overall workspace analytics

Overall analytics also includes the top 25 most popular videos. You can find it at the bottom of the page.

Top 25 most popular videos

Views Shows the number of video starts. A view is counted after 5 seconds of continuous playback.

Player loads Shows how many times the player with the video was loaded on a page. If you open a page with video and then refresh it, that counts as two player loads.

This metric roughly reflects interest in the video, the effectiveness of player placement, or the attractiveness of the poster.

Unique impressions The player remembers the device session and counts uniqueness by session.

Unique impressions metric

Engagement or watch depth Shows the average watch time (how many minutes a user watched out of the total video length) and how that value changed over the selected time period.

A view is counted within a single session: in one session a user can watch the video multiple times, but it is counted as one view.

If within one session a user rewatches the same segment multiple times, it counts as one view of that segment.

This metric shows how high-quality the content is — and therefore how well it can hold viewer attention.

Engagement and watch depth metric

Top countries, platforms, and OS View data broken down by country, platform (desktop, tablet, smartphone), and operating system.

Geography, platforms, and operating systems

Referrers (placement sources) Shows which pages and domains the player loads on, and how effective each placement is. Useful for comparing traffic quality across sources and finding placements with a low view rate.

Open the “Referrer” sub-tab in the “Analytics” tab — it shows a table with the columns:

Rows are grouped by domain: the domain appears as a parent row with total metrics, and individual pages are listed under it. Groups can be collapsed and expanded. The period can be set using the filter (“Last 24 hours”, “This week”, “This month”, “All time”, or “Period”). Data can be exported to CSV or XLSX using the “Export” button.

If there is a lot of data or you need to feed it into your own reporting, export the analytics to a file. The report is built in the background on the Kinescope side, and once it is ready it arrives at the specified email as a ZIP archive containing a CSV or XLSX file. Inside the archive each row corresponds to one video, broadcast, or stream recording — data is grouped by identifier.

Export report dialog: file format, date range, columns, and email

The report settings dialog will close. When the report is ready, an email with a link to the ZIP archive will be sent to the specified address.

Both fixed ranges and a custom period are available:

Fields are split into three groups. Some fields appear in the report only for the matching content type — for example, the broadcast identifier is exported only for stream events.

Content identification

For deeper analysis and integrating analytics into your systems, two approaches are available:

IFrame Player API helps collect client-side events and send them to your analytics platform along with context (for example, user ID, course, lesson, device, browser). This is typically used when you need to:

Using IFrame Player API, you can capture not just views but detailed events (pauses, rewinds, replays) and react to them in real time.

Learn more about IFrame Player API capabilities in the article IFrame Player API .

All analytics data is also available via REST API. Capabilities include:

Analytics API (for developers):

Overall statistics for a period:

Detailed statistics with grouping:

If parameters are invalid, the API returns a validation error with code 400400. For example, if the required from or to parameters are missing, or an invalid sort field is specified (code 400216). Learn more about error handling in the general API guidelines .

Additional value can be gained by linking player view data to user sessions. This approach lets you collect analytics not just around video, but around specific viewers.

To personalize analytics, embed the player using IFrame API , and when creating the player on a page pass the user identifier (such as email or ID) via the externalId parameter.

After exploring analytics, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

**Examples:**

Example 1 (bash):
```bash
curl -X GET "https://api.kinescope.io/v1/analytics/overview?from=2024-01-01&to=2024-01-31" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"
```

Example 2 (bash):
```bash
curl -X GET "https://api.kinescope.io/v1/analytics?from=2024-01-01&to=2024-01-31&group_by=video_id&order=views.desc&per_page=10" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"
```

---

## Built-in Video Editor - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/built-in-video-editor/

**Contents:**
- Built-in Video Editor
- Who this article is for
- How to open the editor
- Scenario 1: Trimming the beginning and end of a video
- Scenario 2: Cutting a segment from the middle of a video
- Scenario 3: Splitting a long video into multiple parts
- Save types — what’s the difference
- What’s next?
- Related articles
  - Table of contents

The Kinescope built-in video editor lets you make basic changes to video directly in the browser, without downloading or installing third-party software. The tool is suitable for quick trimming, removing unwanted segments, and adjusting audio before publishing or embedding.

The video editor for the selected video opens. The interface includes a player for preview, a timeline with an audio track, and a toolbar — all elements are labeled.

Kinescope built-in video editor interface

Use this when you need to remove an intro, a pause at the end of the recording, or dead time at the beginning.

Preview the result in the player and repeat the steps if needed. Use “Undo” if you made a mistake.

Useful when you need to remove a slip, an awkward pause, or an unwanted take from a recording.

Check the join in the player — the transition should be smooth.

When a lecture or webinar recording needs to be broken into separate lessons or episodes:

Repeat for each subsequent part.

The “Save” menu offers two options:

After editing, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — we’ll help.

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Organizing video content in Kinescope: creating projects and folders, managing files, using tags for cataloging and quick search.

---

## Catalog and Video Management - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/

**Contents:**
- Catalog and Video Management
- Who this section is for
- Where to start
  - If you’re new to the catalog
  - If you already work with the catalog
- Key capabilities
  - Content organization
  - Media file settings
  - Playlists
  - Search and filtering

The catalog is the central place for organizing and managing your video content in Kinescope. Here you can create projects, group videos by folders and tags, set up playlists, search for files, and track view analytics.

Use projects, folders, and tags to structure your media library. The interface resembles a familiar file system, making it easy to manage.

More about organizing your media library →

Configure privacy, access, and embedding for each video. You can set default settings for the project or configure each file individually.

More about settings →

Combine videos into sequential collections for courses, product demos, or presentations. Playlists support a strict playback order.

More about playlists →

Quickly find files by name, tags, upload date, and other parameters. The search bar with filters helps when working with large media libraries.

Track views, engagement, content popularity, geography, and audience behavior. Analytics helps optimize your video strategies.

More about analytics →

Add subtitles for accessibility, create chapters for video navigation, and upload additional audio tracks for multilingual content.

More about working with files →

Make edits directly in the browser: trim, cut segments, split into parts — without exporting to an external editor.

More about the video editor →

Deleted files, projects, and folders move to the recycle bin, where they are stored for 30 days. Accidentally deleted content can be easily restored.

More about the recycle bin →

After organizing your catalog, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

Organizing video content in Kinescope: creating projects and folders, managing files, using tags for cataloging and quick search.

Creating playlists in Kinescope: combining videos into sequential collections for courses, product demos, or presentations with embedding support.

Searching the Kinescope catalog: quickly find files by name, filters by author, tags, domains and upload status, sorting results.

Kinescope analytics: views, player loads, watch depth, referrers, geography, platforms, browsers, and exporting reports to CSV or XLSX.

Ways to upload files to Kinescope: drag-and-drop, upload by link, from cloud storage, requesting files from external users, and other options.

Managing the recycle bin in Kinescope: restoring deleted files, configuring retention period, emptying the bin, and access rights.

---

## Catalog Search - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/catalog-search/

**Contents:**
- Catalog Search
- Who this article is for
- Search by name
- Filters for advanced search
  - Adding filters
  - Sorting matches
- What’s next?
- Related articles
  - Table of contents

Can’t remember which project or folder a media file is in? Kinescope has a convenient search bar that helps you quickly find content regardless of its location. Search supports filters by various parameters and result sorting.

To access the search panel, simply click the bar at the top of the project workspace.

Search bar in the catalog

If you know the media file name, enter it in the search bar. Kinescope will display all matches from your catalog as a list.

Search results by name

If you don’t know the exact name or need a detailed search, use filters. Kinescope supports the following categories:

Filters for advanced search

You can combine multiple filters. Results update as each new filter is added.

Filters work in two modes: include and exclude. For example, you’re looking for a file and you (don’t) know who uploaded it:

If there are many matches, use result sorting. Available options:

After configuring search, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

---

## Media File Settings - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/media-file-settings/

**Contents:**
- Media File Settings
- Who this article is for
- Basic parameters
- Name, subtitle, and description
  - Name
  - Subtitle and description
- Selecting a poster
  - Uploading a poster
  - Selecting a frame from the video
- Downloading video posters from Kinescope via direct links

Before publishing a media file, you need to configure its basic parameters: name, description, poster, tags, privacy, and other settings. These parameters affect the video’s visibility in search engines, ease of search in the catalog, and content accessibility for viewers.

The “General” tab includes the following parameters:

General media file settings tab

The name should be concise but informative. It helps viewers understand the video’s content and affects visibility in search engines.

The subtitle complements the name and clarifies the video topic, while the description helps viewers and search engines understand what the video is about.

Click “Save” to finish editing.

Auto-generate description (beta)

This feature automatically generates a description based on the video content. It is currently in open beta testing. To participate, write to the support chat within the Kinescope interface.

The poster is a key visual element of the media file. It appears everywhere the video is published: in search results, on video pages, and in link previews.

By default, Kinescope automatically selects a poster. For videos longer than 30 seconds, the system picks a frame from the first scene change after the 30-second mark. If no such frame is found, the 25th frame is used. However, this choice doesn’t always reflect the video’s essence, so you can upload your own poster or select a suitable frame from the video. To do this, open the “Add poster” dropdown and select “Upload poster” or “Select frame”.

Selecting a frame from the video for a poster

If you want to upload a custom poster image:

To make the poster look good, make sure the poster’s aspect ratio matches the video’s — you can find the video’s aspect ratio in the “Files” tab.

You can also select a frame from the video itself to use as a poster:

You can download posters from Kinescope videos via direct links. Posters are available in different formats (JPG and WEBP) and different sizes.

If you need a poster in standard (default) size, use the following link format: JPG: https://kinescope.io/<video_link>/poster.jpg

WEBP: https://kinescope.io/<video_link>/poster.webp

Simply open the desired link in a browser or use right-click → “Save image as…”.

If you need a poster in a specific size, replace {size} in the URL with one of these values:

Small poster (sm) in JPG format: https://kinescope.io/<video_link>/poster/sm.jpg

Medium poster (md) in WEBP format: https://kinescope.io/<video_link>/poster/md.webp

Tags help structure media files and improve their search visibility. For example, a video about growing oranges might have the tags “oranges”, “trees”, “gardening”.

The tag manager in Kinescope lets you view, add, edit, or delete tags. To access it:

Tag manager in media file settings

Accessing the tag manager from profile settings

To modify an existing tag:

Editing a tag in the tag manager

Unused tags can be archived or deleted:

Archiving and deleting tags

Archived tags can be restored via the “Archive” tab → “Restore tag”.

Tag archive tab in the tag manager

To see media files linked to a specific tag:

Media files linked to a tag

Privacy settings in Kinescope let you precisely control who can view your media files and where. You can control access to your files and regulate their embedding, as described below.

To configure access settings, open the “Who can view?” field in the privacy settings and choose one of five levels:

Video access settings in privacy configuration

Unique codes limit viewing to people you give a code to — handy for webinars and private screenings without sign-up. Under “Privacy”, in “Who can view?”, select “Users with unique codes”, then “Manage codes”: generate a batch, download the file, and share the video link and codes with viewers.

For a full walkthrough with screenshots, what viewers see, deleting batches, and FAQs, see Video access restrictions (section Access by unique codes).

Kinescope lets you restrict media file embedding by domain, so you can place content only on trusted websites. This setting is available in the “Where can the player be shown?” section and offers three options:

Embedding domain settings for a media file

To allow media file embedding on specific domains:

To remove a domain from the trusted list:

Using the “Domain manager”, you can add, edit, and delete domains, as well as view their linked media files:

If a domain is no longer in use, you can:

To do this, click the “Archive domain” or “Delete” icon next to the domain. In the dialog box, select the desired action. Archived domains can be restored in the “Archive” tab by clicking “Restore domain”.

In the “Player” section, you can select a ready-made player template for the video and modify the settings of the selected template. If you change the template settings, they will also apply to all videos using that template.

Getting familiar with player settings is straightforward — learn more in the section .

Customize player for a media file

If you need to update a file while keeping the link, embed code, analytics, tags, poster, privacy settings, and other data unchanged, use the “Versions” feature.

After upload completes, the old version is automatically deleted, and the “Versions” block shows information about the current file (name, date and time of replacement, name of the user who replaced it).

Kinescope offers two ways to publish: direct links and embed codes.

Sharing access options for a media file

To embed media on websites and platforms:

Use the additional parameters to configure size and aspect ratio. You can also use the three-dot menu in the upper-right corner of the settings panel and select “Copy link” → “Copy embed code” (by default, the fixed embed code is copied).

After configuring the basic media file parameters, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

Organizing video content in Kinescope: creating projects and folders, managing files, using tags for cataloging and quick search.

---

## Organizing Your Media Library in Kinescope - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/organizing-media-library/

**Contents:**
- Organizing Your Media Library in Kinescope
- Who this article is for
- Projects
  - How to create a project
  - Managing projects
  - Searching the project list
    - How the search works
    - Clearing the query
  - Project order in the catalog
- Folders

The Kinescope media library lets you organize your videos, recordings, and other materials into projects and folders, making collaboration, content management, and file search easier. The interface resembles a familiar file system, so it’s easy to manage.

Projects are the primary level of media library organization. They are separate content groups you can use to separate by topic, client, or area of work.

Alternative: via the projects tab in the right panel of the dashboard.

Creating a new project in the catalog

Project settings in the catalog

When there are many projects in your workspace, scrolling through the left-hand list becomes inconvenient. To quickly open the project you need without leaving the catalog:

Example: the query Mar returns the projects “Marketing Plan” and “My march trip”; the query M returns only projects that start with the letter “M”, such as “Mobile App”.

The clear icon becomes active as soon as there is at least one character in the field. Clicking it empties the field, the list shows all projects again, and the focus stays in the search field — so you can immediately start a new query.

Searching the project list and drag-and-drop for reordering

The order of projects in the left-hand list is set manually by drag-and-drop. This is convenient when several people work with the list and you want to keep the projects you return to most often at the top.

Reordering works separately within two list groups:

You cannot move a project from one group to the other by dragging — to do that, pin or unpin the project via the context menu (⁝).

Folders help structure content within a project. This is especially useful when working with large volumes of material. For example, in an “Employee Training” project, folders could be named “Introduction”, “Case Studies”, “Practice”.

Creating a folder in a project

To add videos or other materials to a project:

Learn more about advanced file upload .

The article Media file settings describes all media file settings.

Deleted files go to the recycle bin and are stored there for the configured period. They continue to occupy storage space until the bin is fully emptied.

Tags are keywords you can assign to projects, folders, and files for quick search. To add tags:

There’s more to tags — learn about all their capabilities in the article Media file settings .

Adding tags to a media file

Playlists can be created within projects and folders. To add a video, simply drag it into the playlist. Playlists can be embedded on a website just like individual videos.

We cover playlist capabilities in detail in the article Playlists .

Any project, folder, or file can be deleted via the right-click context menu. After deletion, items go to the recycle bin and are stored there for 30 days by default. The retention period can be changed. Learn how in the article Recycle bin .

After organizing your media library, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

---

## Playlists - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/playlists/

**Contents:**
- Playlists
- Who this article is for
- Creating a playlist
- Adding files to a playlist
- Managing files
- Playlist settings
  - General
  - Privacy
  - Player
- Embedding a playlist

Playlists are a convenient tool for creating sequential video collections that can be embedded on a website. Playlists support a strict playback order, making them ideal for courses, product demos, or presentations.

Method 1: Convert a folder to a playlist

Creating a playlist from a folder

Method 2: Create a new playlist

Creating a new playlist

Playlists support sorting by name, creation date, duration, and other parameters. The default order is custom.

Settings are accessible via the right-click context menu on the playlist name in the Catalog, or via the (⁝) three-dot menu when hovering over the playlist row → “Settings”.

Name: not indexed by search engines if the video is protected by privacy settings or SEO optimization is disabled in the “Advanced” tab.

This tab is in the settings of the player template applied to the playlist.

Description: not indexed by search engines if the video is protected by privacy settings or SEO optimization is disabled in the “Advanced” tab of the player template settings applied to the playlist.

Tags: help organize and find playlists. Multiple tags can be added to one playlist. All created tags are managed in workspace settings → “Tag manager”.

The password or link is unique to each playlist but can be changed or disabled.

Select one of the ready-made templates or create a new one. The selected template applies to all videos in the playlist.

Learn more about customizing player design and behavior in the article Player customization .

A playlist is embedded just like a regular player. The embed code lets you place it on a website with the ability to switch between videos.

Learn more in the article Embedding .

If you want the playlist to start from a specific video, add the ?start_item=1 parameter to the URL.

https://kinescope.io/pl/5ifZjJLLGYncrHYBdPNhKE

Embedding a playlist in documentation:

After creating a playlist, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

---

## Recycle Bin - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/recycle-bin/

**Contents:**
- Recycle Bin
- Who this article is for
- Emptying or restoring
  - Full empty or restore
  - Selective empty or restore
- Retention period
- Storage pricing
- Recycle bin access rights
- Sorting and searching files
- What’s next?

The recycle bin helps you avoid losing media files. Deleted files and folders go to the bin and are kept for 30 days by default. This period can be changed. After the period expires, files are deleted automatically, but you can also empty the bin fully or selectively at any time.

Selectively restoring files from the bin

Recycle bin menu with empty and restore options

Deleted files are available in the bin for the configured period. You can adjust the period via the menu (⁝) next to the bin icon → “Retention period”. Available options:

Sorting and searching files in the bin

Storing files in the bin is billed according to your chosen plan: learn more here . To avoid extra charges, regularly empty the bin or change the retention period for files in it.

Only users with the roles “Editor”, “Editor+”, and “Administrator” have access to empty or restore from the bin. Learn more about roles in the Team management section.

The list of deleted items is available in the bin for the configured retention period. The upper-right corner shows the total number of files and their combined size. Sorting options by date, size, and other parameters are also located there.

Configuring file retention period in the bin

After working with the recycle bin, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Working with additional materials in Kinescope: subtitles and AI auto-generation, chapters (including AI), annotations, attachments, audio tracks, and supplementary videos for improved content accessibility.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

---

## Working with Files: Subtitles, Chapters, and More - Kinescope Help center

**URL:** https://docs.kinescope.com/catalog-and-video-management/working-with-files/

**Contents:**
- Working with Files: Subtitles, Chapters, and More
- Who this article is for
- Annotations
  - How to add annotations
- Supplementary videos
  - How to add a supplementary video
- Attachments
  - How to add attachments
- Subtitles: generating and managing
  - How to upload subtitles

You can mark up chapters for quick navigation to key video segments, attach supplementary materials (such as images or PDF files), and upload subtitles. These features improve content accessibility and help viewers navigate video more easily.

File interactions tab

Annotations are a tool that helps viewers quickly understand the video content and find key moments through brief explanations.

The annotation will appear on the timeline below the video. You can move it along the timeline and add new annotations to other points in the video.

This feature lets you place a link to another video from Kinescope directly in the player. For example, if you briefly mention a topic in a video, you can add a link to a video with a more detailed explanation.

Save changes to make the video accessible in the player. You can move the links on the timeline and add other videos to empty sections.

The “Attachments” feature lets viewers access supplementary materials while watching a video. This is convenient if you want to provide access to presentations, instructions, or other downloadable files.

Viewers will be able to open and download attachments by clicking the paperclip icon in the player.

Uploading subtitles in video settings

Use auto-generation to speed up working with subtitles.

AI subtitle generation in video settings

Open video settings → Subtitles tab.

Click AI Auto-generate and select the subtitle language. While processing, the subtitles block shows a loading indicator. Editing subtitles and menu after auto-generation

Review the result. You can add, merge, or delete text manually. In the additional options menu (⋮), you can also replace, download, and adjust timings.

Select the generated subtitles, turn on Show in player (if not already on), and click Save.

Adding chapters lets viewers easily find the moments they need and share specific segments of long videos.

Adding chapters to a video

Placing chapters in a long video manually takes time. Auto-generation helps: it analyzes the video and suggests timecodes with titles.

Open video settings → Chapters tab.

Click the gear icon next to AI Auto-generate if you want to change settings:

— Maximum number of chapters — up to 99 (default 30). — Generation language — language of chapter titles.

Click AI Auto-generate. While processing, a loading indicator appears in the chapters block.

Review the result. You can edit titles and timecodes manually, and add missing chapters with Add chapter in the preview.

Enable Enable table of contents (if not already on) and click Save.

AI chapter generation in video settings

You can combine auto-generation and manual markup: generate a draft, then refine it.

This section shows a list of available video resolutions that are automatically created when files are uploaded to Kinescope. During playback, the video resolution adapts to the player placement on the site, device, and viewer’s internet speed.

List of available video resolutions

You can download the version of the video or subtitles you need:

Kinescope supports adding multiple tracks to a video, uploaded as a single file — for example, packaged using MKVToolNix.

Kinescope supports lead forms in video, but they cannot be configured independently yet. The development team will help you add lead forms to your video content — simply contact the support chat within the Kinescope interface.

Example call to action at the end of a video

After configuring file interactions, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Configuring media files in Kinescope: name, description, poster, tags, privacy (incl. unique codes), player, versions, and sharing access.

Trim, cut segments, and split video right in the browser — without exporting to an external editor. Working with the Kinescope built-in video editor.

Organizing video content in Kinescope: creating projects and folders, managing files, using tags for cataloging and quick search.

---
