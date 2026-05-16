# Kinescope - Other

**Pages:** 20

---

## Documentation updates - Kinescope Help center

**URL:** https://docs.kinescope.com/whats-new/

**Contents:**
- Documentation updates
- 2026
    - April 28
  - Use cases
    - April 23
  - Kinescope MCP Server and Smithery CLI
    - April 14
  - Unique codes in media file settings
    - April 9
  - Player customization: downloads, subtitle search, default playback speed

Added practical use cases for tracking delayed live stream starts with webhooks and deciding when to provide login and password for Basic Auth on a webhook endpoint. → Use cases

Claude Desktop setup updated: the deprecated Smithery install flow is replaced with mcp add, and the restart steps now spell out applying the MCP configuration. Troubleshooting and the multi-account FAQ aligned with the same commands. → Kinescope MCP Server

The fifth viewer access level is now covered in the main media file settings: a short section with a link to the detailed article, along with clarifications on embedding behavior and sharing guidance. → Media File Settings

Added controls for default playback speed, downloading video and transcriptions, subtitle search, and scale in the settings menu. Screenshots updated. → Player Customization

Documented the AI auto-generation flow for chapters and subtitles: how to start it, what you get as a result, and what to watch for. → Working with Files: Subtitles, Chapters, and More

Added documentation for restricting video access via unique codes. Each viewer receives a personal code to enter before watching — ideal for paid webinars and private screenings. Screenshots added for all steps. → Video Access Restrictions

Added a note on automatic recording import behavior and how videos uploaded before the integration was set up are handled. → Zoom Integration

Added a section on restricting video access by work email domain: how to configure it, which addresses qualify as work emails, and how to allow multiple domains. Access settings screenshots updated. → Video Access Restrictions

Updated content and screenshots for stream setup and the live stream guide. → Live Stream Guide

Updated profile and workspace settings page with new screenshots. → Profile and Workspace Settings

Added a section on premoderation mode: how to enable message review before publishing and manage the queue in real time. → Live Stream Guide

---

## How to track delayed live stream starts - Kinescope Help center

**URL:** https://docs.kinescope.com/use-cases/track-delayed-live-stream-starts/

**Contents:**
- How to track delayed live stream starts
- When this scenario fits
- How to set it up
- What to keep in mind
- Related materials
- Related articles
  - Table of contents

If you need to see which live streams started later than planned, use webhooks. We send an event when a media status changes, and your system can compare the actual event time with the scheduled start time.

This scenario fits when you already have the scheduled stream time: for example, in an LMS, CRM, event schedule, or your own admin panel.

Kinescope does not calculate the start delay instead of your system. We can send a status-change event, and your side should calculate the delay: store the scheduled time, receive the webhook, and compare it with the actual event time.

This lets you build a report showing which live streams started later than scheduled and by how many minutes.

The webhook reports an event in Kinescope, but it does not know your schedule. If the scheduled time lives in an external system, that system should calculate the delay.

Also account for webhook delivery delays and retries on your side. For analytics, it is usually enough to calculate the delay by the actual event time, or by the first successful webhook receive time if your data model has no separate event timestamp.

When to specify login and password when creating a webhook in the Kinescope API, and how they relate to Basic Auth on your endpoint.

---

## Kinescope Help center

**URL:** https://docs.kinescope.com/

**Contents:**
  - Search results
  - Documentation sections

Detailed guides and ready-made solutions — from getting started with the platform to working with the player, live streams, integrations, and API.

Use the search or navigate to the section you need. If you haven't found the answer — feel free to contact support on the website and in the product interface.

---

## Kinescope MCP FAQ - Kinescope Help center

**URL:** https://docs.kinescope.com/kinescope-mcp/faq/

**Contents:**
- Kinescope MCP FAQ
- General questions
  - What is MCP and why is it needed?
  - Which platforms support MCP?
  - is there a cost for using MCP?
  - is using MCP safe?
- Setup and connection
  - How do i configure the connection to MCP Server?
  - Can i use web versions of AI assistants?
  - Can i use free options?

Answers to common questions about working with Kinescope MCP Server.

Model Context Protocol (MCP) is an open standard developed by Anthropic that allows AI assistants to securely interact with external services and data.

Why MCP is needed for Kinescope:

Kinescope MCP Server works with any platform supporting the MCP protocol. We recommend four options:

1. Cursor (for developers)

2. Claude Desktop (recommended for general use)

3. Claude Code (for developers with Claude)

4. Qwen3 (desktop application)

See the current list of all MCP clients in the MCP documentation .

For Kinescope MCP Server:

Additional requirements:

Security recommendations:

The current step-by-step setup for different clients (Cursor, Claude Desktop, Claude Code, Qwen3, etc.) is described in the Configuring the MCP Server connection section.

No, web versions are not supported.

Yes, there are free options:

Additional requirements (free):

Kinescope MCP functionality is independent of the platform:

The difference is only in the interface, cost, and AI usage limits.

