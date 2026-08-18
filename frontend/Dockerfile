FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:22-alpine AS serve

WORKDIR /srv/www
COPY --from=build /app/dist ./
COPY server.mjs /srv/server.mjs

EXPOSE 80
CMD ["node", "/srv/server.mjs"]
