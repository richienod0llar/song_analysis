import sqlite3

def check_database():
    conn = sqlite3.connect('music_database.db')
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in database:")
    for table in tables:
        print(f"\n=== {table[0]} ===")
        # Get column info
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"Number of rows: {count}")
        
        # Show sample data
        if count > 0:
            cursor.execute(f"SELECT * FROM {table[0]} LIMIT 1")
            sample = cursor.fetchone()
            print("Sample row:")
            for col, val in zip([c[1] for c in columns], sample):
                print(f"  {col}: {val}")
    
    conn.close()

if __name__ == "__main__":
    check_database() 