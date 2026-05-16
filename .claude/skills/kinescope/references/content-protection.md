# Kinescope - Content-Protection

**Pages:** 4

---

## Content Protection - Kinescope Help center

**URL:** https://docs.kinescope.com/content-protection/

**Contents:**
- Content Protection
- Who this section is for
- Where to start
  - If you’re new
  - If you need maximum protection
- Key features
  - Video access restrictions
  - DRM encryption
  - Watermarks
- Key use cases

In this section you will learn how to protect your video content in Kinescope. Here you will find instructions for setting up access restrictions, DRM encryption, and watermarks. These tools help prevent unauthorized use of your content.

Configure who can watch your videos:

Learn more about access restrictions →

Technical protection against downloading and screen recording. Even if an attacker downloads your content, it cannot be played without a license.

Learn more about DRM encryption →

Add dynamic or static watermarks to designate authorship. Watermarks help identify the source of content in case of a leak.

Learn more about watermarks →

Restrict video access to paying users only. Use private links, passwords, or integration with an authorization backend.

Protect internal content from leaks. Use domain restrictions to make video available only on the corporate site.

For maximum protection, use a combination of DRM encryption, watermarks, and access restrictions. This prevents copying and distributing content.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

DRM encryption in Kinescope protects video from downloading and screen recording. Videos in playlists are protected the same way. Combine with authorization backend for access control.

Watermarks in Kinescope: dynamic (viewer data) and static (text or logo). They help reduce the risk of leaks and designate authorship.

Access restrictions in Kinescope: private link, password, unique codes, access by email domain, and embedding restrictions by domain. Step-by-step instructions.

---

## DRM File Encryption - Kinescope Help center

**URL:** https://docs.kinescope.com/content-protection/drm-encryption/

**Contents:**
- DRM File Encryption
- Who this article is for
- Important about encryption
- DRM and access control
  - DRM compatibility
- Step-by-step instructions
  - Sample embed code for a player with DRM
- If embedded videos do not play
- Frequently asked questions
- What’s next?

Kinescope has built-in DRM file encryption (MPEG-CENC, Apple FairPlay, Google Widevine) to protect video from unauthorized downloading. Encrypted video cannot be downloaded or played even after saving. DRM blocks downloading via browser plugins and screen recording on mobile devices.

Course creators — need to protect educational materials from downloading and screen recording

Premium content owners — need maximum video protection against piracy

Developers — need to integrate DRM with an authorization backend for access control

Super plan users — need to enable DRM encryption for projects

Downloading via browser plugins (e.g., SaveFrom) and separate programs (VLC, ffmpeg) is blocked.

On iOS and Android, as well as in browsers for macOS and Windows, it is impossible to take a screenshot or record the screen when playing a video.

Encryption is included in the Super plan and is available in project settings (the feature is disabled by default). After enabling:

DRM encryption protects the file technically: it blocks downloading and screen recording. But if you need to control who can watch video based on your system’s rules (courses, subscriptions, roles), use an authorization backend.

How they work together:

When a user tries to watch a video with DRM and an authorization backend:

When you need an authorization backend: If you want to restrict video access by courses, subscriptions, roles, or other rules in your system. See the Authorization Backend for Video Access Control documentation for setup details.

In the catalog , hover over a project name and select Project Settings from the context menu.

Opening project settings to enable DRM

In settings, click Enable Encryption, review the warnings, and confirm the action.

Enabling encryption in project settings

Wait for the process to complete. Progress can be tracked in project settings.

Check embed settings and SSL. Make sure:

Basic variant (DRM only):

With authorization backend (DRM + access control):

If you use an authorization backend for access control, pass the user identifier via the drmauthtoken parameter:

You can use user_id, a JWT token, or any other identifier your backend can verify as the token. See the Authorization Backend for Video Access Control documentation for setup details.

If something doesn’t work, the support chat within the Kinescope interface.

If I enable DRM on all current projects, will I need to re-embed everything on my site, change the player code? Or will it work?

— No changes needed. All changes will take effect automatically; videos will be accessible at the same links.

Playlists and encryption: do I need to enable anything separately?

— No. A playlist is a video catalog; the media files of the project are encrypted. Videos in a playlist from the same project play with DRM just like via a direct link. No need to separately enable encryption for a playlist — moving a playlist to another project does not change the encryption of the videos themselves: only the media files of the project they belong to are encrypted.

Do I need to add the encrypted parameter everywhere after enabling DRM for current projects?

— Nothing needs to be added. This parameter is already in the embed code.

The encrypted-media parameter in the embed code

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Watermarks in Kinescope: dynamic (viewer data) and static (text or logo). They help reduce the risk of leaks and designate authorship.

Access restrictions in Kinescope: private link, password, unique codes, access by email domain, and embedding restrictions by domain. Step-by-step instructions.

**Examples:**

Example 1 (jsx):
```jsx
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

Example 2 (jsx):
```jsx
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?drmauthtoken=${user_id}"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

---

## Dynamic and Static Watermarks - Kinescope Help center

**URL:** https://docs.kinescope.com/content-protection/watermarks/

