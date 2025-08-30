# LiveKit Voice Agent with Multi-Agent Workflow & Telephony Integration

A modular LiveKit voice agent system with specialized agents for different tasks, seamless handoff capabilities, and outbound calling functionality.

## 🏗️ Project Structure

```
revspot-random-at3pwf/
├── main.py                  # Main entry point with telephony support
├── constants.py             # System prompts and constants
├── requirements.txt         # Python dependencies
├── agents/                  # Agent implementations
│   ├── __init__.py
│   ├── master_agent.py      # Main agent with handoff and human transfer capabilities
│   ├── math_agent.py        # Specialized math agent
│   └── weather_agent.py     # Specialized weather agent
├── tools/                   # Tool implementations
│   ├── __init__.py
│   ├── calculator.py        # Calculator tool
│   ├── weather.py           # Weather lookup tool
│   ├── budget_calculator.py # Wedding budget calculator
│   └── telephony_utils.py   # Telephony utilities
├── recording_service.py     # Audio recording and S3 upload service
├── test_recording.py        # Recording service test script
├── RECORDING_SETUP.md       # Recording setup guide
├── dispatch_outbound_call.py # Enhanced script for dispatching outbound calls
├── test_integration.py      # Test script for telephony integration
├── TELEPHONY_SETUP.md       # Telephony setup guide
└── KMS/
    └── logs/
```

## 🎯 Features

### **Multi-Agent Workflow**
- **Master Agent**: Main entry point with wedding planning, outbound calling, and human transfer capabilities
- **Math Agent**: Specialized for mathematical calculations
- **Weather Agent**: Specialized for weather information

### **Seamless Handoffs**
- Automatic agent switching based on user requests
- Context preservation during handoffs
- Return functionality to main agent

### **Telephony Integration**
- **Outbound Calling**: Make calls to phone numbers via SIP
- **Budget Calculator**: Automated wedding service cost estimation
- **Call Management**: Automatic call termination and human transfer
- **SIP Integration**: Seamless integration with SIP providers

### **Audio Recording**
- **Automatic Recording**: Records all participants in LiveKit rooms
- **S3 Integration**: Automatic upload to Amazon S3
- **Configurable Format**: Support for OGG, MP4, and WebM formats
- **Error Handling**: Graceful failure handling without affecting calls

### **Modular Design**
- Clean separation of concerns
- Reusable components
- Easy to extend with new agents and tools

## 🚀 Usage

### **Deploying the Agent to LiveKit Cloud**

First, deploy your agent to LiveKit cloud:

```bash
# Install LiveKit CLI
npm install -g @livekit/cli

# Login to LiveKit
livekit-cli login

# Deploy the agent (or use the deployment script)
python deploy_agent.py

# Or manually deploy
livekit-cli agent deploy --name master-agent --source . --env-file .env.local
```

### **Testing the Deployment**

```bash
# Test deployment
python test_deployment.py

# Check agent status
livekit-cli agent describe master-agent

# View agent logs
livekit-cli agent logs master-agent
```

### **Starting the Agent Locally**
```bash
python main.py
```

### **Making Outbound Calls**
```bash
# Basic outbound call
python dispatch_outbound_call.py +919876543210

# Call with customer details
python dispatch_outbound_call.py +919876543210 "John Doe" "Bangalore"

# Call with transfer number
python dispatch_outbound_call.py +919876543210 "John Doe" "Bangalore" +918860932771

# Dry run (validate without making call)
python dispatch_outbound_call.py +919876543210 --dry-run
```

### **Audio Recording Setup**
```bash
# Test recording configuration
python test_recording.py

# Enable recording in .env.local
ENABLE_AUDIO_RECORDING=true
S3_RECORDING_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

For detailed recording setup instructions, see [RECORDING_SETUP.md](RECORDING_SETUP.md).

### **Testing Telephony Integration**
```bash
python test_integration.py
```

### **Agent Workflow Examples**

**Math Request:**
- User: "I need to calculate the total cost for my wedding"
- Master Agent → Math Agent (automatic handoff)
- Math Agent handles calculation and can return to main agent

**Weather Request:**
- User: "What's the weather like in Mumbai for my wedding?"
- Master Agent → Weather Agent (automatic handoff)
- Weather Agent provides weather info and can return to main agent

**Budget Calculation:**
- User: "What would it cost for 3 events with 100 people in Bangalore?"
- Master Agent uses budget calculator tool
- Provides detailed cost breakdown for décor, photography, and catering

**Human Transfer:**
- User: "I want to speak with a human"
- Master Agent transfers call to human operator using transfer_to number from metadata
- Rich context passed to human operator (call duration, customer info, transfer reason)
- Transfer limit protection (max 3 attempts)
- Graceful fallback if transfer fails

## 🛠️ Adding New Agents

1. **Create a new agent file** in `agents/`:
```python
from .base_agent import BaseAgent

class NewSpecializedAgent(BaseAgent):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="Your specialized instructions",
            tools=[your_tools],
            chat_ctx=chat_ctx,
        )
```

2. **Add handoff tool** to `MasterAgent`:
```python
@function_tool()
async def handoff_to_new_agent(self, context: RunContext):
    # Handoff logic
    return "Transferring to new specialist", NewSpecializedAgent(chat_ctx=self.chat_ctx)
```

## 🛠️ Adding New Tools

1. **Create a new tool file** in `tools/`:
```python
from livekit.agents import function_tool, RunContext

@function_tool()
async def your_tool(context: RunContext, param: str):
    """Tool description"""
    # Implementation
    return {"result": "value"}
```

2. **Import and use** in your agent:
```python
from tools.your_tool import your_tool

# Add to agent tools list
tools=[your_tool]
```

## 📋 Dependencies

- LiveKit Agents
- OpenAI (LLM)
- Deepgram (STT)
- ElevenLabs (TTS)
- SIP Provider (for telephony)
- AWS S3 (for audio recording)
- Other plugins as configured

## 📞 Telephony Setup

For outbound calling functionality, see the detailed setup guide in [TELEPHONY_SETUP.md](TELEPHONY_SETUP.md).

**Quick Setup:**
1. Set up SIP trunk with provider (Twilio, Telnyx, etc.)
2. Create LiveKit SIP outbound trunk
3. Update environment variables
4. Test with `python test_telephony.py`

## 🔧 Configuration

Update your `.env.local` file with necessary API keys and configuration.

## 📚 Best Practices

- **Separation of Concerns**: Each agent has a specific purpose
- **Tool Isolation**: Tools are independent and reusable
- **Context Preservation**: Conversation history maintained during handoffs
- **Error Handling**: Proper error handling in tools and agents
- **Documentation**: Clear docstrings for all tools and agents
