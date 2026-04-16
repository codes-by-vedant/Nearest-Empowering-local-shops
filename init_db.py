import sqlite3

# Connect to (or create) the database
conn = sqlite3.connect('businesses.db')

# Create the table
conn.execute('''
CREATE TABLE businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    area TEXT NOT NULL,
    address TEXT NOT NULL,
    contact INT NOT NULL,
    email TEXT NOT NULL,
    hours TEXT NOT NULL,
    description TEXT NOT NULL,
    map_link TEXT NOT NULL,
    owner_id INTEGER,
    FOREIGN KEY (owner_id) REFERENCES owners(id)
);
''')
conn.execute('''
CREATE TABLE owners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    address TEXT NOT NULL,
    password TEXT NOT NULL
);
''')

conn.execute('''
CREATE TABLE support_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT,
    owner_name TEXT,    
    owner_email TEXT,
    owner_contact TEXT,
    problem TEXT,
    status TEXT
);
''')

conn.close()
print("✅ Database created successfully!")