Possible causes (wrong API token, network, configuration error) and step-by-step solutions for Cursor, Claude Desktop, Claude Code, and Qwen3 are described in the Troubleshooting section of the main guide.

Yes, you can configure multiple connections:

in Cursor or Claude Code:

Switching between accounts:

Specify which account to use in the query, or switch the active server in settings.

MCP Server automatically works with all projects you have access to. Simply specify the project name in the query:

You can edit video metadata:

Use the web interface or specialized tools for file editing.

Data is updated in real time. When you make a query through MCP Server, you get current information from your Kinescope account.

No, direct video file download through MCP is unavailable.

Use the Kinescope web interface for downloading.

Metric availability depends on your Kinescope plan.

Yes, you can ask the AI to export data:

The AI assistant can create:

Use a step-by-step approach:

Detailed examples: Usage Examples

Yes, standard Kinescope API rate limits apply:

When the limit is exceeded, you will get an error suggesting to retry after a few seconds.

Yes, but with limitations:

Minimum: any Kinescope plan

Recommended: Business or higher

Why Business or higher:

Only you, if you have not shared the connection settings.

For team collaboration:

AI can only do what is permitted by your rights in Kinescope:

Yes, all actions through MCP Server are recorded in your Kinescope account logs, just like actions through the web interface.

Yes, simply delete or disable the MCP server in your AI assmstant’s settings (Cursor or Qwen3). Access through MCP will be immediately terminated.

Yes, AI assistants can work simultaneously with Kinescope MCP and other services:

MCP Server allows the AI assistant to work with multiple services simultaneously.

integration examples:

Partially. AI assistants with MCP support are great for:

For full automation (scheduled tasks, webhooks), use Kinescope API .

Cause: authorization issues

Cause: rate limit exceeded

Cause: the query is worded ambiguously

Cause: caching or processing delay

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Detailed guide to setting up Kinescope MCP Server: connecting in Cursor, Claude Desktop via Smithery CLI (mcp add), Claude Code, and Qwen3, video management, and analytics.

Practical scenarios for working with Kinescope through Am assistants: video search, analytics, content management, creating reports, bulk operations.

**Examples:**

Example 1 (sql):
```sql
Show videos from the "Marketing" project
```

Example 2 (unknown):
```unknown
Export statistics for all videos for the month to Google Sheets
```

Example 3 (unknown):
```unknown
Create a CSV file with a list of all videos and their metadata
```

Example 4 (unknown):
```unknown
Show view statistics for Q4 2025
```

---

## Kinescope MCP (Model Context Protocol) - Kinescope Help center

**URL:** https://docs.kinescope.com/kinescope-mcp/

**Contents:**
- Kinescope MCP (Model Context Protocol)
- Who this section is for
- What is Kinescope MCP
- Key features
  - Video management
  - Analytics
  - Content organization
  - Live streams
  - Additional
- Where to start

Kinescope MCP Server is a server implementing the Model Context Protocol (MCP), which allows AI assistants to securely interact with the Kinescope platform through natural language queries.

Model Context Protocol (MCP) is an open standard developed by Anthropic that allows AI assistants to securely interact with external services and data.

Examples of what you can do:

Option 1: Cursor (recommended for developers)

Option 2: Claude Desktop (recommended for general use)

Option 3: Claude Code (for developers with Claude)

Option 4: Qwen3 (desktop app)

Kinescope MCP Server works with any platform supporting the MCP protocol:

Current version: Public beta

Kinescope MCP Server is under active development. The core functionality is stable and ready to use, but changes to the API and new features may be added.

We are actively developing Kinescope MCP Server and welcome your feedback!

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Detailed guide to setting up Kinescope MCP Server: connecting in Cursor, Claude Desktop via Smithery CLI (mcp add), Claude Code, and Qwen3, video management, and analytics.

Practical scenarios for working with Kinescope through Am assistants: video search, analytics, content management, creating reports, bulk operations.

Answers to common questions about Kinescope MCP Server: setup, security, platforms, limitations, troubleshooting.

**Examples:**

Example 1 (sql):
```sql
1. Get Q3 OKRs from Google Drive
2. Find all tutorial videos for the quarter
3. Show retention rate and geography
4. Compare with target KPms
5. Create a Google Doc with the report
```

Example 2 (sql):
```sql
1. Find videos without descriptions or with outdated tags
2. Create a tracking spreadsheet
3. identify update priorities
```

Example 3 (sql):
```sql
1. Update privacy for internal videos
2. Restrict access by corporate domains
3. Verify access rights by project
```

---

## Kinescope MCP Server - Kinescope Help center

**URL:** https://docs.kinescope.com/kinescope-mcp/kinescope-mcp-server/

**Contents:**
- Kinescope MCP Server
- Who this section is for
- Where to start
  - Step 1: Choose a platform
  - Step 2: Preparation
  - if you already work with Kinescope
- What you can do through MCP Server
  - Video and content management
  - Working with projects and structure
  - Analytics and statistics

