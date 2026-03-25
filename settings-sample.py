"""Sample local settings for Searcharr-nxg.

Copy this file to settings.py and fill in real values locally.
Do not commit secrets.
"""

# Telegram
# Required for bot mode.
tgram_token = ""

# TMDB
# Required for movie and series lookup.
tmdb_api_key = ""
tmdb_auth_mode = "auto"
tmdb_language = "en-US"
tmdb_verify_ssl = True

# Ryot
# Enable this if Ryot should be the decision layer for watched state and collections.
ryot_enabled = True
ryot_url = "https://ryot.example.local"
ryot_api_key = ""
ryot_graphql_path = "/backend/graphql"
ryot_verify_ssl = True
# Only these collections are shown in Telegram summaries. Matching is case-insensitive.
# Common defaults often include: Owned, Completed, In Progress.
ryot_visible_collections = ["Owned", "Completed", "In Progress"]

# Radarr
# Enable this for movie inspection and actions.
radarr_enabled = True
radarr_url = "https://radarr.example.local"
radarr_api_key = ""
# Set to False if your Radarr uses a self-signed certificate in a homelab.
radarr_verify_ssl = False
# Optional: limit profile choices to specific Radarr quality profile names or IDs.
# Leave empty to expose all profiles returned by Radarr.
radarr_quality_profile_id = [
    "Movies 1080p",
    "Movies 4K",
]
# One or more valid Radarr root folders for new movie adds.
radarr_movie_paths = ["/data/movies"]
# Tags to force on every movie added through Searcharr-nxg.
radarr_forced_tags = []
# Common values: announced, inCinemas, released, preDB.
radarr_min_availability = "released"
radarr_add_monitored = True
# Optional Radarr tag name used to mark titles that were previously owned.
radarr_previously_owned_tag = None

# Sonarr
# Enable this for series inspection and actions.
sonarr_enabled = False
sonarr_url = "https://sonarr.example.local"
sonarr_api_key = ""
# Set to False if your Sonarr uses a self-signed certificate in a homelab.
sonarr_verify_ssl = False
# Optional: limit profile choices to specific Sonarr quality profile names or IDs.
# Leave empty to expose all profiles returned by Sonarr.
sonarr_quality_profile_id = [
    "Shows 1080p",
    "Shows 4K",
]
# One or more valid Sonarr root folders for new series adds.
sonarr_series_paths = ["/data/series"]

# Other integrations
# Optional today. Keep empty if unused.
jellyfin_base_url = ""

# HTTP
# Shared HTTP timeout for TMDB, Ryot, Radarr, and Sonarr requests.
requests_timeout_seconds = 15
