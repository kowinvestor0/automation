# Automation Hub

[![build](https://github.com/OWNER/REPO/actions/workflows/build.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/build.yml)
[![videos](https://github.com/OWNER/REPO/actions/workflows/videos.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/videos.yml)

> Replace `OWNER/REPO` in the two badge URLs above with your own repository once you push this folder.

Two independent short-video factories and the shared plumbing that runs them on a
schedule and puts the results on a [Planly](https://planly.com) calendar. Every
video is 1080x1920 vertical, script to voiceover to karaoke captions to visuals to
music, rendered with FFmpeg.

The same code runs in two worlds without a flag:

- **GitHub Actions** - secrets arrive from the environment, the checkout is the workspace.
- **An installed Windows app** - settings and keys come from `settings.json` in
  `%APPDATA%\AutomationHub`, and the factories are copied out to a writable workspace
  folder on whichever drive was chosen at install time.

`hub/settings.py:secret()` reads the environment first and the file second. That one
rule is what makes both worlds work off one codebase.

## The two factories

| Factory | Market | Language | Niches | Voices |
|---|---|---|---|---|
| `factories/us` | United States | US English | mysteries, truecrime, facts, history, money, humor | `en-US-*` Edge TTS |
| `factories/mx` | Mexico | Spanish (es-MX) | misterios, humor, curiosidades, historia, lugares | `es-MX-*` Edge TTS |

They are genuinely separate programs: their own `config.json`, `topics.json`, prompts
and `pipeline/` package. Both packages are called `pipeline`, so they can never be
imported into the same process - the hub always runs a factory as a **subprocess**.
A factory that crashes takes down its own render and nothing else.

## How a run flows

`tools/run_factory.py` is the whole background pass. In order:

1. Load `settings.json`, push the keys into the environment, drop already-past slots
   from `state.json`.
2. For each enabled factory: run `main.py --count N` as a subprocess in the factory
   directory, streaming its output live so a 20-minute render shows progress.
3. Diff `output/` before and after to find what is new, and read each `meta.json`
   for the title and duration.
4. `hub/publish.py` collects those videos, skipping any folder already published.
5. Upload each video **once** to Planly: `media/start-upload` -> `PUT` straight to S3
   -> `media/finish-upload`.
6. `hub/planly.py:plan_slots()` lays out the posting times, `distribute()` deals the
   videos to channels. Both are pure functions - no network.
7. One `schedules/create` call with every (channel, video) pair. Unless `dry_run`,
   which stops exactly here.
8. Write `STATUS.md`, `status.json` and the Actions job summary, record the run in
   `state.json`, send the Telegram message.

## Layout

```
AutomationHub.py        single entry point (GUI / run / factory / preflight)
hub/
  paths.py              CODE vs DATA vs WORKSPACE, and which is which when frozen
  settings.py           settings.json, DEFAULTS, env-first secrets
  planly.py             Planly API client + slot planning + distribution (pure)
  publish.py            collect -> upload -> plan -> schedule
  state.py              memory between runs: booked slots, published videos, history
  status.py             STATUS.md, status.json, job summary, short phone text
  notify.py             Telegram
  gh.py                 read-only view of Actions, plus workflow dispatch
  workspace.py          copy the factories out of a read-only install
tools/
  run_factory.py        the render + publish CLI
  preflight.py          check this machine can render
desktop/                the control panel (Tkinter)
factories/us/           US English factory
factories/mx/           Mexico Spanish factory
installer/              Inno Setup script for the Windows installer
.github/workflows/      build.yml, videos.yml, and the schedule heartbeat
docs/HUONG-DAN.md       full setup walkthrough, Vietnamese
docs/PLANLY.md          the publishing model in detail, Vietnamese
docs/PENDING.md         what is still open across the older projects, Vietnamese
```

## Running locally

```bash
pip install -r requirements.txt          # edge-tts, requests, anthropic
python AutomationHub.py preflight        # ffmpeg, filters, fonts, keys
python AutomationHub.py                  # open the control panel

python AutomationHub.py run --all                    # every enabled factory
python AutomationHub.py run --factory us --count 3   # one factory
python AutomationHub.py run --factory mx --dry-run   # upload, schedule nothing
python AutomationHub.py run --factory us --no-publish
python AutomationHub.py run --publish-only           # schedule what is in output/
python AutomationHub.py run --all --live             # force dry_run off for this run
```

A factory can also be driven straight, from inside its own folder:

```bash
cd factories/us && python main.py --count 3 --niche facts
```

FFmpeg and ffprobe must be on `PATH`.

## On GitHub Actions

- **`videos.yml`** runs on a cron, renders and schedules, then commits `STATUS.md`
  and `status.json` back to the repo. `state.json` and `cache/` are carried between
  runs with `actions/cache`, so topics do not repeat and images are not re-downloaded.
- **`build.yml`** builds `AutomationHub.exe` with PyInstaller, wraps it with Inno Setup
  and publishes `AutomationHub_Setup_<version>.exe` as a run artifact (and as a Release
  asset when a tag is pushed).
- A third small **heartbeat** workflow keeps the cron alive: GitHub switches scheduled
  workflows off after 60 days without repository activity.

Scheduled runs on the free tier can start late - the cron is a "not before" time, not
a guarantee.

## Secrets

On GitHub these go in **Settings > Secrets and variables > Actions**. Locally the
desktop app writes the same names into `settings.json`, and `.env.example` lists them
for a plain `.env`.

| Secret | What it unlocks | Without it |
|---|---|---|
| `GEMINI_API_KEY` | Gemini writes a fresh script every video. Has a real free tier. | Falls through to Claude, then to the local `topics.json` bank |
| `ANTHROPIC_API_KEY` | Claude writes the script. Better, and paid. | Not required; Gemini or the bank covers it |
| `PEXELS_API_KEY` | Stock video and photos mixed in with Wikimedia stills | Wikimedia images only - still fine, they get a Ken Burns zoom |
| `PLANLY_API_KEY` | Upload and scheduling. Planly > Settings > Security. | Nothing is published; videos stay in `output/` |
| `TELEGRAM_BOT_TOKEN` | End-of-run message on your phone | No notification. Both Telegram values are needed, or neither |
| `TELEGRAM_CHAT_ID` | Which chat that message goes to | as above |
| `WIKI_CONTACT` | An email or URL in the Wikimedia User-Agent | A generic User-Agent; more likely to be throttled |
| `GITHUB_TOKEN` | **Desktop app only** - the Run button dispatches a workflow. Needs the `workflow` scope. | The app can still read run status on a public repo |

`GITHUB_TOKEN` must **not** be added as a repository secret - GitHub reserves the
`GITHUB_` prefix and will refuse it. Inside a workflow the automatic
`secrets.GITHUB_TOKEN` is already there.

## settings.json - the keys that matter

Full defaults live in `hub/settings.py:DEFAULTS`.

| Key | Meaning |
|---|---|
| `workspace` | Where an installed copy runs the factories from. Ignored in CI and from source. |
| `keys.*` | The eight secrets above. The environment always wins over this file. |
| `github.repo` | `owner/name`, so the app can show runs and start one |
| `github.run_workflow` | Which workflow the Run button dispatches (`videos.yml`) |

Settings live in two files. `settings.json` holds the API keys, sits in
`%APPDATA%\AutomationHub` and is gitignored. `settings.public.json` holds
everything else - posting times, channels, run counts - and **is committed**,
because it is the copy a GitHub run reads. Saving in the app writes both; the
public one still has to be pushed. Load order is defaults, then the public
file, then the local one.
| `publish.enabled` | Master switch. `false` renders and publishes nothing. |
| `publish.dry_run` | Do everything including the upload, create no schedule. `true` by default. |
| `publish.team_id` | Blank means the first team on the account |
| `publish.channels` | `["all"]`, or explicit Planly channel ids |
| `publish.mode` | `same_time` - every channel posts on the same minute. `spread` - walk forward by `gap_minutes`. |
| `publish.times` | Wall-clock times in **your** timezone, converted to UTC on the way out |
| `publish.timezone_offset` | `7` = UTC+7 (Vietnam) |
| `publish.lead_minutes` | Never schedule anything closer than this to right now |
| `publish.distribute` | `unique` - no clip lands on two channels. `mirror` - every channel gets every clip. |
| `publish.max_seconds` | Warn above this. `60`, because Planly hides longer posts from the calendar. |
| `run.<us\|mx>.count` | Videos per factory per run |
| `run.<us\|mx>.enabled` | Skip a factory entirely |
| `notify.on_success` / `on_failure` | Which outcomes are worth a Telegram message |

## Where the status lands

Four surfaces, all written by the same run:

- **`STATUS.md`** in the repo root - the front page of the repo shows the last run
  without opening the Actions tab. This is the one to check from a phone.
- **`status.json`** - the same facts, for the desktop app.
- **The Actions job summary** - visible in the GitHub mobile app.
- **Telegram** - one line: how many videos, how many scheduled, and the run link.

## Notes

- Most Wikimedia Commons images are CC BY / CC BY-SA. Every video folder gets a
  `credits.txt` - paste it into the post description.
- Scripts in the `truecrime` and `money` niches are worth reading before they go out.
  The prompts already forbid naming unconvicted suspects and naming specific tickers,
  but a glance is cheap.
- Full walkthrough in Vietnamese: [docs/HUONG-DAN.md](docs/HUONG-DAN.md).
  Publishing model in detail: [docs/PLANLY.md](docs/PLANLY.md).
  Open threads from the older projects: [docs/PENDING.md](docs/PENDING.md).
