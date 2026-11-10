upstream app { server api:8000; }

server {
    listen 80 default_server;
    server_name _;
    {{HTTP_BLOCK}}
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/nginx/certs/{{CERT}}.crt;
    ssl_certificate_key /etc/nginx/certs/{{CERT}}.key;
    ssl_protocols {{SSL_PROTOCOLS}};
    ssl_ciphers {{SSL_CIPHERS}};

    root /usr/share/nginx/html;
    index index.html;
    client_max_body_size 1m;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;

    location = /api/internal/security-profile { return 404; }

    location /api/ {
        proxy_pass http://app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 20s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
