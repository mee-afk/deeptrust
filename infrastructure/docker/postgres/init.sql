-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create databases if needed
CREATE DATABASE deeptrust_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE deeptrust TO deeptrust;
GRANT ALL PRIVILEGES ON DATABASE deeptrust_test TO deeptrust;
