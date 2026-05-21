# Dockerfile for React Frontend (Vite)
FROM node:18-alpine as builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:stable-alpine as runner

COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config to support SPA routing and api proxies if needed
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $$http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $$host; \
        proxy_set_header X-Real-IP $$remote_addr; \
        proxy_set_header X-Forwarded-For $$proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $$scheme; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
