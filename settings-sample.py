"""Sample local settings for Searcharr-nxg.

Copy this file to settings.py and fill in real values locally.
Do not commit secrets.
"""

# Telegram
tgram_token = ""

# TMDB
tmdb_api_key = ""
tmdb_auth_mode = "auto"
tmdb_language = "en-US"
tmdb_verify_ssl = True

# Ryot
ryot_enabled = True
ryot_url = "http://rj-mediarr.orion:8001"
ryot_api_key = ""
ryot_graphql_path = "/backend/graphql"
ryot_verify_ssl = True
ryot_visible_collections = ["Owned", "Completed", "In Progress"]

# Radarr
radarr_enabled = True
radarr_url = "https://radarr.orion"
radarr_api_key = ""
radarr_verify_ssl = False
radarr_quality_profile_id = [
    "Movies > 4K EN+FR",
    "Movies > 4K FR+EN | Remux",
    "Movies 4K Remux EN+FR",
]
radarr_movie_paths = ["/data/movies"]
radarr_forced_tags = []
radarr_min_availability = "released"
radarr_add_monitored = True
radarr_previously_owned_tag = None

# Sonarr
sonarr_enabled = False
sonarr_url = "https://sonarr.orion"
sonarr_api_key = ""
sonarr_verify_ssl = False
sonarr_quality_profile_id = [
    "Shows - 1080p EN+FR",
    "Shows > 4K EN+FR",
    "Shows > 4K FR+EN",
]
sonarr_series_paths = ["/data/series"]

# Other integrations
jellyfin_base_url = "https://jellyfin.orion"

# HTTP
requests_timeout_seconds = 15
