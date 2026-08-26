SELECT 'CREATE DATABASE test_nails_course'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'test_nails_course')\gexec
