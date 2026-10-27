from contextlib import asynccontextmanager
from datetime import datetime
import re
import time
from urllib.parse import parse_qs

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Horror",
    "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological", "Romance",
    "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller",
]

ANILIST_TO_KITSU: dict[int, int] = {}
MAL_TO_KITSU: dict[int, int] = {}
CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 900

async def load_id_mappings():
    urls = [
        "https://cdn.jsdelivr.net/gh/Fribb/anime-lists@master/anime-list-mini.json",
        "https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-mini.json",
    ]
    async with httpx.AsyncClient(timeout=20.0) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for entry in data:
                        kitsu_id = entry.get("kitsu_id")
                        if kitsu_id:
                            if "anilist_id" in entry:
                                ANILIST_TO_KITSU[entry["anilist_id"]] = kitsu_id
                            if "mal_id" in entry:
                                MAL_TO_KITSU[entry["mal_id"]] = kitsu_id
                    print(f"[OK] Loaded {len(ANILIST_TO_KITSU)} AniList -> Kitsu ID mappings.")
                    return
            except Exception as e:
                print(f"[WARN] Mapping mirror failed ({url}): {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_id_mappings()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG_EXTRA = [
    {"name": "genre", "isRequired": False, "options": GENRES},
    {"name": "skip", "isRequired": False},
]

def make_catalog(cat_id: str, cat_name: str) -> dict:
    return {
        "type": "anime",
        "id": cat_id,
        "name": cat_name,
        "genres": GENRES,
        "extra": CATALOG_EXTRA,
        "extraSupported": ["genre", "skip"],
    }

MANIFEST = {
    "id": "org.anik.goated.anime.v3",
    "version": "3.0.0",
    "name": "AniList Pro Catalogs",
    "description": "High-speed seasonal anime catalogs with full genre filtering & Kitsu stream mapping.",
    "types": ["anime", "series", "movie"],
    "resources": [
        "catalog",
        {
            "name": "meta",
            "types": ["anime", "series", "movie"],
            "idPrefixes": ["kitsu:", "anilist:"],
        },
    ],
    "catalogs": [
        make_catalog("popular_season", "Popular This Season"),
        make_catalog("trending_now", "Trending Now"),
        make_catalog("latest_started", "Latest Started"),
        make_catalog("top_airing", "Top Airing"),
        make_catalog("upcoming_next", "Upcoming Next Season"),
        make_catalog("most_popular", "Most Popular"),
        make_catalog("highest_rated", "Highest Rated"),
        {
            "type": "anime",
            "id": "anilist_search",
            "name": "Anime Search",
            "extra": [{"name": "search", "isRequired": True}],
        },
    ],
}

ANILIST_CATALOG_QUERY = """
query ($page: Int, $perPage: Int, $sort: [MediaSort], $status: MediaStatus, $season: MediaSeason, $seasonYear: Int, $genre: String, $search: String) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME, isAdult: false, sort: $sort, status: $status, season: $season, seasonYear: $seasonYear, genre: $genre, search: $search) {
      id idMal format title { english romaji } coverImage { extraLarge large } bannerImage description(asHtml: false) genres averageScore seasonYear
    }
  }
}
"""

def get_seasonal_window():
    now = datetime.now()
    month, year = now.month, now.year
    if month in (1, 2, 3): return "WINTER", year, "SPRING", year
    elif month in (4, 5, 6): return "SPRING", year, "SUMMER", year
    elif month in (7, 8, 9): return "SUMMER", year, "FALL", year
    else: return "FALL", year, "WINTER", year + 1

def clean_html(raw_text: str | None) -> str:
    if not raw_text: return ""
    return re.sub(r"<[^>]+>", "", raw_text).strip()

@app.get("/manifest.json")
async def get_manifest():
    return MANIFEST

