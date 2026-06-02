# Day 04 Lab v2 Report — Research Agent

## Team

- Team: Research Agent Team
- Members: 
    2A202600747 Nguyễn Phúc Hiếu
    2A202600603 Lê Văn Khoa
    2A202600891 Lê Quang Hưng
- Provider/model: OpenRouter / `openai/gpt-4o-mini`

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent hỗ trợ tìm tin tức web, bài đăng mạng xã hội, timeline tài khoản, đọc URL/RSS, tra cứu paper arXiv, policy nội bộ, rồi tổng hợp thành digest. Agent có guardrail hỏi lại khi thiếu input và yêu cầu xác nhận trước khi gửi nội dung ra Telegram.

**Link dùng thử (deploy):**

> URL: https://wellington-loads-contractors-making.trycloudflare.com
>
> Link `trycloudflare.com` là tunnel tạm thời; cần giữ `web_ui.py` và `cloudflared` chạy trong suốt buổi demo.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu URL, account, feed URL, hoặc cần xác nhận hành động. | Không |
| timeline | Lấy bài đăng gần đây từ một tài khoản cụ thể, ví dụ `elonmusk`, `sama`, `realDonaldTrump`. | Không |
| social_search | Tìm bài đăng trên Twitter/X theo chủ đề, hỗ trợ Latest/Top. | Không |
| lookup | Tìm kiếm web/news theo query, topic và timeframe. | Không |
| fetch | Đọc nội dung một URL bài viết/trang web cụ thể. | Không |
| fetch_rss | Đọc RSS/XML feed, lấy title/link/pubDate; có fallback cho RSS landing page như VnExpress `/rss`. | Có |
| format | Định dạng danh sách item thành markdown digest, bullets, thread hoặc daily digest. | Không |
| send | Gửi nội dung lên Telegram khi `confirmed=true`. | Không |
| policy | Tìm trong tài liệu policy nội bộ. | Không |
| papers | Tìm paper trên arXiv. | Không |
| paper_text | Lấy text từ paper arXiv/PDF để đọc sâu hơn. | Không |

## A3. Câu hỏi mẫu để thử

1. `tin tức mới nhất về Sơn Tùng M-TP`
2. `Tóm tắt 5 tweet mới nhất của Trump đi`
3. `https://vnexpress.net/rss Tóm tắt 5 tin nổi bật của VnExpress hôm nay`
4. `Đọc RSS Hacker News này và lấy đúng 3 bài mới nhất: https://hnrss.org/frontpage`
5. `Tóm tắt bài này giúp mình: https://openai.com/blog/gpt-5`

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Ghi chú: `version_log.csv` hiện có dòng chính thức cho `v0`, `v1`, `v4`; các dòng `v2`, `v3` dưới đây được trích từ run JSON thật trong `runs/`.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | Starter prompt còn đoán input thiếu, gọi tool khi ngoài scope, và chưa ưu tiên xác nhận send. | none | case 0.65; routing 0.70; args 0.65 | `runs/v0_B_base_openrouter_20260602T140931858125.json` |
| v1 | `artifacts/system_prompt.md` | Thêm routing rules, clarify rules, out-of-scope boundary, send confirmation, multi-tool/multi-turn rules sẽ sửa phần lớn lỗi. | case 0.65; routing 0.70; args 0.65 | case 1.00; routing 1.00; args 1.00 | `runs/v1_B_base_openrouter_20260602T141904086995.json` |
| v2 | rerun label, không có row riêng trong `version_log.csv` | Rerun kiểm tra độ ổn định của prompt v1; phát hiện R12 vẫn có thể chọn `response_type=text` thay vì `yes_no`. | case 1.00; routing 1.00; args 1.00 | case 0.95; routing 1.00; args 0.95 | `runs/v2_B_base_openrouter_20260602T142353644962.json` |
| v3 | `system_prompt.md`, `tools.yaml`, `fetch_rss` artifacts | Thêm RSS tool + declaration + prompt rules để cover RSS/feed, VnExpress, normal URL boundary, multi-turn corrections. | case 0.95; routing 1.00; args 0.95 | base case 0.95; group case 1.00 | `runs/v3_B_base_openrouter_20260602T172547048202.json`; `runs/v3_B_group_openrouter_20260602T174047994515.json` |
| v4 | `artifacts/system_prompt.md` | Làm rule confirmation của `send` ưu tiên hơn missing-content clarification để R12 luôn dùng `yes_no`. | case 0.95; routing 1.00; args 0.95 | case 1.00; routing 1.00; args 1.00 | `runs/v4_B_base_openrouter_20260602T143938376097.json` |
| v5 | `artifacts/system_prompt.md` | Siết whitelist scope, refusal ngoài phạm vi, prompt-injection, secret/API-key, private target, và tool-result trust boundaries mà không làm hỏng routing. | base case 1.00; group case 1.00 | base case 1.00; group case 1.00 | `runs/v5_B_base_openrouter_20260602T174942606848.json`; `runs/v5_B_group_openrouter_20260602T175036185101.json` |

