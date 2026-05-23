FROM node:18-slim

# 配置 apt 清华镜像
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

WORKDIR /app

# 配置 yarn 淘宝源
RUN yarn config set registry https://registry.npmmirror.com

# 复制依赖文件并安装
COPY package.json yarn.lock* .yarnrc ./
RUN yarn install --frozen-lockfile 2>/dev/null || yarn install 2>/dev/null || true

# 复制源码
COPY . .

EXPOSE 3000

CMD ["yarn", "dev", "--host", "0.0.0.0", "--port", "3000"]
