# Kinescope - Video-Player

**Pages:** 4

---

## Advertising - Kinescope Help center

**URL:** https://docs.kinescope.com/video-player/advertising/

**Contents:**
- Advertising
- Who this article is for
- Using the adtagurl parameter
  - Example with multiple parameters
- Configuration via IFrame API
- Advertising tag types
- Recommendations
- Limitations
- What’s next?
- Related articles

The Kinescope player supports advertising tag integration via the adtagurl parameter. This allows showing ads during video playback.

Add the adtagurl parameter with the advertising tag URL to the iframe URL:

You can combine the adtagurl parameter with other parameters:

For more flexible ad configuration, use IFrame Player API . See the full documentation for all API capabilities:

The player supports various advertising tag formats:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Kinescope player customization: templates, appearance, controls, behavior; settings menu including subtitle search, scale, default playback speed, and downloading video via direct link and transcriptions.

Embedding — a way to place video on a site. Where to get the code (adaptive, fixed, LLM-friendly), parameters and optimization.

**Examples:**

Example 1 (sass):
```sass
<iframe src="https://kinescope.io/embed/123456789?adtagurl=https://example.com/ad-tag.js"
        allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
        frameborder="0"
        allowfullscreen></iframe>
```

Example 2 (sass):
```sass
<iframe src="https://kinescope.io/embed/123456789?adtagurl=https://example.com/ad-tag.js&autoplay=1&muted=1"
        allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
        frameborder="0"
        allowfullscreen></iframe>
```

Example 3 (javascript):
```javascript
import { createPlayer } from '@kinescope/iframe-api';

const player = await createPlayer({
  videoId: '123456789',
  adTagUrl: 'https://example.com/ad-tag.js'
});
```

---

## Embedding - Kinescope Help center

**URL:** https://docs.kinescope.com/video-player/embedding/

**Contents:**
- Embedding
- Who this article is for
- Prerequisites
- Using embed code
  - Where to find the code?
  - AI-compatible code (LLM-friendly)
  - Configuring player dimensions
  - Code usage example
- Embedding parameters
  - Playback of video fragments

Embedding is a way to place video on a site. Kinescope provides embed codes for this: adaptive and fixed.

Before embedding the player, make sure:

Embed code is a code snippet used to add a player with a media file to a web page.

There are two types of embed codes: adaptive and fixed. Adaptive code automatically adjusts the player size to the user’s screen size and displays correctly on mobile devices. Fixed code maintains set player dimensions on all devices. If a transcript is available, an AI-compatible (LLM-friendly) code is also available.

Code type selection window in video settings

The code can also be copied from the catalog:

Embed code copy menu from catalog

A special variant of embed code that helps video appear in AI assistant search results (ChatGPT, Perplexity, etc.). LLM-friendly code includes the transcript directly in HTML — the player looks normal to users, while AI models can index the video text.

Requirement: The video must have a transcript — manually uploaded or auto-generated. Without it, the LLM-friendly option is unavailable. Creating transcripts is described in the Working with Files: Subtitles, Chapters, etc. article.

How to get the code: In the Embed window, if a transcript is available, select LLM-friendly code or AI code, then adaptive or fixed format. The code size will be larger than usual due to the embedded transcript.

Code structure: Player (regular iframe) + hidden block with transcript. The hidden part uses display: none and the data-video-transcript="true" attribute — the user sees only the player, while AI indexes the text.

Performance impact: The page size will increase by the size of the transcript (usually 5–50 KB of text). Video loading speed does not change. For most cases this is imperceptible.

Limitations: Only inline embedding works — adaptive and fixed code. Popover and plain iframe are not supported. If you need popover, use regular embed code. Best indexing is with ChatGPT, Perplexity, and others.

If the page has many videos with long transcripts, see the Load Optimization section. For embedding problems — Troubleshooting at the end of the article.

Embed the code into the HTML code of the page where you plan to place the Kinescope player.

All sites are different, so there is no single way to embed the player. The general rule: embed the code in a container or exactly where the player should appear on the page.

Adaptive code example:

By default the player adapts to the container width. If the player doesn’t fit by size, you can change dimensions via CSS styles of the div container or the iframe itself.

