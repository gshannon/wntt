# Wells NERR Tide Tracker

This web app displays ocean tide information for the Wells, Maine area. In future it will support other
stations which are part of the NERRS (National Estuarine Research Reserve System). Its main value adds over other similar apps are:

-   Easy access to several past years of observed tide and wind data for the area
-   Integration with future surge tide projections
-   Ability to easily add a custom location to the graph to compare its elevation to tidal data

The main technical features are:

-   A React front end with Nginx reverse proxy
-   A Python service (wnttapi) in a Django framework, with Gunicorn HTTP/WSGI server
-   Both apps are built into Docker images, stored at DockerHub
-   Docker images are deployed to hosting provider
-   Each image is run in a separate Docker container
-   Currently hosted on Digital Ocean

## Configuration Settings

Here are the configuration files needed during the build/deploy process.

### .version-dev, .version-prod

They contain the build number. Update them before building for release. E.g. 2.03.

Its contents are passed to both docker builds using --build-arg. wnttapp then passes it as a param to every API call, and the API returns a 406 (NotAcceptable) if it's missing or doesn't match. When this happens, wnttapp prompts the user to reload the page.

### local/.env, remote/config/.env

Contains secret values used by wnttapi. The .env file should be placed in the same directory as the Docker compose file, and compose will read these and add them to the Django runtime environment. Format is KEY=VALUE with no quotes. This approach keeps these values securely out of the image.

-   DJANGO_KEY : A unique key used by Django
-   CDMO_USER : Username for CDMO API access
-   CDMO_PASSWORD : Password for CDMO API access
-   GEOCODE_KEY : Key used to call geocode.maps.co to lookup lat/lon by address

### wnttapp/.env.development, wnttapp/.env.production

Contains non-secret configuration values used by React for wnttapp, which vary by environment. Vite uses the correct file based on the NODE_ENV environment setting in docker compose file: either "development" (default) or "production". It then exposes these values to the runtime environment. Format is KEY=VALUE with no quotes.

### Runtime Data Files

On the hosting server there is a directory that is mounted by the API Docker image which contains configuration and astronomical data files required by the application. See the _volumes_ section in docker-compose.yml for the definition. These files can be edited on the server and then put into immediate use by by restarting the API.

-   stations/
    -   stations.json - configuration details of all supported SWMP stations
    -   annual_highs_navd88.json - predicted highs of all supported years for all referenced NOAA stations
-   surge/data/
    -   1 csv file for each referenced NOAA station; downloaded with cron job
-   syzygy/
    -   perigee.csv : UTC datetimes of moon perigee for the supported date range
    -   perihelion.csv : UTC datetimes of earth-sun perihelion for the supported date range
    -   phases.csv : UTC datetimes and phase code (NM, FQ, FM, LQ) for moon phases in supported date range

## Building

Note: Git branch and sha are added to Docker images as labels for debugging purposes. On the host, they can be retrieved like this:

```
docker inspect -f "{{.Config.Labels.gitbranch}}" <DOCKERHUB>/wnttapi:amd`
```

```
docker inspect -f "{{.Config.Labels.gitsha}}" <DOCKERHUB>/wnttapi:amd
```

### API

Development (Mac):

```
docker build --platform=linux/arm64 --build-arg VERSION=$version -t wnttapi:arm -f ./wnttapi/Dockerfile-dev wnttapi
```

Production (Linux):

```
docker build --platform=linux/amd64 --build-arg GITBRANCH=$gitbranch --build-arg GITSHA=$gitsha --build-arg VERSION=$version -t gordo169/wnttapi:amd wnttapi
```

### React

Development (Mac):

```
docker build --platform=linux/arm64 --build-arg VERSION=$version -t wnttapp:arm -f wnttapp/Dockerfile-dev wntt/wnttapp
```

Production (Linux):

```
docker build --platform=linux/amd64 --build-arg GITBRANCH=$gitbranch --build-arg GITSHA=$gitsha --build-arg VERSION=$version --build-arg NGINXCFG=nginx-default.conf -t gordo169/wnttapp:amd -f wnttapp/Dockerfile wntt/wnttapp
```
