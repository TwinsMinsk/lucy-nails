# Kinescope - Developer-Guides

**Pages:** 12

---

## Authorization Backend: Video Access Control by Your System's Rules - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/authorization-backend/

**Contents:**
- Authorization Backend: Video Access Control by Your System's Rules
- Who this article is for
- When you need an authorization backend
- How access checking works (4 steps)
- Setup: step 1 — passing a user identifier
- Setup: step 2 — connecting your backend
- What arrives at your backend
- What to return in response
- How to check access (minimal scheme)
- Example: access only to a purchased course

Kinescope lets you control video access through an external authorization backend. This means you decide who can watch a specific video — based on your system’s rules (courses, subscriptions, roles, etc.).

Here are typical situations where this is useful:

If at least one of these scenarios applies to you — read on. Below is how to set up access checking in two steps.

Now let’s walk through how to set this up.

When embedding the player on a website, pass the authorization token via the drmauthtoken parameter in the URL:

You can use any string as a token: user_id, a JWT token, or another identifier your backend can verify.

Recommendation (security): For production, we recommend using a signed JWT in drmauthtoken. This protects against token substitution on the client. On the backend, validate the JWT signature and extract the user_id.

For developers: When validating a JWT, check the standard fields: exp (expiration), aud (audience), iss (issuer) — this improves security.

For Kinescope to be able to call your backend to check access, add your endpoint’s URL to the project or workspace settings via the Kinescope API.

Important: The API token in the Authorization: Bearer header must be in UUID format. You can get a token from the Kinescope Dashboard in Settings → API tokens. Learn more about authorization and error handling in the general API guidelines .

DRM can be configured at two levels:

Setting up the authorization backend URL via API:

For the entire workspace:

For a specific project:

Checking current settings:

Important: Kinescope sends an HTTP request with JSON to your URL (see example below). In response, simply return 200 (allow) or 403 (deny).

When a user tries to watch a video, Kinescope sends JSON with context to your authorization URL:

Your backend must return one of these HTTP codes:

For developers: If your backend is temporarily unavailable (5xx), Kinescope won’t be able to check access. We recommend setting up monitoring and quick service recovery.

Here’s what you need to do in your authorization handler:

Briefly in pseudocode:

Say your site has courses and a user bought only one of them. How do you check access to a video in that course?

Step 1: Map videos to courses in your system (e.g., a course_videos table with course_id and video_id fields).

Step 2: In your authorization handler:

Here’s what happens when a user opens a page with the player:

Done! Now you can control video access using any rules from your system.

After setting up the authorization backend, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (jsx):
```jsx
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?drmauthtoken=${user_id}"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

Example 2 (bash):
```bash
curl -X PUT "https://api.kinescope.io/v1/drm/auth" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/drm/authorize",
    "username": "drm_user",
    "password": "drm_password",
    "strict": false
}'
```

Example 3 (bash):
```bash
curl -X PUT "https://api.kinescope.io/v1/drm/auth/${PROJECT_ID}" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/drm/authorize",
    "username": "drm_user",
    "password": "drm_password",
    "strict": false
}'
```

Example 4 (bash):
```bash
# For workspace
curl -X GET "https://api.kinescope.io/v1/drm/auth" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"