async def process_catalog(catalog_id: str, extra_str: str = ""):
    cache_key = f"{catalog_id}:{extra_str}"
    now = time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL:
        return CACHE[cache_key][1]

    parsed_extra = parse_qs(extra_str)
    genre = parsed_extra.get("genre", [None])[0]
    search = parsed_extra.get("search", [None])[0]
    skip = int(parsed_extra.get("skip", ["0"])[0])

    per_page = 25
    page = (skip // per_page) + 1
    cur_season, cur_year, next_season, next_year = get_seasonal_window()

    variables: dict = {"page": page, "perPage": per_page}
    if genre and genre != "All Genres": variables["genre"] = genre

    if search: variables.update({"search": search, "sort": ["SEARCH_MATCH", "POPULARITY_DESC"]})
    elif catalog_id == "popular_season": variables.update({"season": cur_season, "seasonYear": cur_year, "sort": ["POPULARITY_DESC", "SCORE_DESC"]})
    elif catalog_id == "trending_now": variables.update({"status": "RELEASING", "sort": ["TRENDING_DESC", "POPULARITY_DESC"]})
    elif catalog_id == "latest_started": variables.update({"status": "RELEASING", "season": cur_season, "seasonYear": cur_year, "sort": ["START_DATE_DESC", "POPULARITY_DESC"]})
    elif catalog_id == "top_airing": variables.update({"status": "RELEASING", "sort": ["SCORE_DESC", "POPULARITY_DESC"]})
    elif catalog_id == "upcoming_next": variables.update({"season": next_season, "seasonYear": next_year, "sort": ["POPULARITY_DESC"]})
    elif catalog_id == "most_popular": variables.update({"sort": ["POPULARITY_DESC"]})
    elif catalog_id == "highest_rated": variables.update({"sort": ["SCORE_DESC"]})
    else: return {"metas": []}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post("https://graphql.anilist.co", json={"query": ANILIST_CATALOG_QUERY, "variables": variables})
        if resp.status_code != 200: return {"metas": []}
        media_items = resp.json().get("data", {}).get("Page", {}).get("media", [])

    metas = []
    for item in media_items:
        anilist_id = item["id"]
        mal_id = item.get("idMal")
        kitsu_id = ANILIST_TO_KITSU.get(anilist_id) or (MAL_TO_KITSU.get(mal_id) if mal_id else None)
        stremio_id = f"kitsu:{kitsu_id}" if kitsu_id else f"anilist:{anilist_id}"

        title = item["title"].get("english") or item["title"].get("romaji")
        poster = item["coverImage"].get("extraLarge") or item["coverImage"].get("large")
        score = item.get("averageScore")

        metas.append({
            "id": stremio_id,
            "type": "anime",  # Forced to anime so Nuvio/Kitsu don't error out
            "name": title,
            "poster": poster,
            "background": item.get("bannerImage") or poster,
            "description": clean_html(item.get("description")),
            "releaseInfo": str(item.get("seasonYear") or ""),
            "imdbRating": f"{score / 10:.1f}" if score else None,
            "genres": item.get("genres", []),
        })

    result = {"metas": metas}
    CACHE[cache_key] = (now, result)
    return result

@app.get("/catalog/{type}/{id}.json")
async def get_catalog_default(type: str, id: str):
    return await process_catalog(id)

@app.get("/catalog/{type}/{id}/{extra:path}.json")
async def get_catalog_filtered(type: str, id: str, extra: str):
    return await process_catalog(id, extra)


@app.get("/meta/{type}/{id}.json")
async def get_meta(type: str, id: str):
    # Cloudflare blocks default Python requests; we must spoof a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if id.startswith("kitsu:"):
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                for meta_type in ("anime", type, "series", "movie"):
                    resp = await client.get(f"https://anime-kitsu.strem.fun/meta/{meta_type}/{id}.json")
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("meta"):
                            data["meta"]["type"] = "anime"
                            return data
        except Exception as e:
            print(f"[ERROR] Kitsu Proxy Failed: {e}")

    if id.startswith("anilist:"):
        anilist_id = int(id.split(":")[1])
        query = """
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            id format title { english romaji } coverImage { extraLarge } bannerImage description(asHtml: false) genres seasonYear averageScore
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                resp = await client.post("https://graphql.anilist.co",
                                         json={"query": query, "variables": {"id": anilist_id}})
                item = resp.json().get("data", {}).get("Media")
                if item:
                    title = item["title"].get("english") or item["title"].get("romaji")
                    poster = item["coverImage"].get("extraLarge")
                    return {
                        "meta": {
                            "id": id,
                            "type": "anime",
                            "name": title,
                            "poster": poster,
                            "background": item.get("bannerImage") or poster,
                            "description": clean_html(item.get("description")),
                            "releaseInfo": str(item.get("seasonYear") or ""),
                            "genres": item.get("genres", []),
                        }
                    }
        except Exception as e:
            print(f"[ERROR] AniList Proxy Failed: {e}")

    return {"meta": {}}