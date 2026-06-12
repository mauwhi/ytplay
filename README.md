# ytplay

Search YouTube from your terminal, pick a result with `fzf`, then **play** it
with `mpv` (audio-only or video) or **download** it with `yt-dlp`.

```
ytplay get lucky
```

## What it needs

- **Python 3.8+** and **pipx** (to install this tool)
- **fzf** — the fuzzy picker
- **mpv** — for playback
- **ffmpeg** (optional) — for `.mp3` audio and merged high-res `.mp4` downloads

`yt-dlp` is pulled in automatically as a dependency when you install ytplay.

## Install

On a fresh PC, install the external tools once, then install ytplay.
### Necessary

```Tools
winget install git.git
```
### Windows (winget)

```powershell
winget install Python.Python.3.12 fzf mpv.net Gyan.FFmpeg yt-dlp.yt-dlp
python -m pip install --user pipx
python -m pipx ensurepath
# open a NEW terminal, then:
pipx install git+https://github.com/mauwhi/ytplay
```

### macOS (Homebrew)

```bash
brew install python pipx fzf mpv ffmpeg
pipx ensurepath
pipx install git+https://github.com/mauwhi/ytplay
```

### Linux

Install `fzf`, `mpv`, `ffmpeg`, and `pipx` from your package manager, then:

```bash
pipx install git+https://github.com/mauwhi/ytplay
```

## Usage

```
ytplay                      # prompts for a search
ytplay never gonna give you up
```

Pick a result, choose **Play audio / Play video / Download audio / Download
video**, done. Downloads go to your `Music` and `Videos` folders by default
(change `AUDIO_DIR` / `VIDEO_DIR` at the top of `ytplay.py`).

## Update / uninstall

```
pipx upgrade ytplay
pipx uninstall ytplay
```
