FROM oven/bun:1.2.23 AS build

WORKDIR /app

COPY ui/package.json ui/bun.lock ./
RUN bun install --frozen-lockfile

COPY ui ./

ARG PUBLIC_PERSEPHONE_API_URL=http://127.0.0.1:8787
ENV PUBLIC_PERSEPHONE_API_URL=$PUBLIC_PERSEPHONE_API_URL

RUN bun run build

FROM oven/bun:1.2.23

WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json

EXPOSE 3000

CMD ["bun", "build/index.js"]
