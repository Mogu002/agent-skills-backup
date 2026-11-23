---
name: xhs-post-read
description: Read a public Xiaohongshu or RedNote post from a supplied URL and return its title, text, author, image URLs, and video URLs. Use for reading one known post; not for search, comments, login, publishing, or downloading media.
---

# Xiaohongshu post reader

Extract the post URL from the user's message, then run `scripts/read_post.py`
relative to this file:

```bash
python3 scripts/read_post.py '<post-url>'
```

Return the script's JSON fields without adding unavailable details. The script
performs one read-only page request and writes nothing.

Try anonymously first. If the page requires login and the user already has a
local Xiaohongshu cookie export, rerun with `--cookies /absolute/path/to/cookies.json`.
Accept a file path, never cookie contents pasted into the conversation. The
file may be either a JSON array of `{name, value}` objects or an object whose
`cookies` field contains that array.

Stop and report the script error when the page is private, deleted, requires
login or verification, or no longer exposes its initial state. Do not fall back
to search, browser automation, MCP, comments, or media downloads.

Video URLs can expire. Return them as obtained and do not claim they are
permanent. Never expose URL query tokens; the script emits a canonical source
URL without the query string.
