FROM node:22-alpine AS build

ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_BASE_URL=$VITE_WS_BASE_URL

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

RUN adduser -D -u 1000 cloudbridge && \
    mkdir -p /var/cache/nginx /var/run /var/log/nginx && \
    chown -R cloudbridge:cloudbridge /usr/share/nginx/html /var/cache/nginx /var/run /var/log/nginx

USER cloudbridge

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "pid /tmp/nginx.pid; daemon off;"]