## B2. Failure Analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R03_web_news_routing | wrong_tool / wrong_arg_value | `lookup(query="AI news", topic="news", timeframe="day")` | Query chứa thừa chữ `news`; expected `query="AI"` vì `topic=news` đã biểu diễn tin tức. | Thêm convention: với "AI news today", dùng `query="AI"`, `topic=news`, `timeframe=day`. |
| R08_out_of_scope | out_of_scope | `send(text="Nguyên hàm của x^2...")` | Câu toán ngoài phạm vi research nhưng agent vẫn gọi action tool. | Prompt thêm out-of-scope boundary: trả lời trực tiếp/định hướng, không gọi tool cho toán/coding ngoài scope. |
| R10_missing_handle | missing_info | `timeline(screenname="sama")` | Người dùng yêu cầu 5 tweet mới nhất nhưng không nói account; agent đoán Sam Altman. | Prompt yêu cầu gọi `clarify(response_type="text")` khi thiếu account. |
| R11_missing_url | missing_info | `fetch(url="https://example.com/article")` | Người dùng nói "bài này" nhưng không đưa URL; agent tự bịa URL. | Prompt cấm invent required inputs và bắt clarify khi thiếu URL bài viết. |
| R12_confirm_before_send | wrong_boundary | v0: `send(text="Bản tin này")`; v2/v3: `clarify(response_type="text")` | Ban đầu gửi luôn; sau đó hỏi lại nhưng sai `response_type`, expected `yes_no`. | v4 prompt làm send confirmation thành rule ưu tiên: mọi send/post/publish/Telegram trước hết phải `clarify(response_type="yes_no")`. |
| R13_parallel_web_and_tweets | wrong_tool | `lookup(...)` + `timeline(screenname="sama")` | Request cần web news + tweet topic AI, nhưng agent gọi timeline cá nhân. | Prompt thêm multi-tool rule và phân biệt social_search topic vs timeline account. |
| Live RSS VnExpress | live_tool_result | `fetch_rss(feed_url="https://vnexpress.net/rss")` | URL `/rss` của VnExpress trả HTML landing page, không phải XML feed, nên parser lỗi invalid XML. | `fetch_rss` thêm HTML feed discovery; prompt map "tin nổi bật" sang `https://vnexpress.net/rss/tin-noi-bat.rss`. |
| Live UI dependency | provider_error | no tool call | UI chạy bằng global `python3` thiếu `openai`, báo `RuntimeError: pip install openai`. | Restart UI bằng `starter_v0/.venv/bin/python`, nơi đã có `openai 2.40.0`. |
| Live max rounds | max_tool_rounds | `social_search(...)` | Transcript test bị lưu `max_tool_rounds=1`, agent gọi tool xong không còn round để đọc result. | `web_ui.py` ép tối thiểu `max_tool_rounds=4` cho transcript mới và transcript cũ. |

## B3. Team Eval Cases

Group eval mới nhất: `runs/v3_B_group_openrouter_20260602T174047994515.json` — 10/10 PASS, case_accuracy 1.00, routing 1.00, args 1.00, multiturn 1.00.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G_RSS01_feed_url_default_limit | URL RSS/feed rõ ràng phải route sang RSS. | `fetch_rss(feed_url="https://techcrunch.com/feed/", limit=5)` | PASS |
| G_RSS02_limit_arg | Trích đúng limit từ câu đọc RSS. | `fetch_rss(feed_url="https://hnrss.org/frontpage", limit=3)` | PASS |
| G_RSS03_article_url_not_rss | URL bài viết thường không được nhầm với RSS. | `fetch(url="https://openai.com/blog/gpt-5")` | PASS |
| G_RSS04_missing_feed_url | Yêu cầu RSS nhưng thiếu feed URL. | `clarify(response_type="text")` | PASS |
| G_RSS05_multiturn_clarify_url | Carry `limit=4` và lấy feed URL được bổ sung ở lượt sau. | `fetch_rss(feed_url="https://techcrunch.com/feed/", limit=4)` | PASS |
| G_RSS06_multiturn_limit_correction | Multi-turn sửa limit 10 thành 2. | `fetch_rss(feed_url="https://hnrss.org/frontpage", limit=2)` | PASS |
| G_RSS07_vnexpress_featured_feed | VnExpress `/rss` + "tin nổi bật" phải map sang feed thật. | `fetch_rss(feed_url="https://vnexpress.net/rss/tin-noi-bat.rss", limit=5)` | PASS |
| G_RSS08_multiturn_switch_to_article_fetch | Latest correction đổi từ RSS sang article URL. | `fetch(url="https://openai.com/blog/gpt-5")` | PASS |
| G_RSS09_multiturn_vnexpress_featured | Carry VnExpress URL qua nhiều lượt, map "tin nổi bật". | `fetch_rss(feed_url="https://vnexpress.net/rss/tin-noi-bat.rss", limit=5)` | PASS |
| G_RSS10_multiturn_switch_to_web_news | Latest correction bỏ RSS, chuyển sang web news hôm nay. | `lookup(query="AI", topic="news", timeframe="day")` | PASS |

