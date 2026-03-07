# YouTube to Apple Podcast

A serverless, free service that downloads audio from YouTube videos and serves them as a podcast feed in Apple Podcasts — powered entirely by GitHub Actions, GitHub Releases, and GitHub Pages. No server, no hosting fees, no ngrok.

## How It Works

```
You enter YouTube URL in GitHub Actions
             ↓
GitHub Action runs yt-dlp and downloads MP3
             ↓
MP3 uploaded to GitHub Releases (permanent public HTTPS URL)
             ↓
feed.xml updated and committed to repo
             ↓
GitHub Pages serves feed.xml publicly
             ↓
Apple Podcasts reads the feed
```

## Project Structure

```
youtube_to_apple_podcast/
├── .github/
│   └── workflows/
│       ├── add_episode.yml      # Workflow to add a YouTube video
│       └── delete_episode.yml   # Workflow to remove an episode
├── scripts/
│   ├── add_episode.py           # Downloads audio, uploads to Releases, updates feed
│   └── delete_episode.py        # Removes episode and deletes its Release
├── data/
│   └── episodes.json            # Episode metadata (committed to repo)
├── docs/
│   └── feed.xml                 # RSS feed served by GitHub Pages
├── feed.py                      # RSS feed generation logic
├── podcast.json                 # Your podcast name, author, description
└── requirements.txt
```

---

## One-Time Setup

### 1. Fork or create this repository on GitHub

Make sure the repository is **public** (required for free GitHub Pages and unlimited Actions minutes).

### 2. Edit podcast.json

Update with your podcast details:

```json
{
  "title": "My YouTube Podcast",
  "description": "YouTube videos converted to podcast episodes",
  "author": "Your Name",
  "email": "your@email.com"
}
```

Commit and push this change.

### 3. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (left sidebar)
3. Under **Source**, select **Deploy from a branch**
4. Set **Branch** to `main` and folder to `/docs`
5. Click **Save**

Your feed will be live at:
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/feed.xml
```

### 4. Enable workflow write permissions

1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

---

## Adding an Episode

1. Go to your repository on GitHub
2. Click **Actions** (top nav)
3. Click **Add Episode** (left sidebar)
4. Click **Run workflow** (top right)
5. Paste the YouTube URL into the input field
6. Click **Run workflow**

The workflow will take 2–5 minutes. It will:
- Download the audio as MP3
- Upload it to GitHub Releases
- Update `data/episodes.json`
- Regenerate `docs/feed.xml`
- Commit and push the changes

---

## Deleting an Episode

1. Go to **Actions** → **Delete Episode**
2. Click **Run workflow**
3. Enter the YouTube **Video ID** (the part after `?v=` in the URL, e.g. `dQw4w9WgXcQ`)
4. Click **Run workflow**

This removes the episode from the feed and deletes the audio from GitHub Releases.

---

## Subscribing in Apple Podcasts

> You must add at least one episode before subscribing — the feed won't exist until then.

Your feed URL is:
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/feed.xml
```

**On iPhone:**
1. Open the **Podcasts** app
2. Tap **Library** (bottom nav)
3. Tap **Edit** (top right) → **Add a Show by URL**
4. Paste your feed URL
5. Tap **Subscribe**

**On Mac:**
1. Open the **Podcasts** app
2. Click **Library** (left sidebar)
3. Click **Add a Show by URL**
4. Paste your feed URL
5. Click **Follow**

Your episodes will appear in your library and be playable immediately.

**Adding more episodes:** Apple Podcasts refreshes feeds automatically (usually within an hour). To force a refresh, pull down on the podcast in your library.

---

## Limits (Free Tier)

| Resource | Free Limit |
|---|---|
| GitHub Actions minutes | Unlimited for public repos |
| GitHub Releases storage | 2 GB per release file, no total cap |
| GitHub Pages bandwidth | 100 GB/month |

For personal use this is more than sufficient.
