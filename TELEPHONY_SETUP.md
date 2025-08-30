# Telephony Integration Setup Guide

This guide explains how to set up outbound calling functionality using LiveKit's SIP integration.

## Prerequisites

1. **LiveKit Account**: You need a LiveKit Cloud account or self-hosted LiveKit server
2. **SIP Provider**: A SIP trunk provider (e.g., Twilio, Telnyx, or similar)
3. **LiveKit CLI**: Install the LiveKit CLI for dispatching agents

## Environment Variables

Add the following environment variables to your `.env.local` file:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# SIP Configuration
SIP_OUTBOUND_TRUNK_ID=your_sip_trunk_id

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# ElevenLabs Configuration (for TTS)
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Deepgram Configuration (for STT)
DEEPGRAM_API_KEY=your_deepgram_api_key
```

## SIP Trunk Setup

### 1. Configure SIP Trunk with Provider

1. Sign up with a SIP provider (e.g., Twilio, Telnyx)
2. Create a SIP trunk for outbound calls
3. Note down the trunk credentials and domain

### 2. Create LiveKit SIP Outbound Trunk

Use the LiveKit CLI to create an outbound trunk:

```bash
livekit-cli sip create-outbound-trunk \
  --name "outbound-trunk" \
  --sip-uri "sip:your_provider_domain.com" \
  --username "your_username" \
  --password "your_password"
```

Note the trunk ID from the response and add it to your environment variables.

## Usage

### Making Outbound Calls

Use the provided script to dispatch outbound calls:

```bash
# Basic call
python dispatch_outbound_call.py +919876543210

# Call with customer name
python dispatch_outbound_call.py +919876543210 "John Doe"

# Call with customer name and city
python dispatch_outbound_call.py +919876543210 "John Doe" "Bangalore"
```

### Manual Dispatch

You can also dispatch calls manually using LiveKit CLI:

```bash
livekit-cli agent dispatch \
  --agent-name telephony-agent \
  --metadata '{"phone_number": "+919876543210", "customer_name": "John Doe", "city": "Bangalore"}'
```

## Agent Behavior

### Outbound Calls
- The agent will automatically create a SIP participant when a phone number is provided in metadata
- It will initiate the call to the specified phone number
- The greeting is customized for outbound calls

### Inbound Calls
- Works as before for regular inbound calls
- No SIP participant is created

## Features

### Budget Calculator
The telephony agent includes a budget calculator tool that:
- Calculates wedding service costs based on events, people count, and location
- Provides breakdown for décor, photography, and catering
- Supports location-based pricing adjustments
- Formats output for natural speech

### Call Management
- Automatic call termination when requested
- Human transfer capability
- Specialized agent handoffs (math, weather)

## Troubleshooting

### Common Issues

1. **SIP Trunk Not Found**
   - Verify the `SIP_OUTBOUND_TRUNK_ID` environment variable
   - Check that the trunk exists in your LiveKit project

2. **Call Not Connecting**
   - Verify phone number format (must include country code)
   - Check SIP provider credentials
   - Ensure the SIP trunk is properly configured

3. **Agent Not Dispatching**
   - Verify LiveKit CLI is installed and configured
   - Check that the agent name matches your deployment
   - Ensure all required environment variables are set

### Debugging

Enable debug logging by setting the log level:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

## Security Considerations

1. **API Keys**: Keep all API keys secure and never commit them to version control
2. **Phone Numbers**: Validate phone numbers before making calls
3. **Rate Limiting**: Implement rate limiting for outbound calls
4. **Call Logging**: Consider logging call details for compliance

## Cost Optimization

1. **Call Duration**: Implement automatic call termination to minimize costs
2. **Provider Selection**: Compare SIP provider rates for your target regions
3. **Batch Processing**: Consider batching outbound calls during off-peak hours

## Integration Examples

### CRM Integration

```python
from dispatch_outbound_call import dispatch_outbound_call

# Example: Call leads from CRM
leads = get_leads_from_crm()
for lead in leads:
    dispatch_outbound_call(
        phone_number=lead.phone,
        customer_name=lead.name,
        city=lead.city
    )
```

### Webhook Integration

```python
# Example: Webhook endpoint for call requests
@app.route('/api/call', methods=['POST'])
def initiate_call():
    data = request.json
    success = dispatch_outbound_call(
        phone_number=data['phone_number'],
        customer_name=data.get('customer_name'),
        city=data.get('city')
    )
    return {'success': success}
```

## Support

For issues related to:
- **LiveKit**: Check the [LiveKit documentation](https://docs.livekit.io/)
- **SIP Integration**: Refer to [LiveKit SIP docs](https://docs.livekit.io/agents/v1/start/telephony/)
- **Agent Development**: See the [LiveKit Agents guide](https://docs.livekit.io/agents/v1/)
