# Kinescope - Integrations

**Pages:** 6

---

## Embedding on WordPress - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/embedding-on-wordpress/

**Contents:**
- Embedding on WordPress
- Who this article is for
- Installing the plugin
- Using the plugin
- What’s next?
- Related articles
  - Table of contents

The Kinescope plugin for WordPress lets you add a video player to pages and posts using a shortcode or widget. The plugin supports all Kinescope features, including content protection, player customization, and analytics.

Or download the plugin and upload it to the /wp-content/plugins/ directory.

After installing the plugin, you’ll be able to add video. This can be done in several ways: via an embed element or using the page editor.

If you use a page editor such as Elementor or Bricks, a Kinescope icon will be available there. Specify the video link.

After installing the plugin, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Setting up Single Sign-On (SSO) in Kinescope via Keycloak or AD FS: creating clients, configuring roles, and transformation rules for corporate integration.

Kinescope integration with Zoom: streaming via RTMP, automatic recording import, expanding your audience, and collecting view analytics.

Kinescope integration with Open edX via XBlock extension: installation, configuration, and adding protected video to educational platform courses.

---

## Integrations - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/

**Contents:**
- Integrations
- Who this section is for
- Where to start
  - If you use a website builder
  - If you use an LMS
  - If you’re a developer
- Available integrations
  - Educational platforms (LMS)
  - Website builders
  - Other platforms

Kinescope supports integrations with popular platforms: LMS, website builders, and other services. Ready-made scripts and detailed instructions will help you quickly connect video to your tools.

Integrate video into courses and lessons. Students can watch video directly in the platform interface, and you’ll get view analytics.

Embed video on a corporate site using builders or CMS. Video will automatically adapt to different devices.

Connect video to CRM and marketing tools. Track views and analyze the effectiveness of your video content.

After setting up an integration, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Setting up Single Sign-On (SSO) in Kinescope via Keycloak or AD FS: creating clients, configuring roles, and transformation rules for corporate integration.

Kinescope integration with Zoom: streaming via RTMP, automatic recording import, expanding your audience, and collecting view analytics.

Kinescope plugin for WordPress: installation, setup, and using shortcodes to add protected video players to site pages and posts.

Kinescope integration with Open edX via XBlock extension: installation, configuration, and adding protected video to educational platform courses.

Kinescope integration with Hugo: ready-made shortcode for embedding video and playlists in Hugo documentation and blogs with responsive support and lazy loading.

---

## Integration with Hugo - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/integration-with-hugo/

**Contents:**
- Integration with Hugo
- When you’ll need the Hugo integration
- How the shortcode works (4 steps)
- Setup: step 1 — install the shortcode
- Setup: step 2 — add CSS styles
- Using the shortcode
  - Basic video embedding
  - Embedding playlists
  - Fixed player size
  - Playback parameters

Hugo is a fast and modern static site generator written in Go. Kinescope provides a ready-made shortcode for conveniently embedding video and playlists in Hugo documentation and blogs.

Use the Hugo integration if:

If you use Hugo for documentation or a blog — read on. Below you’ll find how to set up the integration in a few minutes.

Now let’s walk through how to set it up.

The kinescope shortcode is already included in the Kinescope documentation theme. If you’re using your own theme or want to add it to an existing Hugo project:

Or in the project root (if you’re not using a theme):

Add CSS styles for correct display (optional, if they’re not in your theme):

The simplest approach — specify the full video URL:

Or use just the video ID:

Video embedding example:

For playlists, use the URL with the /pl/ prefix:

Or specify the type and ID:

Playlist embedding example:

By default, the player is responsive and adapts to the container width. For a fixed size, specify width and height:

The shortcode supports passing parameters via query string. For example, to play a video segment:

This example starts the video from the 60th second and plays only the next 30 seconds.

Example with parameters:

To apply a specific player template, use the player_id parameter:

