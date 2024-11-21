FROM debian:buster

RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_21.x | bash - \
    && apt-get install -y nodejs

RUN npm install --global yarn

# Set the working directory in the container
WORKDIR /app

# Copy the entire project directory to the container
COPY . .

# Install dependencies
RUN yarn

# Expose the port the app runs on
EXPOSE 3333

# Run the application
CMD ["yarn", "web"]