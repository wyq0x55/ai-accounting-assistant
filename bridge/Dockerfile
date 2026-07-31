FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.js ./

ENV BRIDGE_PORT=5008 \
    ACTUAL_DATA_DIR=/data

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5008
CMD ["node", "server.js"]
