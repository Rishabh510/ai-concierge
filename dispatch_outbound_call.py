#!/usr/bin/env python3
"""
Script to dispatch outbound calls using LiveKit SDK to a phone number
Usage: python dispatch_outbound_call.py <phone_number> [customer_name] [city] [transfer_to]
"""

import sys
import os
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime
from telephony_utils import validate_phone_number

import asyncio
from livekit import api
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")


def validate_customer_name(name: str) -> bool:
    return bool(name and 0 < len(name.strip()) <= 100)


def validate_city(city: str) -> bool:
    return bool(city and 0 < len(city.strip()) <= 50)


def check_environment() -> Dict[str, bool]:
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY",
        "ELEVEN_API_KEY",
        "DEEPGRAM_API_KEY",
    ]
    optional_vars = ["SIP_OUTBOUND_TRUNK_ID"]
    results = {var: bool(os.getenv(var)) for var in required_vars + optional_vars}
    return results


async def dispatch_outbound_call(
    phone_number: str,
    customer_name: Optional[str] = None,
    city: Optional[str] = None,
    transfer_to: Optional[str] = None,
) -> Dict[str, Any]:
    result = {"success": False, "error": None, "metadata": None, "timestamp": datetime.now().isoformat()}

    # Validate passed args
    if not validate_phone_number(phone_number):
        result["error"] = "Invalid phone number format. Must include country code (e.g., +919876543210)"
        return result
    if customer_name and not validate_customer_name(customer_name):
        result["error"] = "Invalid customer name"
        return result
    if city and not validate_city(city):
        result["error"] = "Invalid city name"
        return result
    if transfer_to and not validate_phone_number(transfer_to):
        result["error"] = "Invalid transfer number format"
        return result

    # Check environment variables
    env_check = check_environment()
    missing_required = [
        var
        for var, present in env_check.items()
        if not present and var in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    ]
    if missing_required:
        result["error"] = f"Missing required environment variables: {', '.join(missing_required)}"
        return result

    metadata = {
        "phone_number": phone_number,
        "call_id": f"call_{int(time.time())}",
        "dispatch_timestamp": datetime.now().isoformat(),
    }
    if customer_name:
        metadata["customer_name"] = customer_name.strip()
    if city:
        metadata["city"] = city.strip()
    if transfer_to:
        metadata["transfer_to"] = transfer_to.strip()
    metadata["sip_trunk_configured"] = bool(env_check.get("SIP_OUTBOUND_TRUNK_ID"))
    if not metadata["sip_trunk_configured"]:
        result["warning"] = "SIP trunk not configured - outbound calling may not work"

    room_name = f"outbound_{phone_number}_{int(time.time())}"
    agent_name = "master-agent"
    metadata_json = json.dumps(metadata)

    try:
        print(f"🚀 Dispatching outbound call to {phone_number}")
        async with api.LiveKitAPI() as lkapi:
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(agent_name=agent_name, room=room_name, metadata=metadata_json)
            )
            result["success"] = True
            result["output"] = f"Dispatch created: {dispatch}"
            result["message"] = "Call dispatched successfully!"
            print("✅ Call dispatched successfully!")
            print(f"📋 Dispatch: {dispatch}")
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        print(f"💥 Unexpected error: {e}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python dispatch_outbound_call.py <phone_number> [customer_name] [city] [transfer_to]")
        print("Example: python dispatch_outbound_call.py +919876543210 'John Doe' 'Bangalore'")
        print("Example: python dispatch_outbound_call.py +919876543210 'John Doe' 'Bangalore' +918860932771")
        sys.exit(1)

    phone_number = sys.argv[1]
    customer_name = city = transfer_to = None
    args = sys.argv[2:]
    if args:
        customer_name = args[0] if len(args) > 0 else None
    if args:
        city = args[1] if len(args) > 1 else None
    if args:
        transfer_to = args[2] if len(args) > 2 else None
    if len(args) > 3:
        for arg in args[3:]:
            print(f"⚠️  Warning: Ignoring extra argument: {arg}")

    result = asyncio.run(dispatch_outbound_call(phone_number, customer_name, city, transfer_to))

    if result["success"]:
        print("✅ Call dispatched successfully")
        sys.exit(0)
    else:
        print(f"❌ Failed to dispatch call: {result['error']}")
        if result.get("warning"):
            print(f"⚠️  Warning: {result['warning']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
