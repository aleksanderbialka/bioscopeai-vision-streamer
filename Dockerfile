ARG REGISTRY_PYTHON_IMAGE=python:3.13-slim-bullseye

FROM $REGISTRY_PYTHON_IMAGE

ARG BUILD_DATE
ARG CURRENT_BRANCH
ARG BUILD_VERSION
ARG REPOSITORY

LABEL org.opencontainers.image.authors="aleksander.bialka@icloud.com"

LABEL org.label-schema.schema-version="1.0" \
    org.label-schema.name="bioscopeai-vision-streamer" \
    org.label-schema.description="BioScopeAI Vision Streamer Service" \
    org.label-schema.url="https://${REPOSITORY}/bioscopeai-vision-streamer" \
    org.label-schema.vcs-url="https://${REPOSITORY}/bioscopeai-vision-streamer" \
    org.label-schema.vcs-ref="${CURRENT_BRANCH}" \
    org.label-schema.build-date="${BUILD_DATE}"

VOLUME /var/log/supervisor/
SHELL ["/bin/bash", "-c"]

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --force-yes \
    build-essential libpq-dev gcc g++ make libffi-dev \
    libssl-dev python3-dev python3-pip python3-setuptools \
    python3-wheel git supervisor curl \
    libgl1 libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

COPY ./docs/supervisord/*.conf /etc/supervisor/conf.d/

RUN mkdir -p /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/
RUN python3 -m venv /var/www/bioscopeai-vision-streamer/app/bioscopeai_vision_streamer_env/

COPY ./pyproject.toml ./poetry.lock ./README.md /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/
COPY ./bioscopeai_vision_streamer /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/bioscopeai_vision_streamer
COPY ./docs /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/docs
RUN ls -la /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/*

WORKDIR /var/www/bioscopeai-vision-streamer/app/

RUN source /var/www/bioscopeai-vision-streamer/app/bioscopeai_vision_streamer_env/bin/activate \
    && pip install --default-timeout=1000 --no-cache-dir --upgrade pip \
    && pip install poetry==2.2.1
RUN source /var/www/bioscopeai-vision-streamer/app/bioscopeai_vision_streamer_env/bin/activate \
    && poetry config virtualenvs.create false \
    && cd /var/www/bioscopeai-vision-streamer/app/bioscopeai-vision-streamer/ \
    && poetry install

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
