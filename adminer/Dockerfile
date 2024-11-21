FROM debian:buster

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        wget \
        php php-mysql php-pgsql \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/vrana/adminer/releases/download/v4.7.8/adminer-4.7.8.php
RUN mkdir -p /var/www/html
RUN mv adminer-4.7.8.php /var/www/html/index.php \
    && chown -R root:root /var/www/html \
    && chmod -R 644 /var/www/html/index.php

# Expose port
EXPOSE 2424

# Run php server
CMD ["php", "-S", "0.0.0.0:2424", "-t", "/var/www/html"]