# For project
curl -X GET "https://api.kinescope.io/v1/drm/auth/${PROJECT_ID}" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"
```

---

## Developer Guides - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/

**Contents:**
- Developer Guides
- Who this section is for
- Where to start
  - If you’re new to the Kinescope API
  - If you’re integrating the player
  - If you need authorization
- Key sections
  - API and content management
  - Player integration
  - Authorization and security

Kinescope provides API and SDK for integrating and automating video operations. You can upload files, manage video, configure access, integrate the player, and receive notifications via webhooks.

Use the API to automatically upload video from your system. Simple upload, Tus upload for large files, and URL upload are all supported.

Integrate Kinescope into LMS, CRM, or other platforms. Use the API for video management and IFrame Player API for player embedding.

Set up an authorization backend to control video access based on your system’s rules (courses, subscriptions, roles).

Connect webhooks to receive notifications about events: video upload, processing completion, views, and more.

After exploring the API, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

IFrame Player API allows programmatic player control via JavaScript: start and stop playback, manage volume, subscribe to events, and much more.

Kinescope Player SDK: source code, usage examples, and documentation for integrating the player into mobile and web applications.

Set up an external Kinescope authorization backend: grant video access by courses, subscriptions, and roles. JSON request example and 200/403 response logic.

Set up JWT authentication for stream chat: automatic user authorization, integration with your system, secure key management.

Kinescope webhooks: notifications about video and stream events. Event types, request examples, and error handling for process automation.

Setting up pseudo-fullscreen mode for the Kinescope player on iOS: preserving player controls and working correctly with dynamic watermarks.

Full Kinescope player documentation: embedding via iframe, IFrame API, web components, and advanced player features.

Integrating the Tus protocol with Kinescope for uploading large files: interaction diagram, backend implementation examples in Go, and frontend in JavaScript.

---

## File Upload via API - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/file-upload-via-api/

**Contents:**
- File Upload via API
- Who this article is for
- When you need API upload
- Upload methods
- Preparation: getting the project or folder ID
- Method 1: Creating an upload link
  - Request parameters
- Uploading a file using the received link
- Method 2: Single-request video upload
- Method 3: URL video upload

Kinescope lets you upload video via API. This lets you send files directly to projects and folders, control access to upload links, and keep your API token hidden from users of client applications.

API upload is useful if:

Kinescope supports three upload methods:

For large files: We recommend using the Tus protocol for uploading large files in chunks. See the implementation example here .

Before uploading a video, you need to select a project or folder for the file. The project or folder ID can be obtained via API:

Before you start: If this is your first time using the Kinescope API, we recommend reviewing the general API guidelines — they cover authorization, token format (UUID), pagination, and error handling.

Get the list of projects:

The response will contain a list of projects with their IDs. Use the id from the response to get the list of folders in a specific project.

Pagination and sorting: Project and folder lists support pagination (page, per_page) and sorting (order). See more in the general API guidelines .

Get the list of folders in a project:

Replace ${PROJECT_ID} with the project ID from the previous request.

The response will contain a list of folders with their IDs. The project or folder ID can be used in the parent_id parameter when uploading video.

Video about setting up and working with projects:

Video about setting up and working with folders:

This method is convenient when you need to enable uploading directly through a client application. You get a link that can be passed to the client for uploading the file.

What next? Use the endpoint from the response to upload the file (see “Uploading a file using the received link” below).

Parameters for type video:

Parameters for type attachment:

After getting the link (endpoint), upload the file via a POST request. The same link can be used to upload large files in chunks via the Tus protocol.

In this case, metadata is passed in the request headers and the video file in the body. This is suitable for small files or when you need to upload a file and immediately specify metadata.

You can use a direct link to a video file or a YouTube URL (e.g., https://www.youtube.com/watch?v=UTgSnM3mA-4 or https://youtu.be/UTgSnM3mA-4). Kinescope will download the file from the provided link itself.

After uploading a video, you can get direct links to posters (preview images). Available sizes: xs, sm, md, lg.

If you need to upload many videos from a CSV file, you can use a simple bash script with curl. This is simpler than writing a full application.

Important: The CSV file must have columns named url and title.

To upload one video by URL, use this curl request:

Here is a simple script that reads CSV and uploads all videos:

For developers: If you need more complex logic (error handling, parallel uploads, mapping storage), use Python, Node.js, or another language. But for simple cases, a bash script with curl is the quickest option.

Done! You can now upload video via the Kinescope API using any convenient method.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

IFrame Player API allows programmatic player control via JavaScript: start and stop playback, manage volume, subscribe to events, and much more.

**Examples:**

Example 1 (bash):
```bash
curl --location 'https://api.kinescope.io/v1/projects' \
--header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}'
```

Example 2 (bash):
```bash
curl --location 'https://api.kinescope.io/v1/projects/${PROJECT_ID}/folders' \
--header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}'
```

Example 3 (bash):
```bash
curl --location --request POST 'https://uploader.kinescope.io/v2/init' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}' \
--data-raw '{
    "filesize": 10485760,
    "type": "video",
    "title": "My Video",
    "parent_id": "e51e55a1-7615-493e-9055-10ac9cc44ccd",
    "filename": "video.mp4",
    "description": "Video description",
    "client_ip": "11.22.33.44"
}'
```

Example 4 (json):
```json
{
  "data": {
    "id": "7127f2d7-0e96-40d0-9a03-2e987c096466",
    "endpoint": "https://eu-ams-uploader-1.kinescope.io/v2/upload/0966958f-638b-4aab-bf4a-7f9860a57a93"
  }
}
```

---

## General API Guidelines - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/api-general-rules/

**Contents:**
- General API Guidelines
- Who this article is for
- Basic information
  - Base URL
  - API versions
- Authorization
  - Token format
  - Workspace and tokens
- Response format
  - Successful response

This page describes the general rules for working with the Kinescope API that apply to all endpoints. If you’re new to the API, start here.

All API requests are made to:

The Kinescope API uses versioning via URL prefixes:

For authorization in the public API, use the Authorization header with the Bearer type:

Important: The API token must be in UUID format (e.g., e51e55a1-7615-493e-9055-10ac9cc44ccd). You can get a token from the Kinescope Dashboard in Settings → API tokens.

Each API token is tied to a specific workspace. When making a request, the workspace is determined automatically from the token — you don’t need to pass it separately.

All endpoints require the Authorization: Bearer ... header.

All successful responses are returned in JSON format with a wrapper:

Lists are returned with pagination and sorting metadata:

All API responses include the X-Request-ID header with a unique request identifier. Use it when contacting support:

Use pagination parameters to retrieve lists:

Use the order parameter to sort results:

If a field is specified without a direction, asc is used by default.

Important: Not all fields support sorting. If an invalid field is specified, the API will return an error with code 400216 (NOT_ALLOWED_ORDER_FIELD).

The from and to parameters support two formats:

Both parameters are required for analytics endpoints.

All errors are returned in a consistent format:

For validation errors, the response also includes an invalid_params array:

Some endpoints support exporting data in CSV format via a .csv suffix in the URL:

Important: CSV format is not supported for all endpoints. Check the specific endpoint’s documentation or try adding .csv to the URL — if the format is not supported, JSON will be returned.

If limits are exceeded, the API will return 429 Too Many Requests.

Now that you know the general API rules, you can proceed to specific sections:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

IFrame Player API allows programmatic player control via JavaScript: start and stop playback, manage volume, subscribe to events, and much more.

**Examples:**

Example 1 (yaml):
```yaml
https://api.kinescope.io
```

Example 2 (yaml):
```yaml
Authorization: Bearer YOUR_API_TOKEN
```

Example 3 (json):
```json
{
  "data": {
    "id": "video-uuid",
    "title": "My Video",
    "status": "done"
  }
}
```

Example 4 (json):
```json
{
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total": 156
    },
    "order": {
      "created_at": "desc"
    }
  },
  "data": [
    {"id": "video-1", "title": "First Video"},
    {"id": "video-2", "title": "Second Video"}
  ]
}
```

---

## IFrame Player API - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/iframe-player-api/

**Contents:**
- IFrame Player API
- Who this article is for
- Why use IFrame Player API?
- What IFrame Player API offers
  - Control and events
  - Custom metrics and data sending
  - Parameters and scenarios
- Typical use cases
  - Learning Management Systems (LMS)
  - Interactive applications

IFrame Player API allows programmatic player control via JavaScript: start and stop playback, manage volume, subscribe to events, and much more.

With IFrame Player API you can:

IFrame Player API helps connect the player to your application logic: control playback and subscribe to events.

IFrame Player API is especially useful for educational platforms where many factors matter:

Here’s an example of building an analytics system that collects video view data and enriches it with context:

This example shows how to:

IFrame Player API makes it easy to integrate the player with your application’s internal logic:

To use IFrame Player API, include the script on the page and declare the onKinescopeIframeAPIReady function, which will be called automatically after the API loads.

Use the create method of the playerFactory object to create a player:

After creating the player you receive a player object with methods for controlling playback.

The player fires events you can subscribe to for tracking state changes.

Each event contains a data object:

IFrame Player API supports creating and managing playlists of multiple videos.

Call To Action (CTA) allows you to show calls to action during video playback. Useful for ads, subscriptions, registrations, or other goals.

How it works: When CTA activates, playback stops and an action screen is shown over the player. When the user clicks the action button, an event fires that you can handle programmatically.

CTA can be configured to show:

Use the playlist parameter when creating the player. See the full documentation for all API capabilities.

CTA configuration example:

To close the CTA screen programmatically, call the closeCTA() method on the player object:

When the user clicks the CTA button, the CallAction event fires. Subscribe to track interactions:

See the full IFrame Player Factory documentation for all creation parameters, and the events documentation for player events.

A library with TypeScript types is available:

See more about the library and types on GitHub .

For complete information about all API methods, events, and parameters, see the full IFrame Player API documentation .

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (javascript):
```javascript
// Analytics system for an educational platform
class LearningAnalytics {
  constructor(player, context) {
    this.player = player;
    this.context = {
      userId: context.userId,
      courseId: context.courseId,
      lessonId: context.lessonId,
      device: this.getDeviceInfo(),
      browser: this.getBrowserInfo(),
      timestamp: new Date().toISOString()
    };
    this.events = [];
    this.setupEventListeners();
  }