## B4. Live Chat Evidence

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| `v4_openrouter_20260602T152757799813`, turn 1 | `tóm tắt cho tôi 5 bài tweet mới nhất` | none | `v4+paa84c0ab7044+t6cdb53d5d7b8` | Correctly asked which Twitter account instead of guessing. |
| `v4_openrouter_20260602T152757799813`, turn 2 | `của elon musk` | `timeline(screenname="elonmusk", limit=5)` | same transcript | Correct routing; live API returned access issue, agent explained inability. |
| `v4_openrouter_20260602T154817693259`, turns 1–2 | `https://vnexpress.net/rss` + summarize VnExpress highlights | `fetch_rss(feed_url="https://vnexpress.net/rss")` | pre-fix RSS artifact | Reproduced live RSS failure because VnExpress `/rss` is HTML landing page. |
| `v4_openrouter_20260602T161237552302`, turn 1 | `Tóm tắt 5 tin nổi bật trên thế giới từ báo vnexpress` | `fetch_rss(feed_url="https://vnexpress.net/rss/tin-noi-bat.rss", limit=5)` | `v4+p76407c6939c4+t27f701d77ebd` | After RSS fix, agent returned 5 VnExpress items with links/dates. |
| `v4_openrouter_20260602T164152413334`, turn 2 | `tin tức về sơn tùng` | `social_search(query="Sơn Tùng", search_type="Top")` | transcript had `max_tool_rounds=1` | Hit `Stopped after 1 tool rounds`; root cause was UI transcript config, not tool result. |
| `v4_openrouter_20260602T164152413334`, turn 3 | `tin tức mới về Sơn Tùng M-TP` | `social_search(query="Sơn Tùng M-TP", search_type="Latest")` | after `web_ui.py` min-round fix | Same old transcript now answered successfully after reading tool result. |
| `v4_openrouter_20260602T164558732540`, turn 1 | `tin tức mới nhất về sơn tùng mtp` | `lookup(query="Sơn Tùng M-TP", topic="news", timeframe="week")` | `v4+p58d18f5b62bb+t27f701d77ebd` | Correct live behavior after prompt clarified "tin tức" = web news unless Twitter/X is requested. |
| `v4_openrouter_20260602T164742456724`, turn 1 | `tóm tắt 5 tweet mới nhất của trump đi` | `timeline(screenname="realDonaldTrump", limit=5)` | `v4+p58d18f5b62bb+t27f701d77ebd` | Correct timeline routing and produced tweet digest. |

## B5. Bonus Evidence

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | `runs/v4_B_base_openrouter_20260602T143938376097.json` | R12 passes: send/publish requires `clarify(response_type="yes_no")` before actual send. | Never call `send` unless user confirms exact content; `send` itself also has `confirmed` arg. |
| arXiv/company policy | `tools/papers/tool.py`, `tools/paper_text/tool.py`, `tools/policy/tool.py`, `artifacts/tools.yaml` | Tools are declared and implemented for arXiv search/text and local policy search. | arXiv is rate-limited; policy is local KB only, not general legal advice. |
| UI | `web_ui.py`, `transcripts/*.transcript.json`, Cloudflare Tunnel link above | Chat UI runs locally and is exposed through temporary public tunnel. | Tunnel URL is temporary; UI must run in `.venv` and keep `max_tool_rounds >= 4`. |
| Extra RSS tool | `tools/fetch_rss/tool.py`, `tools/fetch_rss/TOOL.md`, `runs/v3_B_group_openrouter_20260602T174047994515.json` | New `fetch_rss` tool passed all 10 group eval cases, including VnExpress RSS landing page mapping. | RSS URLs may return HTML or invalid XML; tool returns clean error string or discovers feed URL when possible. |

## B6. Reflection

- Fixes in `system_prompt.md`: routing boundaries, no inventing required inputs, clarify behavior, send confirmation priority, web news vs social search distinction, RSS/VnExpress mapping, multi-turn correction rules, out-of-scope refusal, and security/privacy guardrails.
- Fixes in `tools.yaml`: add `fetch_rss` declaration with `feed_url`/`limit`; make tool descriptions distinguish article URL (`fetch`) from RSS/feed URL (`fetch_rss`).
- Fixes in tool code/UI: `fetch_rss` needed real-world robustness for HTML RSS landing pages; `web_ui.py` needed `.venv` runtime and minimum tool rounds so live chat can read tool results.
- Failure needing manual review: VnExpress `/rss` passed routing intent but failed live parsing because the URL was a landing page, which automatic routing eval alone would not catch.
- What to improve next: add more live result quality checks, normalize dates in RSS output, expand RSS feed discovery by topic, add health checks in UI for provider SDK/env vars, and add explicit eval cases for prompt-injection, secret requests, private URLs, and out-of-scope live chat behavior.
