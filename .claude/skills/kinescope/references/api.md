# Kinescope - Api

**Pages:** 1

---

## Kinescope API · Reference

**URL:** https://docs.kinescope.com/api/

**Contents:**
- Kinescope API
- Authentication
- Errors
  - Handling errors
- v1
  - videos
    - posters
  - Posters list
  - Create poster by time
  - Get poster

Base URL: https://api.kinescope.io. Authentication — Bearer token (header Authorization: Bearer <ACCESS_TOKEN>).

Every request to the Kinescope API must carry a valid access token in the Authorization header. Tokens are issued in the dashboard (Settings → API) and are scoped to a single workspace.

Keep the token out of client-side code — anyone who sees it can act as the workspace owner until it is revoked. Create a separate token per integration so you can rotate or revoke any of them without disrupting the others.

The API uses conventional HTTP status codes to signal outcome, and a structured JSON body to describe the reason. Every error response has the same shape — code, short message, and optional detail with extra context.

Numeric codes returned in error.code. The first three digits of each code always match the HTTP status of the response.

Returns a list of posters. Results are paginated and can be filtered via query parameters.

Generates a poster image from a frame of the video at the specified timestamp. The poster is attached to the video and can be made active.

Retrieves the details of a single poster by its unique ID.

Marks the specified poster as the active one — it will be shown in the video player and in lists.

Permanently deletes the poster. This action cannot be undone.

Returns a list of subtitles. Results are paginated and can be filtered via query parameters.

Uploads a subtitle file (VTT or SRT) and attaches it to the video under the specified language.

Changes the order of subtitle tracks. Pass the full list of subtitle IDs in the desired order.

Retrieves the details of a single subtitle by its unique ID.

Updates the metadata of a subtitle track (language, description, ordering).

Duplicates a subtitle track. Useful for creating a variant based on an existing translation.

Permanently deletes the subtitle. This action cannot be undone.

Retrieves the details of a single annotation by its unique ID.

Returns a list of annotations. Results are paginated and can be filtered via query parameters.

Creates a new annotation. Returns the newly created object on success.

Updates the specified annotation. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the annotation. This action cannot be undone.

Returns a list of videos. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single video by its unique ID.

Updates the specified video. Only fields provided in the request body are changed; others are left unchanged.

This request update only passed fields.

Fields which can update: title, description, privacy_type, privacy_domains, additional_materials_enabled

Permanently deletes the video. This action cannot be undone.

Moves the video into a different project and/or folder. The video ID stays the same.

Replaces the chapter markers of the video with the provided list. Pass an empty array to clear all chapters.

Concatenates the source video with one or more other videos into a single new video. The original video is left unchanged and a new video is created with the combined content.

Creates a full copy of the video, optionally moving the copy into a different project or folder.

Trims the video to a given time range. The result is written back to the same video ID; the original bytes are replaced.

Create new trim/crop video.

Returns usage statistics for the given time range, grouped as requested. Useful for billing and capacity planning.

Our API returns resource consumption on a per project basis for better granularity, you can aggregate total on your side.

If necessary, you can specify project_id as a GET parameter to filter the results (edited)

Product types are: - CDN (bytes) - Encoding (min) - Storage (bytes)

Creates a new project. Returns the newly created object on success.

Returns a list of projects. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single project by its unique ID.

Permanently deletes the project. This action cannot be undone.

Updates the specified project. Only fields provided in the request body are changed; others are left unchanged.

Creates a new folder. Returns the newly created object on success.

Returns a list of folders. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single folder by its unique ID.

Updates the specified folder. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the folder. This action cannot be undone.

Returns high-level playback statistics — views, unique viewers, watch time — for the given period.

Returns a custom analytics slice. Specify the fields to return, grouping dimensions, and ordering.

Uploads a file to be attached to a video as additional material (e.g. a PDF handout or source files).

Returns a short-lived signed URL for downloading the material.

Updates the specified additional material. Only fields provided in the request body are changed; others are left unchanged.

Changes the display order of the additional materials attached to a video.

Permanently deletes the additional material. This action cannot be undone.

Returns the list of IANA timezones accepted by the API (for scheduling, analytics, etc.).

Creates a new access token for the workspace. Store the returned value — it is shown once.

Creates an upload-only access token scoped to a single project.

Returns a list of access tokens. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single access token by its unique ID.

Permanently deletes the access token. This action cannot be undone.

Returns the raw avatar image bytes.

Uploads an avatar image for the current workspace or user. Replaces any existing avatar.

Removes the avatar image. The default avatar is used afterwards.

Returns the raw avatar image bytes.

Returns a list of players. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single player by its unique ID.

Creates a new player. Returns the newly created object on success.

Updates the specified player. Only fields provided in the request body are changed; others are left unchanged.

Uploads a logo image that is shown on top of videos played with this player.

Removes the logo from this player.

Returns a list of file requests. Results are paginated and can be filtered via query parameters.

Retrieves the details of a single file request by its unique ID.

Creates a new file request. Returns the newly created object on success.

Updates the specified file request. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the file request. This action cannot be undone.

Returns the DRM auth configuration (URL, headers) currently used for license requests.

Updates the DRM license auth configuration.

