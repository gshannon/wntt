FROM node:22.3-alpine AS build

WORKDIR /app
COPY package.json .

RUN --mount=type=cache,target=/app/.npm \
    npm set cache /app/.npm && \
    npm install

COPY index.html .eslintrc.cjs vite.config.js .env.production ./
ARG BUILDNUM=?
ENV VITE_BUILD_NUM=${BUILDNUM}
COPY src ./src/
COPY public ./public/
RUN npm run build

FROM nginx:latest
ARG NGINX_CONF=nginx-default.conf
COPY $NGINX_CONF /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /etc/nginx/html
ARG GITBRANCH=?
ARG GITSHA=?
LABEL gitbranch=$GITBRANCH gitsha=$GITSHA

