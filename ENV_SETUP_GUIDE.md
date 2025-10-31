# Environment Variables Setup Guide for Vercel Deployment

## 📋 Quick Start

This guide helps you set up all required environment variables for deploying SafeLink to Vercel.

---

## 🔑 Step 1: Generate Secret Keys

### **Method 1: Using Python**
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### **Method 2: Using OpenSSL**
```bash
openssl rand -base64 32
```

### **Method 3: Online Generator**
Visit: https://randomkeygen.com/ (Use "CodeIgniter Encryption Keys")

**Copy the generated keys** - You'll need them in Step 4.

---

## 🗄️ Step 2: Set Up PostgreSQL Database

SafeLink requires a PostgreSQL database for production. Choose one:

### **Option A: Supabase (Recommended - Free Tier)**

1. Go to https://supabase.com
2. Click **"Start your project"**
3. Create new project:
   - Project name: `safelink-db`
   - Database password: (generate strong password)
   - Region: Choose closest to your users
4. Wait for project creation (~2 minutes)
5. Go to **Settings** → **Database**
6. Copy the **Connection string** (Pooler mode):
   ```
   postgresql://postgres.xxx:password@xxx.pooler.supabase.com:5432/postgres
   ```
7. Save this as your `DATABASE_URL`

### **Option B: Neon (Serverless PostgreSQL)**

1. Go to https://neon.tech
2. Sign up and create new project
3. Copy the connection string:
   ```
   postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb
   ```

### **Option C: ElephantSQL**

1. Go to https://www.elephantsql.com
2. Create free "Tiny Turtle" plan
3. Copy the connection URL

---

## 🌐 Step 3: Deploy to Vercel (First Time)

1. **Go to Vercel Dashboard:** https://vercel.com/dashboard
2. **Import Project:**
   - Click **"Add New"** → **"Project"**
   - Import `Nagarohit29/Safelink` from GitHub
   - Click **"Import"**
3. **Configure Build Settings:**
   ```
   Framework Preset: Other
   Root Directory: ./
   Build Command: cd Frontend && npm install && npm run build
   Output Directory: Frontend/dist
   Install Command: npm install --prefix Frontend
   ```