  setupEventListeners() {
    const player = this.player;

    // Track playback start
    player.on(player.Events.Play, () => {
      this.trackEvent('play', {
        currentTime: null, // will get on next TimeUpdate
        playbackRate: null
      });
    });

    // Track pause
    player.on(player.Events.Pause, async () => {
      const currentTime = await player.getCurrentTime();
      const duration = await player.getDuration();
      const percent = (currentTime / duration) * 100;

      this.trackEvent('pause', {
        currentTime,
        percent,
        reason: this.detectPauseReason() // e.g., "user_action", "network_issue"
      });
    });

    // Track view progress
    let lastTrackedPercent = 0;
    player.on(player.Events.TimeUpdate, async (event) => {
      const percent = event.data.percent;
      
      // Send event every 10% viewed
      if (percent - lastTrackedPercent >= 10) {
        lastTrackedPercent = percent;
        this.trackEvent('progress', {
          percent: Math.floor(percent),
          currentTime: event.data.currentTime
        });
      }
    });

    // Track playback end
    player.on(player.Events.Ended, async () => {
      const duration = await player.getDuration();
      this.trackEvent('completed', {
        totalDuration: duration,
        watchedDuration: duration // can be computed from pause events
      });
    });

    // Track seeking
    let lastSeekTime = 0;
    player.on(player.Events.Seeked, async () => {
      const currentTime = await player.getCurrentTime();
      if (Math.abs(currentTime - lastSeekTime) > 5) {
        this.trackEvent('seek', {
          from: lastSeekTime,
          to: currentTime,
          direction: currentTime > lastSeekTime ? 'forward' : 'backward'
        });
      }
      lastSeekTime = currentTime;
    });

    // Track quality changes
    player.on(player.Events.QualityChanged, (event) => {
      this.trackEvent('quality_changed', {
        quality: event.data.quality,
        reason: 'user_selection' // or 'auto_adaptation'
      });
    });

    // Track errors
    player.on(player.Events.Error, (event) => {
      this.trackEvent('error', {
        error: event.data.error,
        currentTime: null // can be fetched asynchronously
      });
    });
  }

