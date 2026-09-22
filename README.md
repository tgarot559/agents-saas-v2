# 🚀 Agents SaaS Platform

Multi-tenant SaaS platform for managing LinkedIn, Social Media, and Prospection agents.

## Features

✅ **Multi-tenant architecture** - Each client has isolated data  
✅ **Admin dashboard** - Manage all clients and invitations  
✅ **Three integrated apps:**
  - 📱 LinkedIn Agent - Multi-account campaign management
  - 📝 Social Media Manager - Post creation and scheduling
  - 🎯 Prospection Agent - Cold email automation

✅ **Secure authentication** - JWT tokens + password hashing  
✅ **Supabase database** - PostgreSQL with row-level security  
✅ **Vercel deployment** - Serverless hosting

## Setup

### 1. Environment Variables

Create `.env` file:

```bash
SUPABASE_URL=https://xfceukvqkllmoyjqmqui.supabase.co
SUPABASE_KEY=sb_publishable_zH1nJ800Ovh7SnteeWTe5Q_i32qeKrF
JWT_SECRET=your-secret-key-change-in-production
NODE_ENV=production
PORT=3000
```

### 2. Database Setup

Run the SQL from `init.sql` in Supabase:
1. Go to SQL Editor in Supabase dashboard
2. Copy contents of `init.sql`
3. Execute

### 3. Install Dependencies

```bash
npm install
```

### 4. Run Locally

```bash
npm run dev
```

### 5. Deploy to Vercel

```bash
npm run build
```

Then connect your GitHub repo to Vercel for automatic deployments.

## First Admin Account

1. Open app and register with invite code empty
2. You'll be marked as admin
3. Use this account to create clients
4. Generate invite codes for each client

## Client Workflow

1. Admin creates client
2. Admin generates invite code
3. Client registers with invite code
4. Client has access to three apps

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/admin/clients` - Create client (admin only)
- `GET /api/admin/clients` - List clients (admin only)
- `POST /api/admin/clients/:id/invite` - Generate invite code (admin only)

## Architecture

```
Frontend (HTML/JS) 
    ↓
Express Backend (Node.js)
    ↓
Supabase (PostgreSQL)
```

## Support

For issues or questions, check the documentation or create an issue.
# Force Redeploy
