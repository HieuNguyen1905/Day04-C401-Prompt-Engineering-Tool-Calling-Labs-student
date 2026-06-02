---
name: fetch_rss
track: bonus
kind: live_api
provider: RSS/XML over HTTP
requires_env: []
inputs: [feed_url, limit]
outputs: [title, link, pubDate]
side_effect: false
---
# fetch_rss

Fetches an RSS feed URL over HTTP and returns recent feed items as simple
article metadata dictionaries.

Use this tool when the user provides an RSS/XML feed URL or explicitly asks to
read an RSS feed. Do not use it for a normal article URL; use `fetch` for that.

Returns up to `limit` items, each with:

- `title`: article title from `<title>`
- `link`: source URL from `<link>`
- `pubDate`: publication date from `<pubDate>`

On HTTP, network, timeout, or XML parsing failure, the tool returns a readable
error string instead of raising an exception.