  trackEvent(eventType, eventData) {
    const event = {
      type: eventType,
      data: eventData,
      context: this.context,
      timestamp: new Date().toISOString()
    };

    this.events.push(event);
    
    // Send event to your analytics system
    this.sendToAnalytics(event);
  }

  async sendToAnalytics(event) {
    try {
      await fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(event)
      });
    } catch (error) {
      console.error('Analytics send error:', error);
      // Can save to local storage for retry
    }
  }

  detectPauseReason() {
    // Logic to determine pause reason
    return 'user_action';
  }

  getDeviceInfo() {
    return {
      type: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'mobile' : 'desktop',
      screen: {
        width: window.screen.width,
        height: window.screen.height
      }
    };
  }

  getBrowserInfo() {
    return {
      name: navigator.userAgent.match(/(Chrome|Firefox|Safari|Edge)\/[\d.]+/)?.[1] || 'unknown',
      version: navigator.userAgent.match(/(Chrome|Firefox|Safari|Edge)\/([\d.]+)/)?.[2] || 'unknown'
    };
  }

  getSummary() {
    return {
      totalEvents: this.events.length,
      events: this.events,
      context: this.context
    };
  }
}

// Using the analytics system
function onKinescopeIframeAPIReady(playerFactory) {
  playerFactory
    .create('player', {
      url: 'https://kinescope.io/1111111',
      size: { width: '100%', height: 400 }
    })
    .then(function (player) {
      // Initialize analytics system with learning context
      const analytics = new LearningAnalytics(player, {
        userId: 'user_12345',
        courseId: 'course_67890',
        lessonId: 'lesson_11111',
      });

      // Example: send summary on page close
      window.addEventListener('beforeunload', () => {
        const summary = analytics.getSummary();
        navigator.sendBeacon('/api/analytics/track', JSON.stringify({
          type: 'session_end',
          summary: summary
        }));
      });
    });
}
```

Example 2 (javascript):
```javascript
function onKinescopeIframeAPIReady(playerFactory) {
  checkUserAccess()
    .then(hasAccess => {
      if (!hasAccess) {
        showAccessDeniedMessage();
        return;
      }

      return playerFactory.create('player', {
        url: 'https://kinescope.io/1111111',
        size: { width: '100%', height: 400 }
      });
    })
    .then(function (player) {
      if (!player) return;
      setupPlayerLogic(player);
    });
}

async function checkUserAccess() {
  const response = await fetch('/api/check-access');
  const data = await response.json();
  return data.hasAccess;
}

function setupPlayerLogic(player) {
  player.on(player.Events.Ended, async () => {
    await updateUserProgress();
    await unlockNextLesson();
    showNotification('Lesson complete!');
  });
}
```

Example 3 (javascript):
```javascript
// Integration with React/Vue/Angular application state
function createPlayerWithState(playerFactory, appState) {
  return playerFactory.create('player', {
    url: appState.currentVideo.url,
    behavior: {
      autoPlay: appState.settings.autoPlay,
      muted: appState.settings.muted
    }
  }).then(function (player) {
    player.on(player.Events.Pause, () => {
      appState.setPlayerState('paused');
    });

    player.on(player.Events.Playing, () => {
      appState.setPlayerState('playing');
    });

    appState.on('videoChanged', (newVideo) => {
      player.switchTo(newVideo.id);
    });

    return player;
  });
}
```

Example 4 (html):
```html
<!doctype html>
<html>
  <body>
    <!-- Player container -->
    <div id="player"></div>

    <script>
      // Load the IFrame Player API script
      var tag = document.createElement('script');
      tag.src = 'https://player.kinescope.io/latest/iframe.player.js';
      var firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

      // This function is called automatically after the API loads
      function onKinescopeIframeAPIReady(playerFactory) {
        playerFactory
          .create('player', {
            url: 'https://kinescope.io/1111111',
            size: { width: '100%', height: 400 },
          })
          .then(function (player) {
            console.log('Player created:', player);
          });
      }
    </script>
  </body>
