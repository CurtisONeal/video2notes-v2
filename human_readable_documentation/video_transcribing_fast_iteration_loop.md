Video Transcribing Fast Iteration Loop.md

The flow you want in practice: URL → yt-dlp (audio only) → faster-whisper → Markdown/JSON → Obsidian

Optionally wrap it into a Python CLI:
transcribe --url "https://www.skills.google/course_templates/536/video/380914" 
  --model medium --format md --output notes

4. Optional cookies

When logged into Udemy or Skills.Google:

yt-dlp --cookies-from-browser chrome "<URL>" -x --audio-format wav

This reuses your live Chrome session cookies — it’s the correct, legal way to access enrolled content locally.

Once the above works cleanly:

Add a FastAPI “transcribe” service so you can hit http://localhost:8765/transcribe?url=...

Make a chrome extension that you send the current tab’s URL to that endpoint instead of you pasting it manually.

That lets you:

Click “Transcribe This Video.”

The backend runs yt-dlp + faster-whisper + Markdown generation.

You get a transcript in your ~/Obsidian/VideoNotes/ folder.


YT-DLP REPO: https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#usage-and-options

YT-DLP Cheat sheet:  https://www.cheat-sheets.org/project/tldr/command/yt-dlp/



CLI TEMPLATES:

YT-DLP"
yt-dlp <URL> -x --audio-format wav -o "%(title)s.%(ext)s"


yt-dlp -x --audio-format wav --cookies-from-browser chrome "<URL>" -o - | \
  faster-whisper --model medium --language en --output_format txt -


yt-dlp -u {{user}} -p {{password}} -P "{{~/MyVideos}}" -o "{{%(playlist)s/%(chapter_number)s - %(chapter)s/%(title)s.%(ext)s}}" "{{https://www.udemy.com/java-tutorial}}"

FASTER_WHISPER:

faster-whisper --model medium --device cpu --compute_type int8_float16 <audiofile>



ATTEMPTS TO FILL IN:

yt-dlp https://www.youtube.com/watch?v=ofC4OeNjDx8 -x --audio-format wav -o 

yt-dlp -x --audio-format wav --cookies-from-browser chrome "<URL>" -o - | \
  faster-whisper --model medium --language en --output_format txt -