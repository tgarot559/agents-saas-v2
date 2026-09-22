-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  is_admin BOOLEAN DEFAULT false,
  client_id UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255),
  admin_id UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Invitations table
CREATE TABLE IF NOT EXISTS invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  code VARCHAR(20) UNIQUE NOT NULL,
  used BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days'
);

-- LinkedIn campaigns
CREATE TABLE IF NOT EXISTS linkedin_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  name VARCHAR(255),
  account_id UUID,
  status VARCHAR(50) DEFAULT 'draft',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Social media posts
CREATE TABLE IF NOT EXISTS social_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  text TEXT,
  networks TEXT[],
  schedule_date TIMESTAMP,
  status VARCHAR(50) DEFAULT 'draft',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Prospection campaigns
CREATE TABLE IF NOT EXISTS prospection_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  name VARCHAR(255),
  email_id UUID,
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Prospects
CREATE TABLE IF NOT EXISTS prospects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  campaign_id UUID REFERENCES prospection_campaigns(id),
  email VARCHAR(255),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  company VARCHAR(255),
  status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_client_id ON users(client_id);
CREATE INDEX idx_clients_admin_id ON clients(admin_id);
CREATE INDEX idx_linkedin_campaigns_client_id ON linkedin_campaigns(client_id);
CREATE INDEX idx_social_posts_client_id ON social_posts(client_id);
CREATE INDEX idx_prospection_campaigns_client_id ON prospection_campaigns(client_id);
CREATE INDEX idx_prospects_client_id ON prospects(client_id);
CREATE INDEX idx_prospects_campaign_id ON prospects(campaign_id);