</html>
```

---

## IFrame: Pseudo-Fullscreen on iOS - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/iframe-pseudo-fullscreen-on-ios/

**Contents:**
- IFrame: Pseudo-Fullscreen on iOS
- Who this article is for
- When you need pseudo-fullscreen mode on iOS
- How the script works (3 steps)
- Setup: step 1 — adding the script to the page
- Setup: step 2 — the script code
- How it works (in detail)
  - The KINESCOPE_PLAYER_FULLSCREEN_CHANGE event
  - iframe style management
  - Security

On iOS devices, when entering fullscreen mode the browser uses the native fullscreen API, which can conflict with Kinescope player controls. This script solves the problem: it preserves the original controls and works correctly with dynamic watermarks.

Now let’s go through how to set this up.

Place the script on the page where the Kinescope player is embedded, before the closing </body> tag or in the <head> section. The script will automatically handle all Kinescope player iframes on the page.

Example placement in HTML:

Here is the ready-to-use code for your page:

Here’s what happens when a user opens the page with the player:

The Kinescope player automatically sends this event via window.postMessage when:

When entering fullscreen:

When exiting fullscreen:

The script verifies that the event originates from the correct iframe (event.source matches iframe.contentWindow). This ensures security when working with multiple iframes on the page — each iframe is handled independently.

If you have one player on the page, the code above will work out of the box:

If there are multiple players on the page, the script will automatically handle each one independently:

If you use React, Vue, or another framework, place the script in the component that mounts after DOM loading:

Done! Now fullscreen mode will work correctly on iOS devices, and player controls will be preserved.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (html):
```html
<!DOCTYPE html>
<html>
<head>
  <title>Page with Kinescope Player</title>
</head>
<body>
  <!-- Your content -->
  <iframe src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz" width="640" height="360" frameborder="0"></iframe>
  
  <!-- Script for iOS fullscreen mode -->
  <script>
    // Script code here
  </script>
</body>
</html>
```

Example 2 (javascript):
```javascript
window.addEventListener('message', (event) => {
  if (event.data.type && event.data.type === 'KINESCOPE_PLAYER_FULLSCREEN_CHANGE') {
    const frames = document.getElementsByTagName('iframe');
    for (let i = 0; i < frames.length; i++) {
      if (frames[i].contentWindow === event.source) {
        if (event.data.value) {
          // Save original styles
          if (!frames[i].dataset.originalStyles) {
            frames[i].dataset.originalStyles = frames[i].style.cssText;
          }
          // Apply fullscreen styles
          frames[i].style.cssText = `
            background: #000;
            border: none;
            position: fixed;
            z-index: 9999;
            width: 100%;
            height: 100%;
            bottom: 0;
            right: 0;
            top: 0;
            left: 0;`;
        } else {
          // Restore old styles if they were saved
          if (frames[i].dataset.originalStyles) {
            frames[i].style.cssText = frames[i].dataset.originalStyles;
            delete frames[i].dataset.originalStyles;
          } else {
            frames[i].style.cssText = '';
          }
        }
        break;
      }
    }
  }
});
```

Example 3 (javascript):
```javascript
{
  type: 'KINESCOPE_PLAYER_FULLSCREEN_CHANGE',
  value: true  // or false
}
```

Example 4 (sql):
```sql
1. Receive event from iframe
2. Check: event.source === iframe.contentWindow
3. If matched — handle the event
4. If not matched — ignore
```

---

## JWT Authentication for Stream Chat - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/jwt-authentication-for-stream-chat/

**Contents:**
- JWT Authentication for Stream Chat
- Who this article is for
- When you need JWT chat authentication
- How JWT works in chat (5 steps)
- How to enable JWT authentication
- Setup: step 1 — generating keys
  - What is JWK?
  - JWK generation example
  - Saving the public key in Kinescope
  - Key management

JWT authentication lets you automatically authorize users in the stream chat and control access from your server. This is especially useful if you want to integrate the chat with your user management system.

Use JWT authentication if:

JWT authentication uses asymmetric cryptography (RSA) for secure transmission of user data:

Authentication is configured individually for each stream via the Kinescope API. Pass the chat_jwt_required: true parameter to enable it:

Important: The API token in the Authorization: Bearer header must be in UUID format. You can get a token from the Kinescope Dashboard in Settings → API tokens. See more about authorization in the general API guidelines .

After enabling, users will be automatically authorized when following a link with a token:

Now let’s go through how to set everything up from scratch.

JWT authentication uses asymmetric RSA cryptography, which requires a key pair:

JWK (JSON Web Key) is a standardized format for representing cryptographic keys (RFC 7517). It allows secure key exchange between systems:

Here’s what key pair generation looks like:

Example of a ready public JWK in JSON:

After generating the JWK, save the public part of the key in Kinescope via API. Make sure to pass all parameters: kty, e, use, kid, alg, n, and expires_at (key expiry date in ISO 8601 format):

Example successful response:

View all active keys:

Get data for a specific key:

Create a JWT token (JSON Web Token, RFC 7519) with required fields and sign it with your private key.

Important: event_id is required for chat embedding — chat can be embedded on a page without JWT authentication, but when using JWT, event_id is required to bind the token to a specific stream.

All standard JWT fields will be checked by the Kinescope system when validating the token.

Here’s what JWT generation and signing looks like:

For developers: In a real implementation, use libraries for JWT generation:

A JWT consists of three parts separated by dots: header.payload.signature

Signature: The signature is created by hashing base64(header) + "." + base64(payload) using the private key with the RS256 algorithm.

After generating the token, pass it in the chat URL:

Done! Your users can now be automatically authorized in the stream chat via JWT tokens.

It is recommended to regularly update keys to improve security. The rotation process:

If the private key was compromised (leak, suspected breach):

Problem: The user cannot authorize, the token is rejected.

Possible causes and solutions:

Invalid token signature

You can verify the token locally before sending it to the user. Here is an example verification function:

For developers: In a real implementation, use libraries for JWT verification:

Error “invalid key format”

Error “key size too small”

Problem: Chat is not displayed or does not authorize the user when embedded.

If the problem is not resolved, contact the support chat within the Kinescope interface with:

Done! You can now set up JWT authentication for stream chat and automatically authorize users.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (bash):
```bash
curl --location --request PUT 'https://api.kinescope.io/v2/live/events/{{event_id}}' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer your_api_token_here' \
--data '{
	"chat_jwt_required": true
}'
```

Example 2 (yaml):
```yaml
https://kinescope.io/chat/{{event_id}}?token={{jwt}}
```

Example 3 (go):
```go
package main

