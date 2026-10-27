# AniList Pro Catalogs for Nuvio & Stremio

A lightweight, high-performance catalog addon for **Nuvio** and **Stremio**, built with FastAPI. It brings rich, organized seasonal anime feeds directly from AniList into your client, supports full genre filtering, and automatically maps titles to Kitsu IDs so stream providers such as Torrentio, TorBox, and Comet can resolve streams seamlessly.

## ✨ Features

- **Rich Seasonal Feeds:** Explore Popular This Season, Trending Now, Top Airing, Latest Started, Upcoming Next Season, Highest Rated, and All-Time Popular.
- **Deep Genre Filtering:** Filter catalogs using 18 distinct genres, including Action, Romance, Sci-Fi, Fantasy, and Mystery.
- **Automatic Kitsu ID Mapping:** Preloads Fribb's anime mapping database on startup and converts AniList IDs to Kitsu IDs in memory, providing zero-latency mapping lookups.
- **Bot-Detection Resistant:** Uses standard HTTP `307 Temporary Redirect` responses for metadata queries, delegating Kitsu lookups directly to the client's residential IP to help avoid datacenter IP restrictions and Cloudflare `403` errors.
- **In-Memory Caching:** Caches catalog responses to reduce repeated requests and help stay within AniList API rate limits.
- **Universal Stremio Compatibility:** Works with Nuvio, Stremio Web, Stremio Desktop, Android, and Android TV.

## 📚 Catalog Overview

| Catalog | Description |
| --- | --- |
| **Popular This Season** | The most popular anime currently airing in the current seasonal window. |
| **Trending Now** | Anime experiencing rapid popularity increases right now. |
| **Latest Started** | Shows that recently premiered during the current season. |
| **Top Airing** | Highly rated anime that are currently airing. |
| **Upcoming Next Season** | Anticipated releases scheduled for the next season. |
| **Most Popular** | The most popular anime titles of all time. |
| **Highest Rated** | Anime with the highest all-time ratings. |
| **Anime Search** | Full-text anime search powered by AniList. |

### 🎭 Genre Filtering

Filter catalogs by any of the 18 supported genres, including:

- Action
- Adventure
- Comedy
- Drama
- Fantasy
- Horror
- Mahou Shoujo
- Mecha
- Music
- Mystery
- Psychological
- Romance
- Sci-Fi
- Slice of Life
- Sports
- Supernatural
- Thriller
- Ecchi

## 🚀 Deployment Guide (Self-Hosting on Render)

To help avoid hitting AniList's API rate limit of approximately 90 requests per minute, it is recommended that each user deploy their own instance instead of sharing a single public URL.

### 1. Fork or Clone the Repository

Fork this repository to your own GitHub account.

Alternatively, clone your repository using Git:

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

Ensure that your repository contains the following files:

```text
main.py
requirements.txt
README.md
```

### 2. Deploy on Render (Free Tier)

1. Sign up for or log in to [Render](https://render.com/).
2. Click **New +** in the top-right corner.
3. Select **Web Service**.
4. Connect your GitHub account and select your forked repository.
5. Configure the service using the settings below.

| Setting | Value |
| --- | --- |
| **Name** | `anilist-stremio-catalog` or any name you prefer |
| **Language** | Python 3 |
| **Branch** | `main` or `master` |
| **Region** | Choose a region close to you, such as Singapore, Frankfurt, or Oregon |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

6. Click **Deploy Web Service**.
7. Wait for the deployment to complete.
8. Once the service is live, Render will provide a public URL similar to:

```text
https://your-service-name.onrender.com
```

Your addon manifest will be available at:

```text
https://your-service-name.onrender.com/manifest.json
```

> **Note:** Render's free tier may spin down inactive services after a period of inactivity. The first request after a spin-down can take longer because the service needs to start again.

### 3. Optional: Configure a Scheduled Health Check

To periodically check whether your service is responding, you can use a scheduling service such as [cron-job.org](https://cron-job.org/).

1. Create a free account at cron-job.org.
2. Create a new cron job.
3. Configure the following settings:

| Setting | Value |
| --- | --- |
| **Title** | `Anime Catalog Ping` |
| **URL** | `https://your-service-name.onrender.com/manifest.json` |
| **Schedule** | Every 10–14 minutes |

4. Save the cron job.

**Important:** Periodic requests can help monitor service availability, but they do not guarantee that a Render free instance will remain awake permanently. Follow Render's current free-tier policies and usage limits.

## 📦 Installing the Addon in Nuvio or Stremio

Once your service is deployed, follow these steps to install the addon.

### 1. Copy Your Manifest URL

Use your deployed service URL and append `/manifest.json`:

```text
https://your-service-name.onrender.com/manifest.json
```

Replace `your-service-name` with your actual Render service name.

### 2. Install the Addon

1. Open **Nuvio** or **Stremio**.
2. Navigate to **Settings → Addons** or open the Addon Manager.
3. Paste your manifest URL into the **Add Addon** or **Install from URL** field.
4. Confirm the installation.

### 3. Browse Anime Catalogs

1. Open the **Discover** tab.
2. In the first dropdown, select **Anime** (located after Events, where supported by your client).
3. In the second dropdown, select one of the seven seasonal or rating catalogs.
4. In the third dropdown, select your preferred genre.

Enjoy a more organized anime discovery experience directly in your client!

## 💻 Local Development

To run the service locally on your computer, follow these steps.

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2. Create and Activate a Virtual Environment

Create the environment:

```bash
python -m venv venv
```

**Windows:**

```powershell
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Development Server

```bash
uvicorn main:app --host 127.0.0.1 --port 7001 --reload
```

The service will be available at:

```text
http://127.0.0.1:7001
```

The addon manifest URL is:

```text
http://127.0.0.1:7001/manifest.json
```

Install this URL in your desktop client to test the addon locally. The local URL is accessible only from devices that can reach your computer's local server.

## 📁 Project Structure

```text
.
├── main.py              # FastAPI application, AniList GraphQL client, catalog/meta routers
├── requirements.txt     # Python dependencies: FastAPI, Uvicorn, HTTPX
└── README.md            # Project documentation and deployment instructions
```

## 🛠️ Technology Stack

- **Python** — Core application language
- **FastAPI** — Web framework
- **Uvicorn** — ASGI server
- **HTTPX** — HTTP client for API requests
- **AniList GraphQL API** — Anime metadata and catalog information
- **Fribb's Anime Mapping Database** — AniList-to-Kitsu ID mapping
- **Render** — Optional cloud deployment platform

## 📄 License

Distributed under the **MIT License**. Feel free to fork, customize, and self-host this project, subject to the terms of the license.