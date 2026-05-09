FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev

FROM node:18-alpine AS runtime
ENV NODE_ENV=production \
    node_port=8080
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Run as non-root
RUN addgroup -S app && adduser -S app -G app && chown -R app:app /app
USER app

EXPOSE 8080

CMD ["node", "./bin/www"]
