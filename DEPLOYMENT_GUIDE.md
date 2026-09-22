# 🚀 Deployment Guide - Vercel

## Step 1: Push to GitHub

```bash
cd agents-saas
git init
git add .
git commit -m "Initial commit: Agents SaaS platform"
git branch -M main
git remote add origin https://github.com/tgarot559/agents-saas.git
git push -u origin main
```

## Step 2: Create Vercel Account (if needed)

1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "Import Project"
4. Select your `agents-saas` repo

## Step 3: Configure Environment Variables

In Vercel Dashboard:
1. Go to your project
2. **Settings** → **Environment Variables**
3. Add these:

```
SUPABASE_URL = https://xfceukvqkllmoyjqmqui.supabase.co
SUPABASE_KEY = sb_publishable_zH1nJ800Ovh7SnteeWTe5Q_i32qeKrF
JWT_SECRET = agents-saas-super-secret-2026-change-in-production
NODE_ENV = production
```

## Step 4: Setup Database

1. Go to Supabase dashboard
2. SQL Editor
3. Copy all SQL from `init.sql`
4. Run in SQL Editor
5. Done!

## Step 5: Deploy

1. Vercel automatically deploys on push
2. Wait for build to finish
3. Your URL: `https://agents-saas.vercel.app` (or your domain)

## Step 6: Create First Admin Account

1. Open your Vercel URL
2. Click "Register"
3. Leave "Invite Code" empty
4. You're now admin!

## First Use

**As Admin:**
- Create clients
- Generate invite codes
- Share codes with clients

**As Client:**
- Register with invite code
- Access three apps
- Manage your data

## Support

All data is stored in Supabase.
Contact: thierry.garot@iroko-conseil.pro
