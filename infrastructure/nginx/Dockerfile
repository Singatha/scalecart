FROM node:22-alpine AS storefront-build
WORKDIR /storefront
COPY apps/storefront/package*.json ./
RUN npm ci
COPY apps/storefront ./
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY infrastructure/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY infrastructure/nginx/proxy-common.conf /etc/nginx/proxy-common.conf
COPY --from=storefront-build /storefront/dist /usr/share/nginx/html
EXPOSE 8080

