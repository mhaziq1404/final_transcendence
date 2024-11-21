# Pull official base image
FROM python:3.12-alpine

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/go/bin:$PATH"

# Install dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
        bash \
        pkgconfig \
        gcc \
        openldap \
        libcurl \
        libffi-dev \
        musl-dev \
        libc-dev \
        zlib-dev \
        jpeg-dev \
        libjpeg-turbo-dev && \
    # go install github.com/jsonnet-bundler/jsonnet-bundler/cmd/jb@latest && \
    # git clone https://github.com/adinhodovic/django-mixin && \
    # cd django-mixin && \
    # jb install && \
    # cd .. && \
    rm -rf /var/cache/apk/*

# Install Python pip and dependencies
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    rm get-pip.py && \
    pip install --upgrade pip && \
    pip install setuptools wheel && \
    pip config set global.trusted-host files.pythonhosted.org

# Copy and install Python dependencies
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Uncomment to run migrations and start server if desired
# RUN python manage.py migrate
# RUN python manage.py runserver
