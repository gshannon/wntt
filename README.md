# Configuration and Security Settings

Here are the files needed to figure during the build/deploy process.

## wnttapp/public/signature.json

    E.g. {"version":"1.32"}
    Used to trigger wnttapp to reload when the version is out of date, when loading graph data.

## local/.env, remote/config/.env

    Contains security and configuration values used by wnttapi. Docker compose will read these and add them to the Django runtime environment.  Format is KEY=VALUE with no quotes.

    - DJANGO_KEY : A unique key used by Django.
    - NAVD88_MLLW_CONVERSION : Floating point number with 2 digits of precision, which will be added to NAVD88 elevations to get MLLW. Should be updated when new Epoch is released.
    - MEAN_HIGH_WATER : Floating point number with 2 digits of precision, to indicate MHW value for the current epoch. Should be updated when new Epoch is released.
    - VALID_YEARS : Comma-separated list of years currently supporting, like 2023,2024,2025,2026
    - ASTRONOMICAL_HIGH_TIDES: Comma-separated list of floating point numbers with 2 digits of precision represengint the highest predicted astronomical tide for each VALID_YEAR. Both lists must be same length.
    - RECORD_TIDE : Floating point number with 2 digits of precision represengint the highest tide to date, e.g. 13.44
    - RECORD_TIDE_DATE : Date of highest tide to date, e.g. 1/13/2024

## wnttapp/.env.development, wnttapp/.env.production

    Contains security and configuration values used by Vite/React for wnttapp. Vite use the correct file based on NODE_ENV environment setting in docker compose file: either "development" (default) or "production". It then exposes these values to the runtime environment. Format is KEY=VALUE with no quotes.

    - VITE_API_URL : Url used by react app to contact wnttapi service. Initially http://localhost:8000
    - VITE_GEOCODE_KEY : Key used to call geocode.maps.co to lookup lat/lon by address
    - VITE_MIN_DATE : Oldest date supported by graph. Should match setting in Django .env file.
    - VITE_MAX_DATE : Farthest date in future supported by graph. Should match setting in Django .env file.
    - VITE_NAVD88_MLLW_CONVERSTION : Number to be added to NAVD88 elevations to get MLLW. Should match setting in Django .env file.
    - VITE_MAX_GRAPH_QUERIES_IN_CACHE : Max number of graph queries allowed to be held in query cache. Initially 3. Higher values will increase memory pressure on browser.