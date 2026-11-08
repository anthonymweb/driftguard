upstream portal { server portal:5000; }
server {
    listen 80 default_server;
    server_name _;
{{HTTP_BLOCK}}
}
server {
    listen 443 ssl default_server;
    server_name _;
    ssl_certificate     /etc/nginx/certs/{{CERT}}.crt;
    ssl_certificate_key /etc/nginx/certs/{{CERT}}.key;
    ssl_protocols {{SSL_PROTOCOLS}};
{{SSL_CIPHERS}}
{{DEBUG_LOCATION}}
    location / { proxy_pass http://portal; proxy_set_header Host $host; }
}
