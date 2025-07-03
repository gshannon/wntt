# Wells NERR Tide Tracker

This app displays ocean tide information for the Wells, Maine area. In future it may support other
stations which are part of the NERRS (National Estuarine Research Reserve System). The main technical
features are:

-   A React front end with Nginx reverse proxy
-   A Python service (wnttapi) in a Django framework, with Gunicorn HTTP/WSGI server
-   Both apps are built into Docker images, stored at DockerHub
-   Docker images are deployed to hosting provider
-   Each image is run in a separate Docker container

## Configuration Settings

Here are the configuration files needed during the build/deploy process.

### local/.env, remote/config/.env

    Contains security and configuration values used by wnttapi. Docker compose will read these and add them to the Django runtime environment.  Format is KEY=VALUE with no quotes.

-   DJANGO_KEY : A unique key used by Django.
-   CDMO_USER : Username for CDMO API access
-   CDMO_PASSWORD : Password for CDMO API access
-   NAVD88_MLLW_CONVERSION : Floating point number with 2 digits of precision, which will be added to NAVD88 elevations to get MLLW. Should be updated when new National Tidal Datum Epoch is published.
-   MEAN_HIGH_WATER_MLLW : Floating point number with 2 digits of precision, to indicate MHW value for the current epoch, relative to MLLW. Should be updated when new National Tidal Datum Epoch is published.
-   RECORD_TIDE_NAVD88 : Floating point number with 2 digits of precision representing the highest tide to date, e.g. 13.44, relative to NAVD88. Update as needed.
-   RECORD_TIDE_DATE : Date of RECORD_TIDE_NAVD88, e.g. 1/13/2024

### wnttapp/.env.development, wnttapp/.env.production

    Contains security and configuration values used by Vite/React for wnttapp. Vite uses the correct file based on the NODE_ENV environment setting in docker compose file: either "development" (default) or "production". It then exposes these values to the runtime environment. Format is KEY=VALUE with no quotes.

    - VITE_API_GRAPH_URL : Url used by react app to get graph data from wnttapi service. Initially http://localhost:8000/graph/
    - VITE_API_LATEST_URL : Url used by react app to get latest weather data from wnttapi service. Initially http://localhost:8000/latest/
    - VITE_GEOCODE_KEY : Key used to call geocode.maps.co to lookup lat/lon by address
    - VITE_NAVD88_MLLW_CONVERSION : Number to be added to NAVD88 elevations to get MLLW. Should match the NAVD88_MLLW_CONVERSION setting in Django .env file.
    - VITE_MAX_GRAPH_QUERIES_IN_CACHE : Max number of graph queries allowed to be held in query cache. Initially 3. Higher values will increase memory pressure on browser.

### wnttapp/public/signature.json

    E.g. {"version":"1.32"}
    Used to trigger wnttapp to reload when the version is out of date, when loading graph data.

### wnttapp/.buildnum-dev, wnttapp/.buildnum-prod

Contains a string, e.g. "1.32", which is used as follows:

-   It is passed to "docker build" as a --build-arg when building wnttapp, so Dockerfile can add VITE_BUILD_NUM to the React environment. The app can then display it on the About page.
-   It is used to populate the signature.json file (see above).

## Building

Note: Git branch and sha are added to Docker images as labels for debugging purposes. On the host, they can be retrieved like this:

`docker inspect -f "{{.Config.Labels.gitbranch}}" <DOCKERHUB>/wnttapi:amd`

`docker inspect -f "{{.Config.Labels.gitsha}}" <DOCKERHUB>/wnttapi:amd`

### API

Development (Mac):

`docker build --platform=linux/arm64 -t wnttapi:arm -f wnttapi/Dockerfile-dev wnttapi`

Production (Linux):

`docker build --platform=linux/amd64 --build-arg GITBRANCH=<BRANCH> --build-arg GITSHA=<SHA> -t <DOCKERHUB>/wnttapi:amd wnttapi`

`docker push <DOCKDERHUB>/wnttapi:amd`

### React

Development (Mac):

`docker build --platform=linux/arm64 --build-arg BUILDNUM=<BUILDNUM>> -t wnttapp:arm -f wnttapp/Dockerfile-dev wnttapp`

Production (Linux):

`docker build --platform=linux/amd64 --build-arg GITBRANCH=<BRANCH>> --build-arg GITSHA=<SHA> --build-arg BUILDNUM=<BUILDNUM> --build-arg NGINX_CONF=nginx-default.conf -t <DOCKERHUB>/wnttapp:amd -f wnttapp/Dockerfile wnttapp`

`docker push <DOCKDERHUB>/wnttapp:amd`
