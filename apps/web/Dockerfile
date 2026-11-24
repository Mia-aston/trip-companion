# Trip Companion web — local/dev image. The browser calls the API directly, so the API URL is baked in at build.
FROM node:22-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-slim
WORKDIR /web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /web/package.json /web/package-lock.json ./
COPY --from=build /web/node_modules ./node_modules
COPY --from=build /web/.next ./.next
COPY --from=build /web/next.config.ts ./
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000", "-H", "0.0.0.0"]
