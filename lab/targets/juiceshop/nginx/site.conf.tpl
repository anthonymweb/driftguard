upstream juice-shop { server juice-shop:3000; }

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

    {{DEBUG_LOCATION}}

    location / {
        proxy_pass http://juice-shop;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
