CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    site_name TEXT NOT NULL,
    https_link TEXT NOT NULL,
    login_user TEXT NOT NULL
);
