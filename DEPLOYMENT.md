# LiveKit Agent Deployment Guide

This guide explains how to deploy your agent to LiveKit cloud for both outbound calling and inbound call handling.

## Prerequisites

1. **LiveKit Cloud Account**: You need a LiveKit Cloud account
2. **LiveKit CLI**: Install the LiveKit CLI
3. **Environment Variables**: Configure all required environment variables

## Environment Setup

Create a `.env.local` file with the following variables:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# SIP Configuration (for outbound calls)
SIP_OUTBOUND_TRUNK_ID=your_sip_trunk_id

# AI Service APIs
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
```

## Deployment Steps

### 1. Install LiveKit CLI

```bash
# Install LiveKit CLI
npm install -g @livekit/cli

# Or using curl
curl -sSL https://get.livekit.io | bash
```

### 2. Login to LiveKit Cloud

```bash
livekit-cli login
```

### 3. Deploy the Agent

```bash
# Deploy the agent to LiveKit cloud
livekit-cli agent deploy \
  --name master-agent \
  --source . \
  --env-file .env.local
```

### 4. Verify Deployment

```bash
# List deployed agents
livekit-cli agent list

# Check agent status
livekit-cli agent describe master-agent
```

## Testing the Deployment

### Method 1: Outbound Calls (Already Working)

```bash
# Test outbound calling
python dispatch_outbound_call.py +919876543210 "John Doe" "Bangalore"
```

### Method 2: Inbound Calls (New)

```bash
# Create a room and join it
livekit-cli room create test-room

# Join the room (this will trigger the agent)
livekit-cli room join test-room
```

### Method 3: Direct Agent Dispatch

```bash
# Dispatch agent to a new room
livekit-cli agent dispatch \
  --agent-name master-agent \
  --metadata '{"phone_number": "+919876543210", "customer_name": "John Doe", "city": "Bangalore"}'
```

## Troubleshooting

### Common Issues

1. **Agent Not Deploying**
   - Check LiveKit CLI is installed and logged in
   - Verify all environment variables are set
   - Check the agent name matches in deployment

2. **Agent Not Responding**
   - Check agent logs: `livekit-cli agent logs master-agent`
   - Verify the agent is running: `livekit-cli agent describe master-agent`

3. **Environment Variables Not Loading**
   - Ensure `.env.local` file exists and is properly formatted
   - Check variable names match exactly

### Debug Commands

```bash
# Check agent status
livekit-cli agent describe master-agent

# View agent logs
livekit-cli agent logs master-agent

# Restart agent
livekit-cli agent restart master-agent

# Update agent
livekit-cli agent deploy --name master-agent --source . --env-file .env.local
```

## Local Development

For local development and testing:

```bash
# Run agent locally
python main.py

# Test with local LiveKit server
LIVEKIT_URL=ws://localhost:7880 python main.py
```

## Production Deployment

For production deployment:

1. **Set up CI/CD pipeline** to automatically deploy on code changes
2. **Configure monitoring** and alerting
3. **Set up logging** aggregation
4. **Configure auto-scaling** based on call volume

## Security Considerations

1. **API Keys**: Keep all API keys secure
2. **Environment Variables**: Use secure environment variable management
3. **Access Control**: Limit access to LiveKit Cloud dashboard
4. **Call Logging**: Implement proper call logging for compliance

## Cost Optimization

1. **Agent Scaling**: Configure auto-scaling based on demand
2. **Call Duration**: Implement automatic call termination
3. **Resource Usage**: Monitor and optimize resource usage
4. **Billing Alerts**: Set up billing alerts to avoid unexpected costs