4. **Skip environment variables for now** (we'll add them next)
5. Click **"Deploy"**
6. **Note your deployment URL:** `https://your-app-name.vercel.app`

---

## ⚙️ Step 4: Add Environment Variables to Vercel

### **Go to Project Settings:**
1. Go to https://vercel.com/dashboard
2. Select your **Safelink** project
3. Click **Settings** → **Environment Variables**

### **Add These Variables One by One:**

Click **"Add New"** for each variable:

---

#### **1. Database (REQUIRED)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Production, Preview, Development |

**Paste your Supabase/Neon connection string here**

---

#### **2. Security Keys (REQUIRED)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `SECRET_KEY` | *(Paste your generated key from Step 1)* | Production, Preview, Development |
| `JWT_SECRET_KEY` | *(Paste your other generated key from Step 1)* | Production, Preview, Development |
| `JWT_ALGORITHM` | `HS256` | Production, Preview, Development |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Production, Preview, Development |

---

#### **3. CORS Configuration (REQUIRED)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `CORS_ORIGINS` | `https://your-app-name.vercel.app` | Production, Preview, Development |

**Replace `your-app-name` with your actual Vercel domain from Step 3**

---

#### **4. Application Settings (REQUIRED)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `APP_MODE` | `production` | Production |
| `ENABLE_PACKET_SNIFFING` | `false` | Production, Preview, Development |
| `NETWORK_INTERFACE` | `disabled` | Production, Preview, Development |

---

#### **5. API Configuration (REQUIRED)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `API_HOST` | `0.0.0.0` | Production, Preview, Development |
| `API_PORT` | `8000` | Production, Preview, Development |
| `FRONTEND_URL` | `https://your-app-name.vercel.app` | Production, Preview, Development |
| `VITE_API_BASE_URL` | `https://your-app-name.vercel.app/api` | Production, Preview, Development |

---

#### **6. Logging (OPTIONAL)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `LOG_LEVEL` | `INFO` | Production, Preview, Development |
| `LOG_FILE_PATH` | `/tmp/safelink.log` | Production, Preview, Development |

---

#### **7. Threat Intelligence (OPTIONAL - Recommended)**

Get free API key from: https://www.abuseipdb.com/register

| Variable | Value | Environment |
|----------|-------|-------------|
| `ABUSEIPDB_API_KEY` | *(Your AbuseIPDB API key)* | Production, Preview, Development |

---

#### **8. Model Configuration (OPTIONAL)**

| Variable | Value | Environment |
|----------|-------|-------------|
| `RF_MODEL_PATH` | `Backend/SafeLink_Backend/models/random_forest_model.pkl` | Production |
| `ANN_MODEL_PATH` | `Backend/SafeLink_Backend/models/ann_model.h5` | Production |
| `RF_THRESHOLD` | `0.5` | Production |

---

## 🚀 Step 5: Redeploy

After adding all environment variables:

1. Go to **Deployments** tab
2. Click **"Redeploy"** on the latest deployment
3. Wait for deployment to complete (~2-3 minutes)
4. Visit your site: `https://your-app-name.vercel.app`

---

## ✅ Step 6: Test Your Deployment

1. **Visit your site:** `https://your-app-name.vercel.app`
2. **Test API:** `https://your-app-name.vercel.app/api/health`
3. **Check API docs:** `https://your-app-name.vercel.app/docs`
4. **Try to login/register** on the dashboard

---

## 🔧 Step 7: Update CORS After First Deploy

Now that you know your exact domain:

1. Go back to **Environment Variables** in Vercel
2. Edit `CORS_ORIGINS`
3. Update to your actual domain(s):
   ```
   https://safelink-abc123.vercel.app,https://www.your-custom-domain.com
   ```
4. **Save** and **Redeploy**

---

## 📋 Minimum Required Variables Checklist

For deployment to work, you MUST set these:

- [x] `DATABASE_URL` - PostgreSQL connection string
- [x] `SECRET_KEY` - Random 32+ character string
- [x] `JWT_SECRET_KEY` - Another random 32+ character string
- [x] `CORS_ORIGINS` - Your Vercel domain
- [x] `APP_MODE` - Set to `production`
- [x] `ENABLE_PACKET_SNIFFING` - Set to `false`
- [x] `API_HOST` - Set to `0.0.0.0`
- [x] `FRONTEND_URL` - Your Vercel domain

---

## 🎯 Optional Enhancements

### **Enable GitHub Auto-Deploy:**

1. Get Vercel token: https://vercel.com/account/tokens
2. Go to GitHub: https://github.com/Nagarohit29/Safelink/settings/secrets/actions
3. Add secret:
   - Name: `VERCEL_TOKEN`
   - Value: *(Paste your token)*
4. Now every push to `main` auto-deploys! 🎉

### **Custom Domain:**

1. In Vercel, go to **Settings** → **Domains**
2. Add your custom domain
3. Update DNS records as instructed
4. Update `CORS_ORIGINS` to include new domain

---

## 🆘 Troubleshooting

### **Build Fails:**
- Check if all Frontend files are committed to Git
- Verify `Frontend/src/lib/` folder exists in repository

### **Database Connection Error:**
- Verify `DATABASE_URL` is correct
- Check if database allows connections from Vercel IPs
- Ensure database password doesn't contain special characters

### **CORS Errors:**
- Update `CORS_ORIGINS` with correct domain
- Include both with and without `www.` if needed
- Redeploy after changing

### **401 Unauthorized:**
- Check `SECRET_KEY` and `JWT_SECRET_KEY` are set
- Verify they are at least 32 characters long

---

## 📞 Support

If you encounter issues:
- Check Vercel deployment logs
- Review environment variables
- Ensure database is accessible
- Verify all required variables are set

---

## 🎉 Success!

Your SafeLink application should now be running on Vercel!

**Next Steps:**
- Set up custom domain (optional)
- Configure email alerts (optional)
- Deploy backend worker on VPS for packet sniffing (optional)
- Monitor performance in Vercel dashboard

---

**Generated for:** SafeLink Network Defense System  
**Platform:** Vercel Serverless  
**Date:** October 31, 2025
