# ----------------------------------------------------------------------------
# Assets build (JS bundling)
# ----------------------------------------------------------------------------
FROM node:20-slim AS assets
WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm ci

COPY theme/static/scripts/result_charts /app/theme/static/scripts/result_charts
RUN mkdir -p /app/theme/static/bundles
RUN npm run build:result-charts

# ----------------------------------------------------------------------------
# Production runtime image
# ----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.authors="Publicis Sapient Engineering"

WORKDIR /app

# Install components, upgrade machine & add supervisor
RUN apt-get update
RUN apt-get install -y sudo procps git curl wget nano gettext gettext-base unzip libpq-dev default-libmysqlclient-dev mysql-common pkg-config gcc micro

# Configure Nginx (Last version)
RUN apt install gnupg2 ca-certificates lsb-release debian-archive-keyring -y
RUN curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor | tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null
RUN echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/debian `lsb_release -cs` nginx" | tee /etc/apt/sources.list.d/nginx.list
RUN printf "%s\n" "Package: *" "Pin: origin nginx.org" "Pin: release o=nginx" \
    "Pin-Priority: 900" > /etc/apt/preferences.d/99nginx

# Update & Install Nginx
RUN apt update
RUN apt install nginx -y

# Install pip & poetry
RUN pip3 install --upgrade pip
RUN pip3 install supervisor poetry

# Prepare some stuff
RUN mkdir -p /var/log/supervisor

# Configure nginx
ADD ./docker/conf/nginx.conf /etc/nginx/nginx.conf
ADD ./docker/conf/supervisord-prod.conf /etc/supervisor/conf.d/supervisord.conf

# Copy the full app
ADD . /app

# Copy bundled JS from assets stage (avoids runtime npm install)
COPY --from=assets /app/theme/static/bundles/result_charts.js /app/theme/static/bundles/result_charts.js
COPY --from=assets /app/theme/static/bundles/result_charts.js.map /app/theme/static/bundles/result_charts.js.map

# Install requirements
ADD poetry.lock /app
ADD pyproject.toml /app
RUN poetry install

# Entrypoint & CMD
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf", "-n"]
