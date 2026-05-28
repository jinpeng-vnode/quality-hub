# 阶段一：构建
FROM node:18-slim AS builder

WORKDIR /app

RUN yarn config set registry https://registry.npmmirror.com

COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile 2>/dev/null || yarn install

COPY . .
RUN yarn build

# 阶段二：nginx 托管
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