**Contents:**
- Dynamic and Static Watermarks
- Who this article is for
- Dynamic watermarks
- Static watermarks
- What’s next?
- Related articles
  - Table of contents

Watermarks help protect content, designate authorship, and reduce the risk of copying. Kinescope has two types of watermarks: dynamic and static. Dynamic watermarks show viewer data (email, name, ID) and help identify the source of a leak, while static watermarks are a permanent text or logo.

Use separate instructions if you want to add such marks to videos on sites in the Tilda website builder or on the GetCourse platform.

A dynamic watermark is text that randomly appears in different places on the screen during video playback. This can be user data (e.g., email or name) to make it easy to trace the source of a leak in case of unauthorized copying. Such marks are suitable for educational videos, private content, or corporate data.

To use dynamic watermarks, add a variable to the embed code:

A static watermark is text or a logo that is permanently displayed on screen during video playback. This type of watermark is most commonly used to designate authorship or indicate rights. Suitable for public videos, commercials, and widely distributed content.

Setting up a static watermark in the player

To add a static watermark:

Enable watermarks in the Kinescope player settings:

In the video embed code, specify the watermark text in the watermark parameter:

You can also use a logo as a watermark. To do this, configure the logo in the Kinescope player settings:

Adding a logo as a watermark

If you still have questions, write to the support chat within the Kinescope interface — specialists will help you set up watermarks and understand the code.

DRM encryption in Kinescope protects video from downloading and screen recording. Videos in playlists are protected the same way. Combine with authorization backend for access control.

Access restrictions in Kinescope: private link, password, unique codes, access by email domain, and embedding restrictions by domain. Step-by-step instructions.

**Examples:**

Example 1 (jsx):
```jsx
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?watermark=${user_data}"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

Example 2 (sass):
```sass
<iframe
 	src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?watermark=Your_text"
  	width="640"
  	height="360"
  	frameborder="0"
allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

---

## Video Access Restrictions - Kinescope Help center

**URL:** https://docs.kinescope.com/content-protection/access-restrictions/

**Contents:**
- Video Access Restrictions
- Who this article is for
- Private link
- Password access
- Access by unique codes
  - How to enable access by codes
  - What the viewer sees
  - How to delete codes
  - FAQ
- Access by email domain

In Kinescope you can configure who can view your videos and where they can be embedded. This helps protect content and control access. Access can be restricted by private link, password, email domain, or by allowing embedding only on certain sites.

To configure access restrictions, open the “Who can view?” field in the privacy settings and select one of five levels:

Video access settings in privacy configuration

Setting up a private link

If you need to provide access to video without disabling domain restrictions, use the private link access privacy setting. This option lets you bypass the configured domain restrictions.

Bypassing domain restrictions via private link

Unique codes restrict access to a video or live stream: only those who received a code from you can watch. Useful when you don’t need user accounts or registration — for example, for paid webinars or private screenings.

Access by unique codes

Selecting unique codes access mode

The downloaded file contains two columns:

The viewer opens the video link, enters the code they received, and then gets access to the video.

If the code is already being used in another session, the viewer sees a warning:

This means the viewer who is already watching will temporarily lose access — it will pass to the new viewer using the same code.

If multiple viewers are allowed to use one code, each of them gets simultaneous access to the video.

In the code manager, select the set, click Delete, and confirm in the dialog window.

Can one code be used on multiple devices at the same time?

By default, one code works in one session. If the “Allow multiple viewers to use one code” field is set to a higher number, that many viewers can watch simultaneously. When the limit is exceeded, the new viewer displaces the previous one.

What happens if a viewer enters a code after it has expired?

The code will not work and access will not be granted. The viewer will see a message that the code has expired.

Can codes be added to an existing set?

No, codes cannot be added to a set — simply generate a new one. The number of sets is unlimited.

If codes are deleted and the same access mode is re-enabled, will they be restored?

No. Deleted codes cannot be restored; new ones must be generated.

Setting up privacy settings for email domain access

Setting up access by email domain

Adding an email for domain-based access

Code for video viewing in email

Video access after verification

In Kinescope you can restrict media file embedding by domain, so content is only placed on trusted sites. The setting is available in the “Where can the player be shown?” section and offers three options:

Setting up embedding by domain

To allow embedding media files on certain domains:

To view the list of videos linked to a specific domain:

To remove a domain from the trusted list:

Using the domain manager you can add, edit, and delete domains, as well as view media files linked to them:

Via the Domains dialog window in the settings of a specific file.

Managing domains in Kinescope

Via the settings section in the dashboard.

Domain manager in settings

If a domain is no longer used, you can:

To do this, click the Archive domain or Delete icon next to the domain. In the dialog window, select the desired action. Archived domains can be restored in the Archive tab by clicking Restore domain.

If you still have questions, write to the support chat within the Kinescope interface — specialists will help!

DRM encryption in Kinescope protects video from downloading and screen recording. Videos in playlists are protected the same way. Combine with authorization backend for access control.

Watermarks in Kinescope: dynamic (viewer data) and static (text or logo). They help reduce the risk of leaks and designate authorship.

---