import (
    "crypto/rand"
    "crypto/rsa"
    "crypto/x509"
    "encoding/base64"
    "encoding/json"
    "time"
    
    "github.com/go-jose/go-jose/v3"
)

type JWK struct {
    Kty string `json:"kty"` // key type (RSA)
    Kid string `json:"kid"` // key identifier (unique)
    Use string `json:"use"` // purpose (sig for signing)
    Alg string `json:"alg"` // algorithm (RS256)
    N   string `json:"n"`   // RSA key modulus (base64url-encoded)
    E   string `json:"e"`   // exponent (usually "AQAB")
}

// Generate 2048-bit RSA key pair
func generateRSAKeyPair() (*rsa.PrivateKey, *JWK, error) {
    privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
    if err != nil {
        return nil, nil, err
    }
    
    // Generate unique Key ID (kid)
    kid := "key-" + time.Now().Format("2006-01-02")
    
    // Build public key in JWK format
    publicKeyJWK := &JWK{
        Kty: "RSA",
        Kid: kid,
        Use: "sig",   // purpose - signing
        Alg: "RS256", // algorithm - RSA with SHA-256
        N:   base64.RawURLEncoding.EncodeToString(privateKey.PublicKey.N.Bytes()),
        E:   base64.RawURLEncoding.EncodeToString([]byte{1, 0, 1}), // 65537 = AQAB
    }
    
    return privateKey, publicKeyJWK, nil
}

