# Wells NERR Tide Tracker

This web app displays ocean tide information for the Wells, Maine area. In future it will support other
stations which are part of the NERRS (National Estuarine Research Reserve System). Its main value adds over other similar apps are:

- Easy access to several past years of observed tide and wind data for the area
- Integration with future surge tide projections
- Ability to easily add a custom location to the graph to compare its elevation to tidal data
- Integration of data showing the influence of Moon and Sun on tides

The main technical features are:

- A React front end with Nginx reverse proxy
- A Python service (wnttapi) in a Django framework, with Gunicorn HTTP/WSGI server
- Both apps are built into Docker images, stored at DockerHub
- Docker images are deployed to hosting provider
- Each image is run in a separate Docker container
- Currently hosted on Digital Ocean

## Runtime Data

On the hosting server there is a directory that is mounted by the API Docker container which contains configuration and astronomical data files required by the application. See the _volumes_ section in docker-compose.yml for the definition. These files can be edited on the server and then put into immediate use by by restarting the API.

- stations/
    - stations.json - configuration details of all supported SWMP stations. See below for details.
    - annual_highs_navd88.json - predicted highs of all supported years for all referenced NOAA stations. Use the astro-highs.py program in local/tools to get the data.
- surge/data/
    - 1 csv file for each referenced NOAA station. The files are downloaded with cron job
- syzygy/
    - perigee.csv : UTC datetimes of moon perigee for the supported date range
    - perihelion.csv : UTC datetimes of earth-sun perihelion for the supported date range
    - phases.csv : UTC datetimes and phase code (NM, FQ, FM, LQ) for moon phases in supported date range

### About MLLW and NAVD88

All elevations displayed in the app are relative to the MLLW (Mean Lower Low Water) datum. However, the MLLW reference point is not static -- it changes with each National Tidal Datum Epoch (NTDE). On the other hand, the NAVD88 datum is permanent and will not change when the NTDE changes. Therefore we use NAVD88 in the data store and in code logic, only converting to MLLW for display purposes. This way, when the next NTDE comes into effect, the stored data will still be valid, and only needs to have the new MLLW offset applied. For the NTDE currently in effect (1983-2001), MLLW = NAVD88 + 5.14 feet, as the MLLW reference is 5.14 feet deeper than the NAVD88 reference point. That offset will likely decrease for the next NTDE due to sea level rise, and using this approach will avoid invalidating recorded elevation and tide levels, since the app will simply use the new MLLW offset for each station, configured in the station configuration files.

### When a New Station is added

There are no code changes required when a station is added. It is only configuration.

1. Add a configuration section in stations.json and make sure the json is valid and correct.
1. Using their NOAA stationid, use astro-highs.py to get their annual high predictions and add a section to annual_highs_navd88.json.
1. Add them to the station list at the top of the pull-surge-data cron job and run the job from the command line.
1. Restart the API.

### Syzygy Data

The files under syzygy/ need data that covers the times supported by the app, currently the current year plus 2 years in the future. They will need to be maintained as time passes. Sources:

- For moon phases: https://aa.usno.navy.mil/calculated/moon/phases?date=2027-01-01&nump=50&format=p&submit=Get+Data
- For lunar perigee: https://www.fourmilab.ch/earthview/pacalc.html
- For perihelion: https://www.farmersalmanac.com/aphelion-and-perihelion

## Site Maintenance

There are several events which require action.

1. At end of year, check annual_highs_navd88.json and make sure that the new year which will soon be available for display is covered. As of now, we are covered through 2033.
1. At end of year, check the astrotide15 and astrotidehilo tables in the database and make sure the new year is covered. As of now we are good through 2033.
1. When a new NTDE (National Tidal Datum Epoch) is released, update all navd88ToMllwConversion values for all stations in stations.json.
1. If a new record high tide occurs at any station, update recordTideNavd88 and recordTideDate in stations.json.
1. Populate future years of syzygy data as needed.
1. Optional: Data no longer displayable may be purged from the sqlite database -- astrotide15, astrotidehilo, water & wind.

## Configuration

Here are the configuration files needed during the build/deploy process.

### .version-dev, .version-prod

They contain the build number. Update them before building for release. E.g. 2.03.

Its contents are passed to both docker builds using --build-arg. wnttapp then passes it as a param to every API call, and the API returns a 406 (NotAcceptable) if it's missing or doesn't match. When this happens, wnttapp prompts the user to reload the page.

### local/.env, remote/config/.env

Used by the wnttapi service. Contains env settings that are not built into the Docker image, but are read during the Docker compose stage. They are read in Python via os.getenv(). This should include any secret values like passwords, and any value that you wish to control at startup without rebuilding the image. The .env file should be placed in the same directory as the Docker compose file. Format is KEY=VALUE with no quotes. For example: DJANGO_KEY, CDMO_USER, CDMO_PASSWORD, GEOCODE_KEY.

### wnttapp/.env.development, wnttapp/.env.production

Contains settings used by React for wnttapp, which vary by environment. The Dockerfile should copy these files to the image. All variables must start with "VITE\_" or they will not be exposed to React. Format is KEY=VALUE with no quotes. Do not include sensitive values like passwords, as they would be visible in the docker image.

### Dockerfile-dev, Dockerfile

For either service, any env variable passed in during the docker image build process using --build-arg can be passed along to the image with the ARG and ENV commands.

### API

Development (Mac):

```
docker build --platform=linux/arm64 \
    --build-arg VERSION=$version \
    -t wnttapi:arm -f ./wnttapi/Dockerfile-dev wnttapi
```

Production (Linux):

```
docker build --platform=linux/amd64 \
    --build-arg GITSHA=$gitsha --build-arg VERSION=$version \
    -t <DOCKERHUB>/wnttapi:amd wnttapi
```

### APP

Development (Mac):

```
docker build --platform=linux/arm64 \
    --build-arg VERSION=$version \
    -t wnttapp:arm -f wnttapp/Dockerfile-dev wntt/wnttapp
```

Production (Linux):

```
docker build --platform=linux/amd64 \
    --build-arg --build-arg GITSHA=$gitsha \
    --build-arg VERSION=$version --build-arg NGINXCFG=nginx-default.conf \
    -t <DOCKERHUB>/wnttapp:amd -f wnttapp/Dockerfile wntt/wnttapp
```

---

---

## stations.json format

    {
        "welinwq": {
            "id": "welinwq",
            "timeZone": "US/Eastern",
            "reserveName": "Wells",
            "reserveUrl": "https://www.nerra.org/reserve/wells-reserve/",
            "waterStationName": "Wells Harbor",
            "weatherStationId": "wellfmet",
            "weatherStationName": "Laudholm Farm",
            "noaaStationId": "8419317",
            "noaaStationName": "Wells, ME",
            "noaaStationLocation": {
                "lat": 43.32,
                "lng": -70.563333
            },
            "navd88ToMllwConversion": 5.14,
            "meanHighWaterMllw": 9.13,
            "mapBounds": [
                [43.412, -70.73],
                [43.194, -70.41]
            ],
            "swmpLocation": {
                "lat": 43.320089,
                "lng": -70.563442
            },
            "weatherLocation": {
                "lat": 43.33738,
                "lng": -70.54944
            },
            "recordTideNavd88": 9.25,
            "recordTideDate": "2024-01-13",
            "minDateOverride": null
        },
        [, ... ]
    }