For non-standard video formats, you can change the aspect ratio (default is 16:9, corresponding to padding-top: 56.25%):

The ratio value is specified as a percentage. For example:

Add video to a documentation article:

Embed video in blog posts:

Use playlists for sequential learning:

The shortcode automatically checks parameter correctness during site build:

Example error for incorrect usage:

All iframes automatically load with the loading="lazy" attribute, improving page performance.

The shortcode supports all parameters that can be passed in the player URL:

Simply add them as shortcode parameters:

The shortcode works with:

For the shortcode to work, enable the following in config.toml:

This allows Hugo to process the HTML code generated by the shortcode.

If you have questions about the Hugo integration or using the shortcode, contact the support chat within the Kinescope interface — specialists will help you set up video embedding in your documentation or blog.

Hugo documentation is available on the official website .

That’s it! You can now embed Kinescope videos and playlists in your Hugo documentation or blog.

After setting up the Hugo integration, we recommend:

If you have any questions, write to the support chat within the Kinescope interface — our specialists will help!

Setting up Single Sign-On (SSO) in Kinescope via Keycloak or AD FS: creating clients, configuring roles, and transformation rules for corporate integration.

Kinescope integration with Zoom: streaming via RTMP, automatic recording import, expanding your audience, and collecting view analytics.

Kinescope plugin for WordPress: installation, setup, and using shortcodes to add protected video players to site pages and posts.

**Examples:**

Example 1 (bash):
```bash
themes/your-theme/layouts/shortcodes/kinescope.html
```

Example 2 (bash):
```bash
layouts/shortcodes/kinescope.html
```

Example 3 (html):
```html
{{- /* 
  Shortcode for embedding Kinescope players (video and playlists)
*/ -}}

{{- $url := .Get "url" -}}
{{- $id := .Get "id" -}}
{{- $type := .Get "type" | default "" -}}
{{- $width := .Get "width" -}}
{{- $height := .Get "height" -}}
{{- $ratio := .Get "ratio" | default "56.25" -}}
{{- $allow := .Get "allow" | default "autoplay; fullscreen; picture-in-picture; encrypted-media; gyroscope; accelerometer; clipboard-write; screen-wake-lock;" -}}

{{- /* Validation: either url or id must be specified */ -}}
{{- if and (not $url) (not $id) -}}
  {{- errorf "kinescope shortcode: either 'url' or 'id' parameter is required" -}}
{{- end -}}

{{- /* Determine embed URL */ -}}
{{- $embedUrl := "" -}}
{{- if $url -}}
  {{- if strings.HasPrefix $url "https://kinescope.io/embed/" -}}
    {{- $embedUrl = $url -}}
  {{- else if strings.HasPrefix $url "https://kinescope.io/pl/" -}}
    {{- $embedUrl = strings.Replace $url "https://kinescope.io/pl/" "https://kinescope.io/embed/pl/" 1 -}}
  {{- else if strings.HasPrefix $url "https://kinescope.io/" -}}
    {{- $embedUrl = strings.Replace $url "https://kinescope.io/" "https://kinescope.io/embed/" 1 -}}
  {{- else -}}
    {{- errorf "kinescope shortcode: unsupported URL format: %s" $url -}}
  {{- end -}}
{{- else if $id -}}
  {{- if eq $type "pl" -}}
    {{- $embedUrl = printf "https://kinescope.io/embed/pl/%s" $id -}}
  {{- else -}}
    {{- $embedUrl = printf "https://kinescope.io/embed/%s" $id -}}
  {{- end -}}
{{- end -}}

{{- /* Build query parameters */ -}}
{{- $queryParams := slice -}}
{{- $serviceParams := slice "url" "id" "type" "width" "height" "ratio" "allow" "title" -}}
{{- range $key, $value := .Params -}}
  {{- if and (ne $key "_") (not (in $serviceParams $key)) -}}
    {{- $encodedValue := $value | urlquery -}}
    {{- $queryParams = $queryParams | append (printf "%s=%s" $key $encodedValue) -}}
  {{- end -}}
{{- end -}}

{{- if gt (len $queryParams) 0 -}}
  {{- $queryString := delimit $queryParams "&" -}}
  {{- $embedUrl = printf "%s?%s" $embedUrl $queryString -}}
{{- end -}}

{{- /* Determine mode: responsive or fixed */ -}}
{{- $isFixed := and $width $height -}}

{{- if $isFixed -}}
  <div class="kinescope-embed kinescope-embed-fixed">
    <iframe 
      src="{{ $embedUrl }}"
      allow="{{ $allow }}"
      frameborder="0"
      allowfullscreen
      width="{{ $width }}"
      height="{{ $height }}"
      loading="lazy">
    </iframe>
  </div>
{{- else -}}
  <div class="kinescope-embed kinescope-embed-responsive" style="position: relative; padding-top: {{ $ratio }}%; width: 100%;">
    <iframe 
      src="{{ $embedUrl }}"
      allow="{{ $allow }}"
      frameborder="0"
      allowfullscreen
      style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;"
      loading="lazy">
    </iframe>
  </div>
{{- end -}}
```