Important: The allowfullscreen attribute is a boolean attribute that allows fullscreen mode. It has no width and height parameters. Player dimensions are set separately:

Example of changing adaptive player dimensions via CSS:

Fixed code embedding is similar to adaptive. The only difference is that the code has no div tag setting adaptive characteristics.

The Kinescope player is now embedded on your page.

The seek and duration parameters allow playing only part of a video:

Full video (4 min 18 sec):

Video from 1 minute (skip first 60 seconds):

Video fragment (from 1 minute, duration 30 seconds):

For direct use of HLS manifests:

For iframe embedding:

The player_id parameter allows applying different design templates to the same video without creating content copies.

Copy the player template ID:

Copying player template ID from menu

Add the parameter to the video link:

Call To Action (CTA) allows showing calls to action during video playback. Useful for ads, subscriptions, registrations, or other goals.

How it works: When CTA activates, playback stops and an action screen is shown over the player. When the user clicks the action button, an event fires that can be handled programmatically.

Configuring CTA via player templates:

For more flexible CTA configuration (showing at specific playback moments, on pause, programmatic control), use IFrame Player API . See the full documentation for all CTA capabilities.

In addition to seek, duration, and player_id parameters, you can use additional URL parameters to configure player behavior. Parameters are added to the end of the URL in the src attribute of the iframe and start with a question mark (?). Use the & symbol for multiple parameters.

Supported parameters:

For parameters that accept true/false values, the values 1/0 are equivalent. For example: ?autoplay=true is equivalent to ?autoplay=1.

For parameters that accept the value true, the absence of a value is treated as true. For example: ?autoplay is equivalent to ?autoplay=true.

A direct link like https://kinescope.io/[VIDEO_ID] opens the video on a separate Kinescope player page. Supports seek, duration, player_id parameters.

Use: For publishing on social media, messengers, email newsletters.

Code for embedding video on your site. Supports seek and duration parameters via URL in the src attribute.

Use: For placing video on websites, blogs, LMS platforms.

Direct link to the HLS manifest (master.m3u8) for use in custom players or mobile applications.

Use: For integration with custom solutions, mobile applications, advanced playback scenarios.

To speed up page loading and save traffic, you can optimize player loading. This is especially useful if the page has multiple players or they are at the bottom of the page.

By default the player preloads video data. To disable preloading and load only the poster, use the preload=false parameter:

In this case the player will load (as will the poster), but video data will not load until playback starts. This saves traffic if the user doesn’t plan to watch the video right away.

If the iframe is outside the visible area (e.g., at the bottom of the page), you can defer its loading until the user scrolls to the player. Use the loading="lazy" attribute:

If you use your own poster or don’t want to show the player poster, use the no_poster=1 parameter:

This will reduce the amount of data loaded.

You can limit the maximum video quality when automatically determining the appropriate quality (ABR). This helps save traffic on mobile devices:

Available values: auto, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p.

If you encounter issues with the player, see the Troubleshooting section, which contains common situations and how to resolve them.

For basic embedding problems, check:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Kinescope player customization: templates, appearance, controls, behavior; settings menu including subtitle search, scale, default playback speed, and downloading video via direct link and transcriptions.

Integrating advertising tags into the Kinescope player via the adtagurl parameter to show ads during video playback.

**Examples:**

Example 1 (html):
```html
<!DOCTYPE html>
<html>
<body>
<h1>My Course</h1>
<p>First lesson</p>

<!-- Embed code start -->
<div style="position: relative; padding-top: 56.25%; width: 100%">
  <iframe src="https://kinescope.io/embed/202589431"
          allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
          frameborder="0"
          allowfullscreen
          style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;"></iframe></div>
<!-- Embed code end -->

</body>
</html>
```

Example 2 (jsx):
```jsx
<div style="position: relative; padding-top: 56.25%; width: 80%">
  <iframe src="https://kinescope.io/embed/202589431"
          allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
          frameborder="0"
          allowfullscreen
          style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;"></iframe>
</div>
```

