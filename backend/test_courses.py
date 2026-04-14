import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="nails_course",
        user="postgres", password="Punkrock77",
    )
    cur = conn.cursor()
    
    # Show current courses
    cur.execute("SELECT id, title, price_self, price_support, is_published FROM courses")
    rows = cur.fetchall()
    print("=== CURRENT COURSES ===")
    for row in rows:
        print(f"  ID: {row[0]}, Title: {row[1]}, Self: {row[2]}, Support: {row[3]}, Published: {row[4]}")
    
    # Update prices to match landing page
    cur.execute("UPDATE courses SET price_self = 5900, price_support = 11900")
    updated = cur.rowcount
    conn.commit()
    print(f"\n=== UPDATED {updated} course(s) prices: self=5900, support=11900 ===")
    
    # Verify
    cur.execute("SELECT id, title, price_self, price_support FROM courses")
    rows = cur.fetchall()
    print("\n=== AFTER UPDATE ===")
    for row in rows:
        print(f"  ID: {row[0]}, Title: {row[1]}, Self: {row[2]}, Support: {row[3]}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
