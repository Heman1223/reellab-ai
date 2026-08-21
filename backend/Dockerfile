# Build context is the REPO ROOT — the backend compiles `shared/schemas`.
FROM node:22-alpine AS build

WORKDIR /app

COPY backend/package*.json ./backend/
RUN cd backend && npm ci

COPY shared ./shared
COPY backend ./backend

RUN cd backend && npm run build && npm prune --omit=dev

FROM node:22-alpine

WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/backend/node_modules ./backend/node_modules
COPY --from=build /app/backend/dist ./dist
COPY --from=build /app/backend/package.json ./backend/package.json
# `config/paths.ts` locates the repo root by finding `shared/` and `data/`;
# `data/` is mounted by docker-compose at runtime.
COPY shared ./shared

EXPOSE 4000
CMD ["node", "dist/backend/src/server.js"]
