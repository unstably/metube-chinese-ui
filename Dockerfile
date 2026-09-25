FROM nginx:alpine

# MeTube 后端地址（构建时可覆盖）：
#   同一 docker 网络 -> metube:8081
#   走宿主机端口     -> host.docker.internal:7878
ARG METUBE_BACKEND=metube:8081

COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN sed -i "s|__BACKEND__|${METUBE_BACKEND}|g" /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