Example 4 (css):
```css
/* Kinescope embed styles */
.kinescope-embed {
    margin: 1.5em 0;
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--color-bg-tertiary);
}

.kinescope-embed-responsive {
    position: relative;
    width: 100%;
}

.kinescope-embed-responsive iframe {
    position: absolute;
    width: 100%;
    height: 100%;
    top: 0;
    left: 0;
    border: none;
}

.kinescope-embed-fixed {
    display: inline-block;
    max-width: 100%;
}

.kinescope-embed-fixed iframe {
    display: block;
    border: none;
    max-width: 100%;
    height: auto;
}
```

---

## Integration with Open edX - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/integration-with-open-edx/

**Contents:**
- Integration with Open edX
- Who this article is for
- What is Kinescope XBlock?
- Installing Kinescope XBlock
- Testing Kinescope XBlock
- How to add a video to an Open edX course via Kinescope XBlock
- What’s next?
- Related articles
  - Table of contents

Open edX is a free LMS with open-source code. Kinescope supports integration via the XBlock extension: it lets you embed protected video from Kinescope directly into Open edX courses, without external links or third-party solutions.

XBlock is an extension for Open edX that adds new functionality to the educational platform. Kinescope XBlock lets you embed video from Kinescope directly into Open edX courses, without external links or third-party solutions.

Kinescope XBlock is available in the OpenCraft GitHub repository and in the Open edX Marketplace catalog under Video Delivery.

To install, follow these steps:

Clone the repository into your Open edX environment:

git clone https://github.com/open-craft/xblock-kinescope.git

Install XBlock using pip:

Add XBlock to the LMS configuration:

In the lms.env.json file, add:

Restart the Open edX server: tutor local stop

After this, Kinescope XBlock will be available in Studio for adding to courses.

After installation, verify that the XBlock works in your Open edX environment:

Adding a video to a course on the platform takes just 10 steps. A short video below makes the process more visual.

Integration is ready! You can now add video to your courses using the ready-made XBlock components.

After setting up integration with Open edX, we recommend:

If you have any questions, write to the support chat within the Kinescope interface — our specialists will help!

Setting up Single Sign-On (SSO) in Kinescope via Keycloak or AD FS: creating clients, configuring roles, and transformation rules for corporate integration.

Kinescope integration with Zoom: streaming via RTMP, automatic recording import, expanding your audience, and collecting view analytics.

Kinescope plugin for WordPress: installation, setup, and using shortcodes to add protected video players to site pages and posts.

**Examples:**

Example 1 (json):
```json
"XBLOCK_SETTINGS": {
    "kinescope": {
        "enabled": true
    }
}
```

---