// Save private key in PEM format
func savePrivateKey(key *rsa.PrivateKey) ([]byte, error) {
    return x509.MarshalPKCS8PrivateKey(key)
}
```

Example 4 (json):
```json
{
  "kty": "RSA",
  "kid": "key-2024-12-25",
  "use": "sig",
  "alg": "RS256",
  "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbwE...",
  "e": "AQAB"
}
```

---

## Kinescope API - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/kinescope-api/

**Contents:**
- Kinescope API
- Who this article is for
- Full API documentation
- Quick start
- What’s next?
- Related articles
  - Table of contents

Kinescope API is a REST API for programmatic platform management. With the API you can automate work with projects, videos, streams, and settings without using the web interface.

The full Kinescope API documentation with request examples is available here .

In the documentation you will find:

To work with the API you will need:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

IFrame Player API allows programmatic player control via JavaScript: start and stop playback, manage volume, subscribe to events, and much more.

---

## Kinescope Player Docs & IFrame API - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/kinescope-player-docs-iframe-api/

**Contents:**
- Kinescope Player Docs & IFrame API
- Who this article is for
- What the documentation covers
- Basic guide
- What’s next?
- Related articles
  - Table of contents

Full technical documentation for the Kinescope player is available at a dedicated domain: docs.kinescope.io/player/latest/ .

In the full documentation you will find:

A basic player embedding guide is also available in the Video Player: Setup and Embedding section.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

---

## Kinescope Player SDK - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/kinescope-player-sdk/

**Contents:**
- Kinescope Player SDK
- Who this article is for
- SDK repository
- What’s next?
- Related articles
  - Table of contents

Kinescope Player SDK is a set of libraries for integrating the Kinescope player into your mobile and web applications. The SDK provides ready-made components and an API for controlling video playback.

The Kinescope Player SDK repository is available on GitHub .

In the repository you will find:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

---

## Tus Protocol Implementation Example - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/tus-protocol-implementation/

**Contents:**
- Tus Protocol Implementation Example
- When you need Tus
- How Tus upload works (4 steps)
- What to prepare
- Interaction diagram
- The /upload method contract
  - What the client sends → your backend
  - What your backend returns → client
- Example request to Kinescope /v2/init
- Backend implementation example

Tus is an open protocol for resumable file uploads. The protocol allows resuming uploads after a connection drop, uploading large files in chunks, and controlling the upload process.

Use Tus if you are uploading large files and want to:

For developers: Official protocol documentation: https://tus.io/protocols/resumable-upload.htmlLibraries for different languages: https://tus.io/implementations.html

Before starting, make sure you have:

Here is what the upload process looks like:

If you use tus-js-client, a convenient option is to accept standard Tus headers:

For developers: In the examples below, metadata is taken from the Upload-Metadata header and the size from Upload-Length. This is not the only option: these values can also be accepted in JSON if that is more convenient for your frontend.

There are two working options:

If you use Option A, make sure CORS allows the client to read the Location header (Access-Control-Expose-Headers: Location is required).

Your backend should send an upload initialization request:

In response, Kinescope will return 201 Created and an object containing data.endpoint — this is the Tus endpoint for uploading.

Here is a sample backend handler in Go:

Use the tus-js-client library to work with the Tus protocol in the browser.

JavaScript code example (upload.js):

Problem: CORS error in the browser and the Location header is not visible.

Solution: Check that your backend sets Access-Control-Expose-Headers: Location.

Problem: Kinescope returns an authorization error.

Solution: Check the token and access rights, make sure the token is not expired or revoked.

Problem: After a connection drop, the upload does not resume.

Solution: Enable findPreviousUploads()/resumeFromPreviousUpload() and do not change endpoint/uploadURL for the same file.

Problem: Constant network errors during upload.

Solution: Reduce chunkSize and configure retryDelays.

If you need help from technical support, attach:

Support channel: the support chat within the Kinescope interface.

Done! You can now set up large file uploads via the Tus protocol.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (perl):
```perl
sequenceDiagram
    participant Client as Client_Browser
    participant Backend as Backend_UserServer
    participant API as Kinescope_API
    participant TusEndpoint as Kinescope_TusEndpoint

    Note over Backend: "File does not pass through backend"
    Client->>Backend: "POST /upload (metadata,size)"
    Backend->>API: "POST /v2/init (Bearer TOKEN, parent_id, filename, filesize, type)"
    API-->>Backend: "201 Created (endpoint)"
    Backend-->>Client: "endpoint (Location/redirect or JSON)"

    Note over Client,TusEndpoint: "File is uploaded directly to Kinescope"
    Client->>TusEndpoint: "PATCH chunk_1 (file bytes)"
    TusEndpoint-->>Client: "204 No Content (Upload-Offset)"
    Client->>TusEndpoint: "PATCH chunk_2 (file bytes)"
    TusEndpoint-->>Client: "204 No Content (Upload-Offset)"
    Note over Client,TusEndpoint: "Repeats until upload is complete"
    Client->>TusEndpoint: "PATCH last_chunk (file bytes)"
    TusEndpoint-->>Client: "204 No Content (Upload complete)"
```

Example 2 (bash):
```bash
curl -X POST 'https://uploader.kinescope.io/v2/init' \
  -H 'Authorization: Bearer <KINESCOPE_API_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "parent_id": "<PROJECT_OR_FOLDER_ID>",
    "type": "video",
    "filename": "example.mp4",
    "title": "example.mp4",
    "filesize": 123456789
  }'
```

Example 3 (go):
```go
package main

import (
    "encoding/base64"
    "encoding/json"
    "fmt"
    "net/http"
    "strconv"
    "strings"
)

const (
    kinescopeAPIToken      = "11111111-1111-1111-1111-111111111111"
    kinescopeUploadInitURL = "https://uploader.kinescope.io/v2/init"
)

type KinescopeInitResponse struct {
    Data struct {
        ID       string `json:"id"`
        Endpoint string `json:"endpoint"`
    } `json:"data"`
}

