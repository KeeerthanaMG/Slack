# Slack Bot Credentials Setup Guide

## 🚨 **CRITICAL: Required for VIP System to Work**

The VIP system requires proper Slack API credentials to retrieve DM messages and interact with Slack. Follow these steps to configure your bot:

## 📋 **Step 1: Create .env File**

Create a file named `.env` in the `/Slack/` directory with the following content:

```bash
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Django Configuration
DJANGO_SECRET_KEY=django-insecure-tgsizyb$=(1n3zw+c45fd4q$pto)t5u$x-6*tl8sw(d4wjtg18
DEBUG=True
```

## 🔑 **Step 2: Get Your Slack App Credentials**

### From Your Slack App Dashboard (https://api.slack.com/apps):

#### **Bot User OAuth Token** (`SLACK_BOT_TOKEN`)
1. Go to **OAuth & Permissions** → **Bot User OAuth Token**
2. Copy the token that starts with `xoxb-`
3. Paste it in your `.env` file

#### **Signing Secret** (`SLACK_SIGNING_SECRET`)
1. Go to **Basic Information** → **App Credentials** → **Signing Secret**
2. Click **Show** and copy the secret
3. Paste it in your `.env` file

#### **App-Level Token** (`SLACK_APP_TOKEN`) - Optional for HTTP mode
1. Go to **Basic Information** → **App-Level Tokens**
2. If you don't have one, create it with `connections:write` scope
3. Copy the token that starts with `xapp-`
4. Paste it in your `.env` file

### **Required OAuth Scopes**
Make sure your bot has these scopes in **OAuth & Permissions** → **Scopes**:

**Bot Token Scopes:**
- `channels:history` - Read messages from public channels
- `channels:read` - View basic information about public channels
- `chat:write` - Send messages as the bot
- `commands` - Add slash commands
- `groups:history` - Read messages from private channels
- `groups:read` - View basic information about private channels  
- `im:history` - Read messages from direct messages
- `im:read` - View basic information about direct messages
- `im:write` - Send direct messages
- `users:read` - View people in the workspace
- `users:read.email` - View email addresses of people in the workspace

## 🤖 **Step 3: Get Gemini AI Key**

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create an API key
3. Add it to your `.env` file as `GEMINI_API_KEY`

## ✅ **Step 4: Test Configuration**

After setting up your `.env` file:

1. **Restart Django server:**
   ```bash
   cd /Users/happyfox/slack_updated/Slack
   python3 manage.py runserver 8000
   ```

2. **Test VIP commands in Slack:**
   ```
   /vip list
   /vip add @username
   /summary vip username
   ```

## 🔍 **Troubleshooting**

### **Check Logs**
If commands aren't working, check the Django server logs for errors like:
- `SLACK_BOT_TOKEN not found in settings`
- `SlackApiError: invalid_auth`
- `No DM channel found for VIP user`

### **Common Issues**

#### **"Bot configuration error: Slack credentials not found"**
- Your `.env` file is missing or has incorrect token format
- Make sure tokens start with `xoxb-`, `xapp-`, etc.

#### **"Messages analyzed: 0"**
- Bot doesn't have permission to read DMs/channels
- Check OAuth scopes in your Slack app
- Make sure bot is added to channels you want to summarize

#### **"invalid_command_response"**
- Summary text is too long for Slack
- This is now handled automatically by truncating long summaries

## 📱 **Step 5: Update Slack App Configuration**

Make sure your Slack app is configured with your ngrok URL:

### **Slash Commands:**
- **Command:** `/summary`
  - **Request URL:** `https://your-ngrok-url.ngrok-free.app/slack/events/`
- **Command:** `/vip`  
  - **Request URL:** `https://your-ngrok-url.ngrok-free.app/slack/events/`

### **Interactivity & Shortcuts:**
- **Request URL:** `https://your-ngrok-url.ngrok-free.app/slack/events/`

### **Event Subscriptions:**
- **Request URL:** `https://your-ngrok-url.ngrok-free.app/slack/events/`

## 🎉 **You're Ready!**

Once configured, you can use:

```bash
# Add VIPs to your personal list
/vip add @sarah
/vip add @manager

# Get VIP summaries
/summary vip sarah           # Sarah's DM summary
/summary sarah general       # Sarah's activity in #general
/summary manager marketing   # Manager's activity in #marketing

# Manage your VIP list
/vip list                    # See all your VIPs
/vip remove @sarah           # Remove from your VIP list
```

**🔐 Security Note:** Never share your tokens publicly or commit them to version control. The `.env` file is already in `.gitignore` to protect your credentials. 