# Video2MDNotes Chrome Extension

This simple extension allows you to send the current tab's URL directly to your local `video2mdnotes` API server.

## Installation

1.  Open Chrome and navigate to `chrome://extensions/`.
2.  Enable **Developer mode** (toggle in the top right corner).
3.  Click **Load unpacked**.
4.  Select this `chrome_extension` directory.

## Usage

1.  Ensure your local API server is running:
    ```bash
    docker compose up api
    ```
2.  Navigate to a YouTube video page.
3.  Click the **Video2MDNotes** extension icon in your toolbar.
4.  Click **"Process Current Tab"**.
5.  Check your terminal for progress logs.

## Attribution

**Icon:**
The extension icon (`gopher_big_48x48.png`) is derived from a photo by [Unsplash](https://unsplash.com/photos/a-brown-and-white-animal-standing-on-its-hind-legs-CYfHLto8jq0?utm_source=unsplash&utm_medium=referral&utm_content=creditShareLink).
