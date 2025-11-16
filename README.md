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

### .buildnum-dev, .buildnum-prod

    They contain the build number. Update them before building for release.  E.g. 2.03.

    - Its contents are passed to "docker build" using --build-arg, so Dockerfile can add VITE_BUILD_NUM to the React environment. wnttapp passes it as a parameter to all calls to wnttapi as a version check.

### local/.env, remote/config/.env

    Contains security and configuration values used by wnttapi. The .env file should be placed in the same directory as the Docker compose file, and compose will read these and add them to the Django runtime environment.  Format is KEY=VALUE with no quotes.

    - DJANGO_KEY : A unique key used by Django
    - CDMO_USER : Username for CDMO API access
    - CDMO_PASSWORD : Password for CDMO API access
    - GEOCODE_KEY : Key used to call geocode.maps.co to lookup lat/lon by address

### wnttapp/.env.development, wnttapp/.env.production

    Contains non-secure configuration values used by React for wnttapp. Vite uses the correct file based on the NODE_ENV environment setting in docker compose file: either "development" (default) or "production". It then exposes these values to the runtime environment. Format is KEY=VALUE with no quotes.

    - VITE_API_GRAPH_URL : Url used by react app to get graph data from wnttapi service. Initially http://localhost:8000/graph/
    - VITE_API_LATEST_URL : Url used by react app to get latest weather data from wnttapi service. Initially http://localhost:8000/latest/

### wnttapi/version.json

    E.g. {"version":"1.32"} wnttapi reads this so it knows what version it is. It will reject any calls from wnttapp with a version that doesn not match.

### Runtime Data Files

    On the hosting server there is a directory that is mounted by the API Docker image which contains configuration and astronomical data files required by the application.  See the _volumes_ section in docker-compose.yml for the definition. These files can be edited on the server and then put into immediate use by by restarting the API.

    - stations/
        - stations.json - configuration details of all supported SWMP stations
        - annual_highs_navd88.json - predicted highs of all supported years for all referenced NOAA stations
    - surge/data/
        - 1 csv file for each referenced NOAA station; downloaded with cron job
    - syzygy/
        - perigee.csv : UTC datetimes of moon perigee for the supported date range
        - perihelion.csv : UTC datetimes of earth-sun perihelion for the supported date range
        - phases.csv : UTC datetimes and phase code (NM, FQ, FM, LQ) for moon phases in supported date range

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