Example 3 (html):
```html
<!DOCTYPE html>
<html>
<body>
<h1>My Course</h1>
<p>First lesson</p>

<!-- Embed code start -->
<iframe src="https://kinescope.io/embed/202589431"
        allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
        frameborder="0"
        allowfullscreen
        width="560"
        height="315">
</iframe>
<!-- Embed code end -->

</body>
</html>
```

Example 4 (sass):
```sass
https://kinescope.io/203613411/master.m3u8?seek=60&duration=30
```

---

## Player Customization - Kinescope Help center

**URL:** https://docs.kinescope.com/video-player/player-customization/

**Contents:**
- Player Customization
- Who this article is for
- Creating a new player template
  - From video settings
  - Via the template manager
- Editing templates
  - From video settings
  - Via the template manager
- Player behavior and appearance settings
- Basic behavior and appearance settings

Templates in Kinescope let you flexibly adapt the player’s appearance and functionality for different projects and tasks. Each template has a unique name and can be applied to individual videos or to an entire project. For example, you can create one template with visible controls for educational videos and another with a minimalist design and hidden progress bar for promo clips.

Player template configuration from video settings

Player template manager

The template manager shows the names of all player templates available in the workspace, as well as: the update date, author, and the number of files to which each template is applied. Clicking on that count shows all files in the catalog filtered by the selected player template.

To rename, duplicate, or delete a template, go to the menu (three dots next to the template).

The Kinescope player can be adapted for any task and project thanks to its wide range of settings. They are divided into two main categories:

Changes in settings are displayed in the preview area in real time. If you select the Monitor or Phone display mode, you can see how the finished template will look. It is very important not to forget to save settings, otherwise they will not be applied.

Player settings interface with preview

Player basic settings interface:

Player basic settings interface

Set a unique name for the template to make it easier to find, use for other videos, or edit via the template manager in the workspace.

Your brand’s corporate color can influence conversion. The color changes the large Play/Pause button, the progress bar, and the player control panel. The shade can be selected via a palette or by entering RGB or HEX code.

Integrate the player into your site’s general style: in template settings you can round the player window corners from 0 to 24px.

Add a logo that will be displayed in the lower right corner of the player. Usually a 150×150 px image in PNG format is sufficient. You can also add a hover tooltip or a link that opens on click.

Example player with clickable logo:

Allows video to play automatically when the page loads.

Example player with autoplay:

Player settings for background playback:

Mode for viewing panoramic, spherical video.

This setting stretches the video to the player’s borders to remove black bars at the edges. Especially useful for non-standard video resolutions.

Set the volume level when starting video from 0% to 100%, so the sound level is immediately comfortable for viewers.

Default video quality

Select the video stream quality that will be used when starting video. Available options:

Default playback speed

Set the playback speed at which video starts for all viewers. Available range: 0.25× to 2×. By default, speed is normal — 1×.

Default playback speed setting

If Playback speed is enabled in the player’s advanced settings, the viewer can change speed while watching.

Behavior at video end

Choose what happens after the video ends. Four scenarios are available:

Example call to action at the end of a video

Allows viewers to download video delivered via a direct link. Downloading is disabled by default. When enabled, a button appears below the player. It opens a window with two tabs:

Downloading video and transcriptions from the player

Player element display settings before playback starts:

Player element display settings before playback

The video title and subtitle will be displayed in the upper left corner of the player before launch if they are specified in the video settings on the Basic tab. These elements are hidden by default.

Example title and subtitle display in the player:

Example title and subtitle display in the player

By default the Play/Pause button is displayed in the center of the player before playback starts, but it can be hidden with this setting.

Example player with play button:

Example player with play button

By default it is hidden, making the player design minimalist. If preloading is enabled in the player’s advanced settings , the player control panel will be displayed before the clip starts.

Example control panel display before launch:

Example control panel display before launch

Player element display settings during playback:

Player element display settings during playback

Player playback settings allow customizing the display of titles, progress bar, and control panel.

This option allows hiding the progress bar during video playback. This can be useful for promo videos where it’s important to hold the user’s attention from start to finish. The progress bar is enabled by default.

Example player without progress bar:

Example player without progress bar

You can completely hide the control panel during playback, leaving only the progress bar if it’s not disabled. The control panel is shown by default.

