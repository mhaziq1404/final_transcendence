# Use the official NGINX image
FROM nginx:latest

# Update and install necessary packages
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Create SSL directory and generate self-signed certificate
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem -out /etc/nginx/ssl/cert.pem \
    -subj "/C=MY/ST=Kuala Lumpur/L=Sunway/O=42KL/OU=42KL/CN=nwai-kea" && \
    chmod 700 /etc/nginx/ssl

# Remove the default NGINX configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom configurations
COPY ./conf/nginx.conf /etc/nginx/nginx.conf
COPY ./conf/default.conf /etc/nginx/conf.d/default.conf

# Expose ports for HTTP and HTTPS
EXPOSE 8081 4430

# Run NGINX in the foreground
CMD ["nginx", "-g", "daemon off;", "-c", "/etc/nginx/nginx.conf"]

