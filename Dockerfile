FROM nginx:alpine

# 站点配置：开启 gzip，静态文件不缓存（改完 index.html 刷新即可生效）
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html socket.io.min.js /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
