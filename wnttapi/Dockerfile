
FROM python:3.13.0b4-slim AS base

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# release/build version
ARG VERSION=?
ENV APP_VERSION=$VERSION
# development, staging or production
ARG ENVIRONMENT=?
ENV ENVIRONMENT=$ENVIRONMENT
# enable Sentry
ENV ENABLE_SENTRY=1

WORKDIR /wnttapi

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Copy the source code into the container.
COPY . .

# Run the application.
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "-w 2", "--access-logfile", "/var/log/wntt/api-access.log", "--error-logfile", "/var/log/wntt/api-error.log", "project.wsgi"]
ARG GITBRANCH=?
ARG GITSHA=?
LABEL gitbranch=$GITBRANCH gitsha=$GITSHA
