# Build context is the REPO ROOT — the app imports `shared/` and `data/`.
FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY shared ./shared
COPY data ./data
COPY frontend ./frontend

# Vite inlines env vars at build time, so these must be build args.
ARG VITE_API_BASE_URL=http://localhost:4000/api/v1
ARG VITE_USE_MOCKS=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS

RUN cd frontend && npm run build

FROM nginx:alpine

COPY --from=build /app/frontend/dist /usr/share/nginx/html
# Single-page app: every unknown path must fall through to index.html.
RUN printf 'server {\n\
  listen 80;\n\
  root /usr/share/nginx/html;\n\
  location / { try_files $uri $uri/ /index.html; }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