Kinescope MCP Server is a server implementing the Model Context Protocol (MCP), which allows AI assistants to interact with the Kinescope platform through natural language queries. You can manage videos, get analytics, configure projects, and work with content simply by talking to an AI assistant.

Option 1: Cursor (recommended for developers)

Option 2: Claude Desktop (recommended for general use)

Option 3: Claude Code (for developers with Claude)

Option 4: Qwen3 (desktop application)

Before configuring, get an API token:

Step 1. install Cursor

Step 2. Configure MCP Server

Open the MCP configuration file:

Add the Kinescope configuration:

Step 3. Verify the connection

if the connection does not work:

Step 1. install Claude Desktop

Step 2. install MCP Server via terminal

Step 3. Restart the application

Step 4. Verify the connection

if the connection does not work:

Step 1. install Claude Code

Step 2. Configure MCP Server

Open the MCP configuration file:

Add the Kinescope configuration:

Step 3. Verify the connection

if the connection does not work:

Step 1. install Qwen3

Step 2. Configure MCP Server

Step 3. Verify the connection

Working with playlists:

Step 1. Collecting data from Google Drive:

Step 2. Analyzing videos in Kinescope:

Step 3. Detailed statistics:

Step 4. Comparing with targets:

Step 5. identifying issues:

Step 6. Creating the report:

Step 7. Recommendations:

Finding unoptmmmzed content:

Team members get access to MCP Server in accordance with their project access rights in Kinescope.

Rights configuration:

We recommend using the Super plan or higher for full access to MCP Server capabilities.

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Practical scenarios for working with Kinescope through Am assistants: video search, analytics, content management, creating reports, bulk operations.

Answers to common questions about Kinescope MCP Server: setup, security, platforms, limitations, troubleshooting.

**Examples:**

