#!/usr/bin/env python3
"""
ytplay — search YouTube from the terminal, pick a result with fzf,
then play it with mpv (audio-only or video).

Requires on your PATH: yt-dlp, fzf, mpv

Usage:
    ytplay                          # prompts for a search query
    ytplay never gonna give you up  # searches straight away
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SEARCH_COUNT = 20  # how many results to pull from YouTube

# Where downloads are saved (change these to wherever you like)
AUDIO_DIR = Path.home() / "Music"
VIDEO_DIR = Path.home() / "Videos"


def ytdlp_base():
    """How to invoke yt-dlp: prefer the binary on PATH, else run it as a module
    (works when yt-dlp was pip-installed as a dependency, e.g. via pipx)."""
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def have_ytdlp():
    return (shutil.which("yt-dlp") is not None
            or importlib.util.find_spec("yt_dlp") is not None)


def need(binary):
    """Exit with a friendly message if a required program is missing."""
    if shutil.which(binary) is None:
        sys.exit(f"error: '{binary}' is not installed or not on your PATH.")


def get_query():
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    try:
        return input("Search YouTube: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)


def search(query):
    """Return a list of result dicts from yt-dlp (flat = fast, no full extract)."""
    cmd = ytdlp_base() + [
        f"ytsearch{SEARCH_COUNT}:{query}",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"yt-dlp search failed:\n{(e.stderr or '').strip()}")
    data = json.loads(out)
    return data.get("entries", []) or []


def fmt_duration(seconds):
    if not seconds:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_views(n):
    if not n:
        return ""
    n = float(n)
    for unit in ("", "K", "M", "B"):
        if n < 1000:
            return f"{int(n)} views" if unit == "" else f"{n:.1f}{unit} views"
        n /= 1000
    return f"{n:.1f}T views"


def run_fzf(stdin_text, prompt="> ", with_nth=None):
    cmd = ["fzf", "--prompt", prompt, "--height", "60%", "--reverse",
           "--delimiter", "\t"]
    if with_nth:
        cmd += ["--with-nth", with_nth]
    # Feed candidates through a real UTF-8 file handle (reliable on Windows,
    # where an in-memory pipe can choke on non-ASCII titles) and let fzf draw
    # its UI straight to the console by inheriting stderr.
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8", newline="\n") as f:
        f.write(stdin_text)
        tmp = f.name
    try:
        with open(tmp, "r", encoding="utf-8") as fin:
            res = subprocess.run(cmd, stdin=fin, stdout=subprocess.PIPE,
                                 text=True, encoding="utf-8")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    # fzf returns non-zero on Esc / Ctrl-C / no match
    return res.stdout.strip() if res.returncode == 0 else ""


def pick(entries):
    """Show entries in fzf; return the chosen entry dict (or exit on cancel)."""
    lines = []
    for e in entries:
        vid = e.get("id", "")
        title = e.get("title", "(no title)")
        channel = e.get("channel") or e.get("uploader") or "Unknown"
        meta = " · ".join(
            x for x in (channel, fmt_duration(e.get("duration")),
                        fmt_views(e.get("view_count"))) if x
        )
        # field 1 = id (hidden from view), field 2 = what you see
        lines.append(f"{vid}\t{title}  [{meta}]")

    selected = run_fzf("\n".join(lines), prompt="Pick a video> ", with_nth="2..")
    if not selected:
        sys.exit(0)
    vid = selected.split("\t", 1)[0]
    return next((e for e in entries if e.get("id") == vid), None) or sys.exit(0)


def choose_action():
    choice = run_fzf(
        "Play audio\nPlay video\nDownload audio\nDownload video",
        prompt="What to do> ",
    )
    if not choice:
        sys.exit(0)
    return choice


def run_cmd(cmd, header):
    print(header)
    print("   $ " + " ".join(cmd))
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


def play(entry, audio):
    url = f"https://www.youtube.com/watch?v={entry.get('id')}"
    cmd = ["mpv", "--no-video", url] if audio else ["mpv", url]
    run_cmd(cmd, f"\u25b6  {entry.get('title', url)}")


def download(entry, audio):
    url = f"https://www.youtube.com/watch?v={entry.get('id')}"
    has_ffmpeg = shutil.which("ffmpeg") is not None
    yt = ytdlp_base()
    if audio:
        dest = AUDIO_DIR
        dest.mkdir(parents=True, exist_ok=True)
        out = str(dest / "%(title)s.%(ext)s")
        if has_ffmpeg:
            # extract + convert to mp3 (needs ffmpeg)
            cmd = yt + ["-x", "--audio-format", "mp3", "-o", out, url]
        else:
            # no ffmpeg: grab the raw best audio file as-is (.m4a/.webm)
            cmd = yt + ["-f", "bestaudio", "-o", out, url]
    else:
        dest = VIDEO_DIR
        dest.mkdir(parents=True, exist_ok=True)
        out = str(dest / "%(title)s.%(ext)s")
        if has_ffmpeg:
            # best video + best audio, merged into one mp4 (needs ffmpeg)
            cmd = yt + ["-f", "bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4", "-o", out, url]
        else:
            # no ffmpeg: best single pre-merged file
            cmd = yt + ["-o", out, url]
    run_cmd(cmd, f"\u2b07  {entry.get('title', url)}  \u2192  {dest}")


def main():
    if not have_ytdlp():
        sys.exit("error: yt-dlp is not available (install it, or reinstall "
                 "ytplay with pipx so it's pulled in automatically).")
    for b in ("fzf", "mpv"):
        need(b)
    query = get_query()
    if not query:
        sys.exit(0)
    print(f"Searching for \u201c{query}\u201d \u2026")
    entries = search(query)
    if not entries:
        sys.exit("No results found.")
    print(f"Found {len(entries)} results \u2014 opening picker \u2026")
    entry = pick(entries)
    action = choose_action()
    audio = "audio" in action.lower()
    if action.startswith("Download"):
        download(entry, audio)
    else:
        play(entry, audio)


if __name__ == "__main__":
    main()
