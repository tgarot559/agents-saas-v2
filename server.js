import express from 'express';
import cors from 'cors';
import { createClient } from '@supabase/supabase-js';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Supabase client
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

// Middleware
app.use(cors());
app.use(express.json());

// Auth middleware - Simple token validation
const authMiddleware = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token' });
  
  try {
    // Decode base64 token (format: base64(email:id:is_admin))
    const decoded = JSON.parse(Buffer.from(token, 'base64').toString());
    req.user = decoded;
    next();
  } catch (err) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// ============================================================================
// AUTH ENDPOINTS
// ============================================================================

app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password, name, inviteCode } = req.body;

    // Check if user exists
    const { data: existingUser } = await supabase
      .from('users')
      .select('id')
      .eq('email', email)
      .single();

    if (existingUser) {
      return res.status(400).json({ error: 'User already exists' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Determine if admin or client
    const isAdmin = !inviteCode;
    let clientId = null;

    if (inviteCode) {
      const { data: invite } = await supabase
        .from('invitations')
        .select('client_id')
        .eq('code', inviteCode)
        .eq('used', false)
        .single();

      if (!invite) {
        return res.status(400).json({ error: 'Invalid invite code' });
      }

      clientId = invite.client_id;

      // Mark invite as used
      await supabase
        .from('invitations')
        .update({ used: true })
        .eq('code', inviteCode);
    }

    // Create user
    const { data: user } = await supabase
      .from('users')
      .insert({
        email,
        password: hashedPassword,
        name,
        is_admin: isAdmin,
        client_id: clientId
      })
      .select()
      .single();

    const token = Buffer.from(JSON.stringify({ id: user.id, email: user.email, isAdmin: user.is_admin, clientId: user.client_id })).toString('base64');

    res.json({ token, user });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    const { data: user } = await supabase
      .from('users')
      .select('*')
      .eq('email', email)
      .single();

    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = Buffer.from(JSON.stringify({ id: user.id, email: user.email, isAdmin: user.is_admin, clientId: user.client_id })).toString('base64');

    res.json({ token, user });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// ADMIN ENDPOINTS
// ============================================================================

app.post('/api/admin/clients', authMiddleware, async (req, res) => {
  try {
    if (!req.user.isAdmin) return res.status(403).json({ error: 'Not admin' });

    const { name, email } = req.body;

    const { data: client } = await supabase
      .from('clients')
      .insert({ name, email, admin_id: req.user.id })
      .select()
      .single();

    res.json(client);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/admin/clients', authMiddleware, async (req, res) => {
  try {
    if (!req.user.isAdmin) return res.status(403).json({ error: 'Not admin' });

    const { data: clients } = await supabase
      .from('clients')
      .select('*')
      .eq('admin_id', req.user.id);

    res.json(clients || []);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/admin/clients/:clientId/invite', authMiddleware, async (req, res) => {
  try {
    if (!req.user.isAdmin) return res.status(403).json({ error: 'Not admin' });

    const code = Math.random().toString(36).substr(2, 9).toUpperCase();

    const { data: invitation } = await supabase
      .from('invitations')
      .insert({
        client_id: req.params.clientId,
        code,
        used: false
      })
      .select()
      .single();

    res.json({ inviteCode: code, invitation });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// DATA ENDPOINTS (Shared between apps)
// ============================================================================

app.get('/api/user', authMiddleware, async (req, res) => {
  try {
    const { data: user } = await supabase
      .from('users')
      .select('*')
      .eq('id', req.user.id)
      .single();

    res.json(user);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/data/:type', authMiddleware, async (req, res) => {
  try {
    const { type } = req.params;
    const clientId = req.user.clientId || req.user.id;

    const { data } = await supabase
      .from(type)
      .select('*')
      .eq('client_id', clientId);

    res.json(data || []);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/data/:type', authMiddleware, async (req, res) => {
  try {
    const { type } = req.params;
    const clientId = req.user.clientId || req.user.id;

    const { data } = await supabase
      .from(type)
      .insert({ ...req.body, client_id: clientId })
      .select()
      .single();

    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// HEALTH CHECK
// ============================================================================

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date() });
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
