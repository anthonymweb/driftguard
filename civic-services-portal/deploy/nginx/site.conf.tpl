upstream api { server api:5000; }

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

    {{DEBUG_LOCATION}}

    location /api/ {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