Example player without controls (video only):

Example player without controls

Player advanced settings interface:

Player advanced settings interface

Launch video with subtitles

If subtitles are loaded for the video, they will be displayed automatically on launch. If the video has multiple subtitle tracks, the order of selection is determined by:

Subtitles are disabled by default.

If multiple players are placed on the page, this can affect performance. Autopause solves this problem: it automatically pauses the player when playback starts in another player on the same page.

This option controls the ability to cast the video stream to external monitors via Chromecast and Airplay protocols, as well as the display of corresponding buttons in the player. Casting support is enabled by default.

The settings menu (gear icon), through which the viewer can change speed, video quality, and other settings. Allows adding or removing items from the menu:

Subtitle search and scale in the player settings menu

Control panel elements

This set of settings allows selectively hiding or showing individual elements of the player control panel. All are shown by default.

Example control panel element settings:

Example control panel element settings

A static watermark is text or a logo that is permanently displayed on screen during video playback to designate authorship or indicate rights. Suitable for public videos, commercials, and widely distributed content.

If video preloading is enabled, the overall page load time may increase. The option is disabled by default.

Preloading and additional function settings:

Preloading and additional function settings

The Kinescope player supports keyboard shortcuts by default; the full list is available in the right-click menu on the player.

Example menu with keyboard shortcuts:

Example menu with keyboard shortcuts

The Kinescope player can remember player settings for each viewer (playback speed, video quality, and other preferences).

Viewer preference memory settings:

Viewer preference memory settings

The mouse click/tap control option is available in settings. When enabled, you can control playback not only via interface elements but also by clicking directly on the video. When disabled, the video can only be controlled via the control panel.

Right-clicking on video in the context menu shows the About Kinescope item, which redirects to the platform’s official site.

Example context menu and pseudo-fullscreen mode settings:

Player context menu and SEO optimization settings

Pseudo-fullscreen mode for iOS preserves the original Kinescope player controls when entering fullscreen mode. If you use dynamic watermarks, enable this option. See more in the Pseudo-Fullscreen Mode on iOS article.

SEO optimization adds metadata to the player code (title, description, poster, and others) that is indexed by search engines. The schema.org markup structure is used to improve the positions of public videos in search engine results.

SEO optimization does not work in the following cases:

In these cases, metadata is not added to the player code to protect content privacy.

Player SEO optimization settings

Enable data collection so the player can populate the analytics section with user behavior data.

Analytics and SEO optimization settings:

Player analytics and SEO optimization settings

If you still have questions, write to the support chat within the Kinescope interface — specialists will help!

Embedding — a way to place video on a site. Where to get the code (adaptive, fixed, LLM-friendly), parameters and optimization.

Integrating advertising tags into the Kinescope player via the adtagurl parameter to show ads during video playback.

---

## Video Player: Setup and Embedding - Kinescope Help center

**URL:** https://docs.kinescope.com/video-player/

**Contents:**
- Video Player: Setup and Embedding
- Who this section is for
- Where to start
  - If you’re new
  - If you’re a developer
- Key use cases
  - Embedding video on a site
  - Brand customization
  - Working with parameters
  - Calls to action and advertising

The Kinescope video player is a powerful tool for playing and embedding video on your sites. In this section you will find everything you need to configure, customize, and integrate the player.

Use embed code to add video to site pages. Two code types are supported:

Learn more about embedding →

Configure the player’s color, add a logo, change controls and player behavior. Create different templates for different content types.

Learn more about customization →

Use URL parameters to configure player behavior:

Learn more about parameters →

Improve page performance using:

Learn more about optimization →

Advanced configuration and integration options:

If you encounter issues with the player, see the Troubleshooting section, which contains common situations and how to resolve them:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Kinescope player customization: templates, appearance, controls, behavior; settings menu including subtitle search, scale, default playback speed, and downloading video via direct link and transcriptions.

Embedding — a way to place video on a site. Where to get the code (adaptive, fixed, LLM-friendly), parameters and optimization.

Integrating advertising tags into the Kinescope player via the adtagurl parameter to show ads during video playback.

---