// Handler for upload initialization request
func handleUploadInit(w http.ResponseWriter, r *http.Request) {
    origin := r.Header.Get("Origin")
    
    // Set CORS headers
    if origin != "" {
        w.Header().Set("Access-Control-Allow-Origin", origin)
        w.Header().Set("Access-Control-Allow-Credentials", "true")
        w.Header().Set("Access-Control-Allow-Headers", 
            "Origin, Content-Type, Tus-Resumable, Upload-Length, Upload-Metadata")
        w.Header().Set("Access-Control-Allow-Methods", 
            "POST, GET, HEAD, PATCH, DELETE, OPTIONS")
        w.Header().Set("Access-Control-Expose-Headers", "Location")
    }
    
    // Handle OPTIONS request
    if r.Method == "OPTIONS" {
        w.Header().Set("Access-Control-Max-Age", "86400")
        w.WriteHeader(http.StatusOK)
        return
    }
    
    // Parse metadata from Upload-Metadata header
    metadata := parseMetadataHeader(r.Header.Get("Upload-Metadata"))
    
    // Parse file size from Upload-Length header
    filesize, err := strconv.ParseInt(r.Header.Get("Upload-Length"), 10, 64)
    if err != nil || filesize <= 0 {
        http.Error(w, "bad header Upload-Length", http.StatusBadRequest)
        return
    }
    
    // Build request to Kinescope API
    requestBody := map[string]interface{}{
        "client_ip": r.RemoteAddr,
        "parent_id": "your project or folder ID here",
        "type":      "video",
        "title":     metadata["filename"],
        "filename":  metadata["filename"],
        "filesize":  filesize,
    }
    
    // Call Kinescope API to initialize upload
    body, _ := json.Marshal(requestBody)
    req, _ := http.NewRequest("POST", kinescopeUploadInitURL, strings.NewReader(string(body)))
    req.Header.Set("Authorization", "Bearer "+kinescopeAPIToken)
    req.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil || resp.StatusCode != http.StatusCreated {
        http.Error(w, fmt.Sprintf("kinescope api response status=%d", resp.StatusCode), 
            http.StatusBadRequest)
        return
    }
    defer resp.Body.Close()
    
    var result KinescopeInitResponse
    json.NewDecoder(resp.Body).Decode(&result)
    
    // Return redirect to Tus endpoint
    w.Header().Set("Location", result.Data.Endpoint)
    w.WriteHeader(http.StatusCreated)
}

// Parse Upload-Metadata header
func parseMetadataHeader(header string) map[string]string {
    meta := make(map[string]string)
    
    if header == "" {
        return meta
    }
    
    elements := strings.Split(header, ",")
    for _, element := range elements {
        parts := strings.Fields(strings.TrimSpace(element))
        if len(parts) != 2 {
            continue
        }
        
        decoded, err := base64.StdEncoding.DecodeString(parts[1])
        if err != nil {
            continue
        }
        meta[parts[0]] = string(decoded)
    }
    
    return meta
}
```

Example 4 (html):
```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>Demo Upload Tus</title>
  </head>
  <body>
    <input type="file" id="file-input">
  </body>
  <script src="https://cdn.jsdelivr.net/npm/tus-js-client@latest/dist/tus.js"></script>
  <script src="upload.js"></script>
</html>
```

---

## Webhook Types - Kinescope Help center

**URL:** https://docs.kinescope.com/developer-guides/webhook-types/

**Contents:**
- Webhook Types
- Who this article is for
- What problems webhooks solve
- How it works
- Video webhooks
  - media.update.status
- Stream webhooks
  - live.created
  - live.connected
  - live.disconnected

Kinescope supports outgoing webhooks — notifications about events that occur with your videos or streams. When an event occurs (e.g., a video is processed or a stream ends), Kinescope sends an HTTP request to the URL you specified.

Webhooks let you automate processes in your system:

Sent when the video status is updated. Used to track video processing, errors, or publication completion.

Example 1: Successful status update

Example 2: Processing error

Notification about the creation of a new stream event (via API or interface).

Streamer connected — RTMP stream started arriving at the server.

Streamer disconnected — RTMP stream stopped.

Stream ended. The response also includes video_id — the ID of the stream recording video (if recording was enabled).

Stream was cancelled.

Stream is available for viewing by clients.

Here is how to handle the media.update.status webhook and update the status in your database:

When a stream ends, you can automatically process the recording:

Here is an example of a universal handler that can process different webhook types:

Webhooks are configured via the Kinescope API. Specify the URL of your endpoint that will receive notifications.

Important: Your endpoint must return HTTP 200 in response to successful webhook handling. If Kinescope receives an error (4xx, 5xx), it may retry the request.

It is recommended to verify webhook authenticity:

Done! You can now set up webhooks and automate processes in your system.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Basic rules for working with the Kinescope API: authorization, token format, workspace, pagination, sorting, error handling, and special response formats.

Uploading video via the Kinescope API: three upload methods, creating upload links for clients, URL upload, and bulk import from CSV.

Full Kinescope REST API documentation: manage projects, videos, streams, and settings via the programmatic interface.

**Examples:**

Example 1 (json):
```json
{
  "event": "media.update.status",
  "data": {
    "id": "7127f2d7-0e96-40d0-9a03-2e987c096466",
    "status": "done"
  }
}
```

Example 2 (json):
```json
{
  "event": "media.update.status",
  "data": {
    "id": "12706830-0e96-40d0-9a03-2e987c096466",
    "status": "error",
    "message": "import error: code=610100, message=cannot download link: https://example.ru/test.mp4, http_code=404"
  }
}
```

Example 3 (json):
```json
{
  "event": "live.created",
  "data": {
    "event_id": "abc123-def456-ghi789"
  }
}
```

Example 4 (json):
```json
{
  "event": "live.connected",
  "data": {
    "event_id": "abc123-def456-ghi789"
  }
}
```

---