## Integration with Zoom - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/integration-with-zoom/

**Contents:**
- Integration with Zoom
- Who this article is for
- Zoom streaming
- What’s next?
- Automatic recording import from Zoom
- Related articles
  - Table of contents

Zoom is a tool for online meetings, webinars, and conferences. Combined with Kinescope, you can stream broadcasts via RTMP, expand your audience, and collect view analytics.

Using Zoom with Kinescope, you can:

If you plan to run a live stream via Kinescope, set up an RTMP stream. You’ll need: a stream key, the RTMP server URL, and the Kinescope stream page link that will receive the stream from Zoom.

Adding the Live Streaming app in Zoom

Adding a broadcast channel in Zoom

Selecting Custom for broadcast

Filling in broadcast parameters in Zoom

Stream window in Zoom

Starting the stream in Zoom

After setting up integration with Zoom, we recommend:

If you have any questions, write to the support chat within the Kinescope interface — our specialists will help!

The integration works with Zoom Pro subscriptions with access to cloud recordings. Setup takes a couple of minutes — just authorization is needed.

After setting up the Zoom integration and choosing a save location in Kinescope, all new videos from the Zoom cloud will be automatically uploaded to the service.

You can also import into Kinescope all videos that were uploaded to the Zoom cloud before the integration was set up.

Setting up Single Sign-On (SSO) in Kinescope via Keycloak or AD FS: creating clients, configuring roles, and transformation rules for corporate integration.

Kinescope plugin for WordPress: installation, setup, and using shortcodes to add protected video players to site pages and posts.

Kinescope integration with Open edX via XBlock extension: installation, configuration, and adding protected video to educational platform courses.

---

## SSO Login Setup - Kinescope Help center

**URL:** https://docs.kinescope.com/integrations/sso-login-setup/

**Contents:**
- SSO Login Setup
- Who this article is for
- Creating and configuring a client in Keycloak
- Setting up AD FS for Kinescope
  - Step 1: Creating an Application Group
  - Step 2: Configuring Server Application
  - Step 3: Configuring credentials
  - Step 4: Configuring Web API
  - Step 5: Configuring permissions (Client Permissions)
  - Step 6: Configuring permitted scopes

With Single Sign-On (SSO), a user can log in to multiple related services with a single username and password. For example, log in to a corporate portal and simultaneously get access to Kinescope. This simplifies access management and improves security.

Creating a client in Keycloak

Entering Client ID in Keycloak

Configuring the authentication flow in Keycloak

Configuring redirect URL in Keycloak

Selecting a client in Keycloak

Creating a role in Keycloak

Use the following role names for correct configuration:

Roles are listed in priority order. If multiple roles are passed, the user will be assigned the role with the lowest priority.

Learn more about Kinescope user roles and their capabilities in the article Managing team access rights .

Linking a role in Keycloak

Selecting an associated role in Keycloak

Users with the selected role in the system will now be created in Kinescope with the “kinescope-manager” role.

Client parameters in Keycloak

Client list in Keycloak

If you encounter an error during setup or need consultation — the support chat within the Kinescope interface.

Creating an Application Group in AD FS

Configuring Server Application in AD FS

Configuring credentials in AD FS

Important: Click the “Copy to clipboard” button to copy the secret. Save this secret in a secure place — you’ll need it to configure the integration.

Configuring Web API in AD FS

Configuring permissions in AD FS

Configuring permitted scopes in AD FS

Configuring Issuance Transform Rules in AD FS

Adding a rule for the manager role in AD FS

Application Groups list in AD FS after setup

After setting up SSO, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Kinescope integration with Zoom: streaming via RTMP, automatic recording import, expanding your audience, and collecting view analytics.

Kinescope plugin for WordPress: installation, setup, and using shortcodes to add protected video players to site pages and posts.

Kinescope integration with Open edX via XBlock extension: installation, configuration, and adding protected video to educational platform courses.

---