Removes the DRM license auth configuration. DRM must be reconfigured before use.

Returns the DRM auth configuration (URL, headers) currently used for license requests.

Updates the DRM license auth configuration.

Removes the DRM license auth configuration. DRM must be reconfigured before use.

Returns a list of privacy domains. Results are paginated and can be filtered via query parameters.

Creates a new privacy domain. Returns the newly created object on success.

Updates the specified privacy domain. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the privacy domain. This action cannot be undone.

Returns a list of tags. Results are paginated and can be filtered via query parameters.

Creates a new tag. Returns the newly created object on success.

Updates the specified tag. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the tag. This action cannot be undone.

Returns the items currently in the playlist, in order.

List medias in playlist

Appends one or more videos to the playlist. If replace is true, the existing contents are cleared first.

Removes the specified items from the playlist.

Changes the position of an item within the playlist.

Retrieves the details of a single playlist by its unique ID.

Returns a list of playlists. Results are paginated and can be filtered via query parameters.

Creates a new playlist. Returns the newly created object on success.

Updates the specified playlist. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the playlist. This action cannot be undone.

Returns a list of moderators. Results are paginated and can be filtered via query parameters.

Creates a new moderator. Returns the newly created object on success.

Retrieves the details of a single moderator by its unique ID.

Updates the specified moderator. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the moderator. This action cannot be undone.

https://kinescope.notion.site/886ae0bc2ac14a149e71cf0ffec3881d?pvs=4

Returns a list of webhooks. Results are paginated and can be filtered via query parameters.

Subscribes to one or more event types. The configured endpoint will receive signed POST requests when those events fire.

Updates the webhook (URL, HTTP Basic credentials, subscribed events).

Permanently deletes the webhook. This action cannot be undone.

Creates a new CDN zone. Returns the newly created object on success.

Returns a list of CDN zones. Results are paginated and can be filtered via query parameters.

Updates the specified CDN zone. Only fields provided in the request body are changed; others are left unchanged.

Permanently deletes the CDN zone. This action cannot be undone.

Returns the participants of a Speak room.

Retrieves a participant by ID.

Adds a participant to a Speak room, optionally with a specific role.

Updates a participant — typically to change their role or display name.

Removes a participant from the Speak room.

Returns all Speak rooms in the workspace.

Retrieves a single Speak room by ID.

Creates a new Speak room. You can pre-create participants or add them later.

Updates properties of a Speak room.

Permanently deletes the Speak room. All participants lose access.

Uploads a new video. Multipart-based; the server returns the video object once the upload completes.

https://kinescope.notion.site/abe1183fe61b4e00a4f8c358bd27413d

Adds an RTMP restream target to the event — the live stream will be mirrored there.

Updates a restream target (URL, stream key, enabled flag).

Retrieves the details of a single restream by its unique ID.

Returns a list of restreams. Results are paginated and can be filtered via query parameters.

Permanently deletes the restream. This action cannot be undone.

Creates a new live event. The event is in draft state until scheduled and enabled.

Updates properties of a live event (title, description, scheduled time, restreams, etc.).

Retrieves the details of a single live event by its unique ID.

Returns a list of live events. Results are paginated and can be filtered via query parameters.

Returns recordings produced by the event, ordered by creation time.

Enables the event so that streams can be ingested and played back.

Marks the event as completed. Ingest endpoints stop accepting streams.

Schedules a new stream within the event. Returns the ingest URL and stream key.

Updates the scheduling of an upcoming stream (start time, expected duration).

Permanently deletes the live event. This action cannot be undone.

Moves the event into a different project or folder.

Uploads a custom poster image for a live event.

Returns quality-of-service statistics for the event (bitrate, dropped frames, latency).

Returns the chat log of the event in the requested format — JSON, CSV, or plain text.

Uploads a custom poster image for a live event.

**Examples:**

Example 1 (bash):
```bash
curl -H 'Authorization: Bearer <ACCESS_TOKEN>' \  https://api.kinescope.io/v1/videos
```

Example 2 (json):
```json
{  "error": {    "code": 400301,    "message": "invalid uuid format",    "detail": "see https://en.wikipedia.org/wiki/Universally_unique_identifier"  }}
```

Example 3 (json):
```json
{  "meta": {    "pagination": {      "page": 1,      "per_page": 10,      "total": 1    },    "order": {      "created_at": "desc"    }  },  "data": [    {      "id": "<UUID>",      "type": "image",      "from_time": 0,      "status": "done",      "active": true,      "to_time": 0,      "original": "https://kinescopecdn.net/<UUID>/posters/<UUID>/<UUID>.jpg",      "md": "https://kinescopecdn.net/<UUID>/posters/<UUID>/md/<UUID>.jpg",      "sm": "https://kinescopecdn.net/<UUID>/posters/<UUID>/sm/<UUID>.jpg",      "xs": "https://kinescopecdn.net/<UUID>/posters/<UUID>/xs/<UUID>.jpg"    }  ]}
```

Example 4 (bash):
```bash
curl -X GET \  '{{baseHost}}/v1/videos/:video_id/posters' \  -H 'Authorization: Bearer <ACCESS_TOKEN>'
```

---
