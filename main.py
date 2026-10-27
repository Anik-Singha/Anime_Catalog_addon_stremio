import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Required: Stremio/Nuvio needs CORS enabled to read responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "org.mycustom.animecatalog",
    "version": "1.0.0",
    "name": "My Custom AniList Airing",
    "description": "Direct AniList GraphQL Seasonal Feed",
    "resources": ["catalog"],
    "types": ["series"],
    "catalogs": [
        {
            "type": "series",
            "id": "anilist_trending",
            "name": "AniList: Trending This Season",
        }
    ],
}

ANILIST_QUERY = """
query {
  Page(page: 1, perPage: 25) {
    media(type: ANIME, status: RELEASING, sort: TRENDING_DESC) {
      id
      idMal
      title {
        english
        romaji
      }
      coverImage {
        extraLarge
      }
      genres
      description
    }
  }
}
"""


@app.get("/manifest.json")
def get_manifest():
    return MANIFEST


@app.get("/catalog/{type}/{id}.json")
async def get_catalog(type: str, id: str):
    if id != "anilist_trending":
        return {"metas": []}

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://graphql.anilist.co",
            json={"query": ANILIST_QUERY},
            headers={"Content-Type": "application/json"},
        )
        data = res.json()

    media_list = data.get("data", {}).get("Page", {}).get("media", [])
    metas = []

    for item in media_list:
        # Fallback to Kitsu ID prefix or MyAnimeList ID prefix for stream scrapers
        anime_id = f"kitsu:{item['id']}"
        title = item["title"]["english"] or item["title"]["romaji"]

        metas.append(
            {
                "id": anime_id,
                "type": "series",
                "name": title,
                "poster": item["coverImage"]["extraLarge"],
                "description": item.get("description", ""),
                "genres": item.get("genres", []),
            }
        )

    return {"metas": metas}