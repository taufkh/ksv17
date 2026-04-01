FROM odoo:17doc.0

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-urw-base35 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER odoo