Example 1 (json):
```json
{
  "mcpServers": {
    "Kinescope MCP": {
      "type": "streamable-http",
      "url": "https://api.kinescope.io/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

Example 2 (bash):
```bash
npx -y @smithery/cli@latest mcp add kinescope/kinescope-mcp --client claude
```

Example 3 (json):
```json
{
  "mcpServers": {
    "Kinescope MCP": {
      "type": "streamable-http",
      "url": "https://api.kinescope.io/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

Example 4 (json):
```json
{
  "mcpServers": {
    "Kinescope MCP": {
      "type": "streamable-http",
      "url": "https://api.kinescope.io/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

---

## Kinescope MCP Usage Examples - Kinescope Help center

**URL:** https://docs.kinescope.com/kinescope-mcp/usage-examples/

**Contents:**
- Kinescope MCP Usage Examples
- Who this article is for
- Where to start
  - Choose your platform
- Basic operations
  - Searching and viewing information
  - Editing metadata
  - Managing structure
- Analytics and reports
  - Basic analytics

This article contains ready-made query examples and usage scenarios for Kinescope MCP Server. Use them as a foundation for automating your tasks.

Works with: Cursor, Claude Desktop, Claude Code, and Qwen3 (desktop application). All examples are universal.

All examples work identically in Cursor, Claude Desktop, Claude Code, and Qwen3 (desktop application). Choose a platform and configure the connection:

Cursor (for developers)

Claude Desktop (recommended for general use)

Claude Code (for developers with Claude)

Qwen3 (desktop application)

Search by multiple criteria:

View video information:

List of all projects:

Adding a description:

Comprehensive update:

Videos with low completion:

Checking availability:

Configuring restreaming:

Goal: Create a report on video content for the week

Goal: Find videos that need updating

Goal: Collect data for a results presentation

Goal: Organize your media library

Sync with spreadsheets:

Reports in Google Docs:

Checking processing status:

Checking accessibility:

Analytics and reports:

Google Workspace integration:

Cursor — for developers and code integrationClaude Desktop — for general useClaude Code — for developers with ClaudeQwen3 — free desktop application

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Detailed guide to setting up Kinescope MCP Server: connecting in Cursor, Claude Desktop via Smithery CLI (mcp add), Claude Code, and Qwen3, video management, and analytics.

Answers to common questions about Kinescope MCP Server: setup, security, platforms, limitations, troubleshooting.

**Examples:**

Example 1 (unknown):
```unknown
Find all videos with the "tutorial" tag
```

Example 2 (unknown):
```unknown
Show videos uploaded in December 2025
```

Example 3 (sql):
```sql
Find videos with the "onboarding" or "training" tags from the "HR" project
```

Example 4 (unknown):
```unknown
Show detailed information about the video with ID abc123
```

---

## Kinescope Pricing Plans: How to Choose and Pay - Kinescope Help center

**URL:** https://docs.kinescope.com/pricing-and-billing/kinescope-pricing-plans/

**Contents:**
- Kinescope Pricing Plans: How to Choose and Pay
- How to choose a plan?
- Free — for small projects and platform testing
- Super — for regular video work
- Mega — for large projects and non-standard requirements
- What makes up pay-as-you-go billing?
  - 1. File storage volume
  - 2. Data transfer traffic (CDN)
  - 3. Video transcoding
- How to calculate cost?

Kinescope has three pricing plans and pay-as-you-go billing — there is a suitable option for every business and project. Below are plan descriptions, billing rules, and calculation examples.

Kinescope plan comparison

Choose a plan based on your needs and project scale:

Free plan is suitable if you are testing the platform, working on a small project, or a landing page with a few videos. This way you can get familiar with Kinescope’s capabilities without paying.

“Super” plan is suitable for educational platforms, media projects, and businesses where video is the primary content. Choose it if you have outgrown the free plan’s limits or if you plan to work with video regularly from the start.

“Mega” plan is for large projects: media holdings with large archives, LMS systems, and streaming platforms. It is suitable if you need individual terms, a guaranteed SLA, and dedicated support.

If at least one of these scenarios fits you — read on. Below you will find a detailed description of each plan and cost calculation examples.

Suitable for personal use, small projects, landing pages, and platform testing.

This way you can get familiar with Kinescope without paying. When you need more features, you can switch to the “Super” plan at any time.

Suitable for educational or media projects, as well as for those who have outgrown the free plan.

On the “Super” plan, billing works on a pay-as-you-go principle. You pay only for the resources actually consumed per month. This is similar to paying utility bills by a meter. Billing is calculated on the 1st of the following month.

A plan for projects with large content and traffic volumes, or special infrastructure and support requirements.

If your project requires a special approach and guarantees, the “Mega” plan may be right for you.

The amount due is made up of three indicators. Let’s look at each in detail.

Everything stored on Kinescope servers is counted:

The data volume is recalculated daily. If you deleted some data in the middle of a month, the amount due on the 1st of the new month will be lower. You can track all changes in the invoice details.

This is the volume of data in GB delivered to viewers from the Kinescope server. Traffic during the initial upload of video to the server is not counted.

Example: Your video in 1080p quality weighs 1 GB. A viewer watched half of it — you will only need to pay for 0.5 GB of traffic.

When a video is uploaded, Kinescope creates additional versions in different qualities (for example, 1080p, 720p). This is needed for adaptive delivery — the viewer gets the quality suited for their internet connection.

Transcoding is billed per minute for each new video upload. Unlike traffic and storage, which are billed monthly, transcoding is paid once upon upload.

Example of volume increase after processing:

If your source file weighs 41 MB, after upload and processing in Kinescope the total file volume increases to 110 MB. This happens because the system creates video versions in different qualities for adaptive delivery.

Video assets and pricing sources in Kinescope

How to reduce storage costs:

Upon request to support, you can disable original storage. This will reduce storage costs. In this case, the responsibility for preserving originals shifts to you.

You can independently calculate expenses using the examples below. The larger the content volumes, the lower the cost of using Kinescope. The price table will help with calculations.

Kinescope uses post-payment billing. This means you do not need to make an advance payment or keep funds on a balance. An invoice is generated automatically on the 1st of each month for all services consumed in the previous month.

You can monitor expenses in the Billing section . Information is updated once a day. You can also see the total outstanding balance for all time.

To see detailed expenses, download a preliminary invoice in PDF or CSV format. You do not need to pay it — it is for information only.

To view monthly invoices, go to the Invoices section . There you can:

You can link or update a card via the “Add payment method” button. Card charges happen automatically monthly. After successful payment, a fiscal receipt is sent to your email.

To enable bank transfer, complete two steps:

After choosing a plan and setting up billing, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

---

## Live Streams - Kinescope Help center

**URL:** https://docs.kinescope.com/live-streams/

**Contents:**
- Live Streams
- Who this section is for
- Where to start
  - If you are new
  - If you already run streams
- Key features
  - Two ways to stream
  - Stream chat
  - Restreaming
  - Stream recording

Kinescope supports live streams with recording, restreaming, view analytics, access control, and embedding on a website together with chat. It is a solution for webinars, lectures, online events, and streaming.

Using video encoders (OBS Studio, Vmix, Zoom)

Learn more about streaming methods →

When a stream starts, a chat is automatically created that can be:

Learn more about chat setup →

Simultaneously stream on multiple platforms without additional internet bandwidth load. Supports forwarding the stream to YouTube and other platforms via RTMP protocol.

Learn more about restreaming →

All streams can be recorded automatically. Recorded video is saved to the catalog and available for viewing, editing, and publishing immediately after the stream ends.

Run webinars with recording, chat, and access restriction options. Recorded streams can be used as course lessons.

Use restreaming to simultaneously broadcast on YouTube and other platforms. Reach a larger audience without additional bandwidth load.

Run internal streams with access restrictions by domain or password. Record important events for the archive.

Host live streams with chat, view analytics, and the option to monetize via advertising.

After setting up streams, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Guide to running live streams through Kinescope: setup via OBS Studio and other video encoders, using chat, choosing RTMP servers, and restreaming.

Step-by-step instructions for setting up OBS Studio and Zoom for streams via Kinescope: installation, configuration, and recommendations for quality broadcasting.

Restreaming in Kinescope: simultaneous streaming to multiple platforms to increase audience reach without additional internet bandwidth load.

---

## Live Stream Guide - Kinescope Help center

**URL:** https://docs.kinescope.com/live-streams/live-stream-guide/

**Contents:**
- Live Stream Guide
- Two ways to stream
  - Using streaming programs (video encoders)
  - Mobile apps
- Stream chat
  - Chat settings
  - Message premoderation
    - How to enable
    - What happens to a message
    - If premoderation is toggled during a live stream

This guide covers stream launch options, using chat, server configuration, and other aspects. You will learn how to set up a stream via OBS Studio, Vmix, Zoom, or mobile apps, how to use chat, and how to choose the optimal server for your region.

Creating a new live stream event in Kinescope

For streaming, you can use OBS Studio, Vmix, a paid Zoom account (instructions ), or hardware streamers. Step-by-step instructions for setting up popular programs to launch streams and webinars through Kinescope ([find here]/live-streams/stream-setup-instructions/)

Use apps like Larix to stream from a mobile device.

Connecting encoding software to Kinescope stream

Live stream chat in Kinescope player

When a stream starts in Kinescope, a chat is automatically created.

Chat moderation is available in the Studio section of the event settings.

Show chat by link — enable chat display when opening the video via a link.

Chat behavior inside the player:

Hide — chat is not displayed in the player (default option).

Always show — chat is always visible next to the video.

Always show chat mode in Kinescope player

Fullscreen mode — chat appears only when expanding to full screen.

Fullscreen mode with chat in Kinescope player

Chat expanded on player load — chat opens immediately.

Hide user links in chat — protects chat from spam.

Show participant list — see who is currently watching the stream.

Unique names in chat — prevents confusion with identical nicknames.

Slow mode — limits the interval between messages from 0 to 300 seconds.

When there are hundreds of participants in a chat, spam and offensive messages can appear instantly. Premoderation holds each new message for a set amount of time, giving a moderator a chance to review it. If the moderator takes no action, the message is published automatically.

Message premoderation in Kinescope chat

Premoderation is enabled and configured by the event organizer.

Premoderation can be turned on or off at any point during a live stream.

The viewer sends a message and sees it in their own chat immediately — other viewers do not see it yet.

The moderator sees the message highlighted in red. During the delay, the moderator can:

Moderator view of pending messages in Kinescope chat

If the moderator takes no action, the message is published for everyone after the delay.

Only published messages appear in the chat history. If a moderator deleted a message before it was published, it will not appear in the chat.

Message order reflects the time of publication, not the time the message was sent.

I sent a message but others can’t see it — why?Premoderation is enabled: the message is waiting for the delay to end or for the moderator’s decision.

I can see my message but my friend can’t — why?You see your own message immediately after sending; others see it only after it is published.

What happens to messages if premoderation is turned off during a stream?Messages waiting for moderation are immediately published for everyone; messages already deleted by the moderator are not restored.

Can the delay be changed during a stream?Yes. Open the stream settings, update the value, and save. The new delay applies to messages sent after the change.

If you know where the streamer is located or if you are using a VPN, choose a server based on the region.

Use the rtmps protocol and port 1936.

After setting up the stream, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Step-by-step instructions for setting up OBS Studio and Zoom for streams via Kinescope: installation, configuration, and recommendations for quality broadcasting.

Restreaming in Kinescope: simultaneous streaming to multiple platforms to increase audience reach without additional internet bandwidth load.

---

## Pricing and Billing - Kinescope Help center

**URL:** https://docs.kinescope.com/pricing-and-billing/

**Contents:**
- Pricing and Billing
- Main sections
- Where to start
  - If you are choosing a plan
- Key topics
  - Kinescope plans
  - Pay-as-you-go billing
- Frequently asked questions
- What’s next?
- Section pages

This section contains all information about Kinescope pricing plans, payment methods, and document management. Everything you need to choose the right plan and set up billing is here.

Kinescope has three pricing plans:

Learn more about plans →

On the “Super” plan, you pay only for the resources you actually use:

How to calculate cost →

Which plan should I choose? Start with the free plan to get familiar with the platform. You can switch to another plan at any time.

How does payment work? Kinescope uses post-payment — an invoice is generated automatically on the 1st of each month for the previous month.

After choosing a plan and setting up billing, we recommend:

If you have questions, write to the support chat within the Kinescope interface — our specialists will help!

Kinescope has three pricing plans and pay-as-you-go billing — there's a solution for every business. Plan comparison, selection recommendations, cost calculation examples, and payment methods.

---

## Profile and Workspace Settings - Kinescope Help center

**URL:** https://docs.kinescope.com/team-management/profile-and-workspace-settings/

**Contents:**
- Profile and Workspace Settings
- Who this article is for
- How to access profile settings?
  - What can you configure in your profile?
  - How to configure two-factor authentication
    - Step-by-step instructions
    - How login with two-factor authentication works
    - How to disable two-factor authentication
- Workspaces in Kinescope
  - Workspace capabilities

Kinescope has two settings sections: “My Profile” — personal settings, and “General” — workspace settings. Personal settings apply to all workspaces, while workspace settings apply only to the current workspace.

Accessing profile settings

Personal details configuration in profile

Profile security settings

Two-factor authentication (2FA) is an additional layer of protection for your account. Even if someone learns your password, they cannot log in without access to your phone. Let’s walk through how to set this up in a couple of minutes.

Two-factor authentication in settings

Step 1. Open profile settings

Opening profile settings for 2FA configuration

Step 2. Go to 2FA settings

In the “Two-factor authentication” section, click the “Enable two-factor authentication” button.

Enabling two-factor authentication

Step 3. Install an authenticator app

For 2FA to work, you will need a special app on your phone. Download and install one of these options:

Both apps are free and work the same way.

Installing an authenticator app

Step 4. Scan the QR code

Step 5. Enter the code from the app

Entering the code from the authenticator app

Done! Two-factor authentication is enabled.

Activating two-factor authentication

Step 6. Save backup codes

After activating 2FA, the system will offer to save backup codes. Never share them and store them in a safe place.

Backup codes are needed if:

Saving backup codes for 2FA

After enabling 2FA, the login process will look like this:

If you need to disable 2FA:

Note: disabling two-factor authentication without a serious reason is not recommended. This reduces the level of protection for your content.

Workspaces are designed for organizing projects, separating tasks, and team collaboration. Creating multiple workspaces is only available on “Super” and “Mega” plans. Full workspace settings management is only available to “Administrator” and “Editor Plus” roles. Learn more about roles and their rights in the article Team Access Rights Management .

Navigating to a workspace

Creating a new workspace

Hover over the avatar or initials icon in the bottom left corner → “General”.

Here you can set the workspace name, choose a timezone, and upload a logo.

On the left there is a list of sections: “Team”, “Players”, “Tags”, “Domains”, “File requests”, “API tokens”. These sections apply only to the selected workspace and help manage everything in one place.

Here you can add data corresponding to the sections. Sections will also be populated from your actions in the catalog. For example, if you create a new player when uploading a video, it will appear in the “Players” section list.

Payment settings in the “Invoice payment” section are available for “Administrator” and “Financial Manager” roles. They are also individual for each workspace.

Workspace payment settings

Yes, but you first need to transfer or delete all projects. Deletion is available through Kinescope support for administrators only.

Go to workspace settings, add members, and assign them roles. The article Team Access Rights Management describes roles and their rights in detail.

After configuring the profile and workspace, we recommend:

If you have questions, write to the support chat within the Kinescope interface — our specialists will help!

Managing access rights in Kinescope: user and guest roles, inviting members, restricting access to projects and folders.

---

## Restreaming - Kinescope Help center

**URL:** https://docs.kinescope.com/live-streams/restreaming/

**Contents:**
- Restreaming
- Who this article is for
- When is restreaming needed?
- How to configure restreaming in Kinescope?
  - Step 1: Get the URL and stream key from the third-party platform
  - Step 2: Add restreaming data to Kinescope
  - Step 3: Start the stream
- Restreaming recommendations
- What’s next?
- Related articles

Restreaming allows you to simultaneously stream on multiple platforms, increasing audience reach without additional internet bandwidth load. You stream a single feed into Kinescope, and the platform automatically forwards it to all connected external services.

Kinescope supports forwarding video streams to external platforms using the RTMP (Real-Time Messaging Protocol) protocol. This is a standard streaming protocol used by YouTube, Facebook Live, and many other services.

Restreaming setup takes a few minutes and requires no additional hardware or software.

First, create a stream on the platform where the feed will be forwarded:

Restreaming configuration in Kinescope

After configuring restreaming, we recommend:

If you have questions, write to the support chat within the Kinescope interface — our specialists will help!

Guide to running live streams through Kinescope: setup via OBS Studio and other video encoders, using chat, choosing RTMP servers, and restreaming.

Step-by-step instructions for setting up OBS Studio and Zoom for streams via Kinescope: installation, configuration, and recommendations for quality broadcasting.

---

## Speak (beta) - Kinescope Help center

**URL:** https://docs.kinescope.com/speak-beta/

**Contents:**
- Speak (beta)
- Who this section is for
- Where to start
- Key features
  - Video meetings and calls
  - Meeting recording
  - Meeting streaming
  - Platform integration
- Main use cases
  - Webinars and online events

Speak is a video meeting feature in Kinescope. Run online meetings, webinars, and video calls directly on the platform with recording and streaming capabilities. All participants can communicate via video and chat, and meetings can be recorded for later viewing.

Host online meetings with multiple participants. Supports video and audio, screen sharing, and chat.

Record video meetings for later viewing. Recorded meetings are saved to the catalog and available for editing and publishing.

Stream meetings to viewers. Participants can watch the stream without joining the video call.

All Speak features are integrated with core Kinescope capabilities: catalog, analytics, content protection, and more.

Host webinars with recording and streaming capability. Participants can ask questions in chat, and you can share your screen.

Hold video meetings with your team. Record important discussions for later review.

Run online lessons with recording. Students can watch recorded lessons at their convenience.

After getting started with Speak, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Speak — a video call tool in Kinescope. Host online meetings, consultations, and training sessions, with recordings automatically saved to the catalog.

---

## Stream Setup Instructions - Kinescope Help center

**URL:** https://docs.kinescope.com/live-streams/stream-setup-instructions/

**Contents:**
- Stream Setup Instructions
- Who this article is for
- Setting up OBS Studio for streams via Kinescope
  - Step 1: Install OBS Studio
  - Step 2: Configure the stream in Kinescope
  - Step 3: Configure OBS Studio
  - Step 4: Configure video and audio
  - Step 5: Create scenes and add sources
  - Step 6: Test and start the stream
  - OBS Studio recommendations

This section contains step-by-step instructions for setting up popular programs to launch streams and webinars through Kinescope. You will learn how to configure OBS Studio and Zoom for stable, high-quality broadcasting.

OBS Studio is a popular video capture program whose reliable streaming can be trusted to Kinescope. A video with basic scenario setup via OBS Studio is available in the Live Stream Guide . Below is a step-by-step guide to properly configuring OBS Studio for use with Kinescope.

Download OBS Studio from the official website and install it on your computer.

Log in to your account on Kinescope .

Go to the “Streams” section and create a new stream.

Choose: “One-time event” (each stream with a new link) or “Recurring event” (one link for all streams).

After creating, you will receive the server URL (RTMP server) and stream key. You will need these for OBS Studio configuration.

Stream configuration in Kinescope

Stream service configuration in OBS Studio

Entering the RTMP server in OBS Studio

Video resolution configuration in OBS Studio

Video bitrate configuration in OBS Studio

In the OBS Studio main window, in the “Scenes” panel, click “+” and create a new scene (for example, “Main”).

In the “Sources” panel, click “+” and add the required sources:

Adding sources in OBS Studio

If you have questions or difficulties, Kinescope support is always ready to help. Happy streaming!

Below is a step-by-step guide to properly setting up the paid version of Zoom for streaming video to Kinescope.

Make sure you have accounts in Zoom and Kinescope:

Log in to your Kinescope account:

Stream configuration in Kinescope

Log in to your Zoom account on the website:

In the Zoom streaming popup window:

Paste the RTMP server URL and stream key received from Kinescope.

In the “Live Stream Page” field, paste a link to your website or the page with the Kinescope player.

Click the “Go Live!” button.

Your webinar is now being streamed through Kinescope.

Log in to the Kinescope dashboard and make sure:

If you want to change the RTMP URL in a Zoom stream, you need to restart the stream in Zoom. This can be done during the stream without ending the meeting. A one-time stream remains in standby mode for 10 minutes — during this time you can update the settings and resume the stream.

Stop streaming in Zoom

Opening stream settings to edit in Zoom

Stream settings form with RTMP URL field in Zoom

Saving updated stream settings in Zoom

If you have questions or difficulties, Kinescope support is always ready to help. Happy streaming!

After setting up streams, we recommend:

If you have questions, write to the support chat within the Kinescope interface — our specialists will help!

Guide to running live streams through Kinescope: setup via OBS Studio and other video encoders, using chat, choosing RTMP servers, and restreaming.

Restreaming in Kinescope: simultaneous streaming to multiple platforms to increase audience reach without additional internet bandwidth load.

---

## Team Access Rights Management - Kinescope Help center

**URL:** https://docs.kinescope.com/team-management/team-access-rights/

**Contents:**
- Team Access Rights Management
- Who this article is for
- Users and Guests
- Team management
- Roles in Kinescope
  - For “Users”:
  - For “Guests”:
- Inviting new members
- Restricting access to projects and folders
  - To restrict access:

Team collaboration works best when each member has access to the functionality they need. Kinescope provides flexible access management tools that will help your team keep content secure and stay focused on tasks.

In Kinescope, the team is divided into two types of members: Users and Guests, who work in the same workspace. You can manage members via the “Settings” → Team menu.

Team management section

The “Team” section has two tabs: “Users” and “Guests”. The number of each is shown in parentheses. If you have a large team, both tabs have member search functionality.

For each member, the following is displayed:

To change the role of a “User” or “Guest”, click on the current role of the selected member and choose a new one.

To remove a member, click on the three dots in the row of the selected member → “Remove user”.

Kinescope has no limit on the number of member invitations, and catalog work is free for all team members regardless of the number of workspaces.

To send an invitation:

When a new user follows the link from the invitation, they complete registration or gain access to a new workspace if they already have a Kinescope account.

After accepting the invitation, the member becomes a “User” and has full content access; it can be restricted in the next step. Unlike a “User”, a “Guest” gets access to a strictly defined location in the Catalog.

Users with “Administrator” and “Editor Plus” roles can hide selected projects and folders from all or some users.

Project access settings

Folder access settings

These restrictions can be removed at any time via the “Settings” → “Team” menu or quick navigation to team management in the access settings window. In the “Access” column in the table, restrictions for each team member are visible. Click on “Restricted access” in the row of the needed member, hover over the project or folder you want to remove the restriction from, and click the “X”.

After configuring access rights, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Profile and workspace settings in Kinescope: personal details, security, two-factor authentication, creating and managing workspaces for team collaboration.

---

## Team Management - Kinescope Help center

**URL:** https://docs.kinescope.com/team-management/

**Contents:**
- Team Management
- Who this section is for
- Where to start
  - If you are a project administrator
- Key features
  - Access rights management
  - Workspaces
  - File upload requests
  - Profile settings
- Main use cases

Kinescope supports team collaboration with a flexible system of access rights and workspaces. You can add team members, configure their rights, create workspaces for different projects and clients, and request file uploads without granting access to the system.

Add team members and configure their access rights. Each member sees only what they are permitted to see. Different roles are available: administrator, editor, viewer, and others.

Learn more about access rights management →

Workspaces let you separate projects and teams within a single account. This is convenient when you have multiple areas of work or many clients. Each workspace has its own projects, team, and settings.

Learn more about workspaces →

You can request file uploads to the catalog without granting system access. This is convenient for working with contractors and external contributors.

Learn more about access rights management →

Configure user profiles, enable two-factor authentication for security, and manage workspaces.

Learn more about profile settings →

Add team members and configure their access rights. Each member will see only the projects and files they have access to.

Create separate workspaces for each client. Each workspace will have its own team, projects, and settings, ensuring data isolation.

Use the file upload request feature so contractors can upload content without system access.

After setting up team collaboration, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

Managing access rights in Kinescope: user and guest roles, inviting members, restricting access to projects and folders.

Profile and workspace settings in Kinescope: personal details, security, two-factor authentication, creating and managing workspaces for team collaboration.

---

## Use cases - Kinescope Help center

**URL:** https://docs.kinescope.com/use-cases/

**Contents:**
- Use cases
- How to use this section
- Scenarios
- Section pages
  - Table of contents

This section collects practical scenarios for applying Kinescope in real tasks. It is not a separate private knowledge base, but a public layer on top of the documentation: the task, the recommended approach, important details, and links to related materials.

Choose a scenario that matches your task. Each page explains when the approach fits, how to configure it, and what details to keep in mind.

For technical context, follow the links in “Related materials” — they point to API methods, events, and settings used by the scenario.

How to use Kinescope webhooks to track live streams that start later than scheduled.

When to specify login and password when creating a webhook in the Kinescope API, and how they relate to Basic Auth on your endpoint.

---

## What is Speak? - Kinescope Help center

**URL:** https://docs.kinescope.com/speak-beta/what-is-speak/

**Contents:**
- What is Speak?
- Who this article is for
- Speak capabilities
- Mobile apps
- What’s next?
  - Table of contents

Speak is a tool for hosting video calls within Kinescope. Host online meetings, consultations, and training sessions, and recordings are automatically saved to the catalog.

Video call interface in Speak

New room with one click. Click the “Speak” button in the dashboard — Kinescope creates a new room with a unique link. Share the link with participants so they can join.

Up to 100 participants. Connect colleagues, clients, or students to online meetings without registration — only a link is needed.

Screen sharing. Show presentations, documents, or any materials from the screen. You can stream the entire screen, a specific window, or a browser tab.

Chat and reactions. Participants can ask questions, share links, or discuss materials without interrupting the conversation.

Meeting recording. An administrator can record meetings with automatic saving to the Kinescope catalog.

Mobile version. Participants can join meetings via a link from smartphones and tablets.

Download the Kinescope Speak app for your mobile device:

After getting started with Speak, we recommend:

Still have questions? Write to the support chat within the Kinescope interface — our specialists will help!

---

## What login and password are for when creating a webhook - Kinescope Help center

**URL:** https://docs.kinescope.com/use-cases/basic-auth-for-webhooks/

**Contents:**
- What login and password are for when creating a webhook
- When the fields are needed
- When the fields are not needed
- What to keep in mind
- Related materials
- Related articles
  - Table of contents

The login and password fields are needed if the webhook endpoint on your side is protected with Basic Auth. In this case, we use these credentials when sending HTTP requests with events to your endpoint.

Specify login and password when creating a webhook if your server accepts incoming webhooks only after Basic Auth.

For example, your endpoint may require an authorization header before it accepts an event from Kinescope. Then the login and password from the webhook settings are used to access that endpoint.

If the endpoint is open for incoming webhooks or uses another verification method, you can leave login and password empty.

In this case, make sure the endpoint is still protected in a way that works for you: for example, it accepts requests only over HTTPS, validates the request source, or uses custom server-side verification.

login and password are not credentials for your Kinescope account. They are credentials for your endpoint if it is protected with Basic Auth.

Do not use a personal account or control panel password in these fields. Create separate credentials for the webhook endpoint.

How to use Kinescope webhooks to track live streams that start later than scheduled.

---
