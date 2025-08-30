#!/usr/bin/env python3
"""
Deployment script for LiveKit agent
"""

import subprocess
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv


def check_livekit_cli() -> bool:
    """Check if LiveKit CLI is available"""
    try:
        result = subprocess.run(["livekit-cli", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def check_login() -> bool:
    """Check if logged in to LiveKit"""
    try:
        result = subprocess.run(["livekit-cli", "whoami"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def deploy_agent(agent_name: str = "master-agent") -> Dict[str, Any]:
    """Deploy the agent to LiveKit cloud"""
    result = {"success": False, "error": None, "output": None}

    try:
        print(f"🚀 Deploying agent '{agent_name}' to LiveKit cloud...")

        cmd = ["livekit-cli", "agent", "deploy", "--name", agent_name, "--source", ".", "--env-file", ".env.local"]

        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if process.returncode == 0:
            result["success"] = True
            result["output"] = process.stdout
            print("✅ Agent deployed successfully!")
        else:
            result["error"] = f"Deployment failed: {process.stderr}"
            print(f"❌ Deployment failed: {process.stderr}")

    except Exception as e:
        result["error"] = f"Error during deployment: {str(e)}"
        print(f"💥 Error during deployment: {e}")

    return result


def verify_deployment(agent_name: str = "master-agent") -> Dict[str, Any]:
    """Verify the agent deployment"""
    result = {"deployed": False, "running": False, "error": None, "details": None}

    try:
        print(f"🔍 Verifying deployment of agent '{agent_name}'...")

        cmd = ["livekit-cli", "agent", "describe", agent_name]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if process.returncode == 0:
            result["deployed"] = True
            result["details"] = process.stdout

            # Check if agent is running
            if "status" in process.stdout.lower() and "running" in process.stdout.lower():
                result["running"] = True
                print("✅ Agent is deployed and running!")
            else:
                print("⚠️  Agent is deployed but not running")
        else:
            result["error"] = f"Agent not found: {process.stderr}"
            print(f"❌ Agent not found: {process.stderr}")

    except Exception as e:
        result["error"] = f"Error checking agent: {str(e)}"
        print(f"💥 Error checking agent: {e}")

    return result


def main():
    """Main deployment function"""
    print("🚀 LiveKit Agent Deployment")
    print("=" * 40)

    # Load environment variables
    load_dotenv(dotenv_path=".env.local")

    # Check LiveKit CLI
    print("\n1. Checking LiveKit CLI...")
    if not check_livekit_cli():
        print("❌ LiveKit CLI not found. Please install it first.")
        print("   Run: npm install -g @livekit/cli")
        print("   Or: curl -sSL https://get.livekit.io | bash")
        sys.exit(1)
    print("✅ LiveKit CLI is available")

    # Check login
    print("\n2. Checking LiveKit login...")
    if not check_login():
        print("❌ Not logged in to LiveKit. Please login first.")
        print("   Run: livekit-cli login")
        sys.exit(1)
    print("✅ Logged in to LiveKit")

    # Check environment file
    print("\n3. Checking environment file...")
    if not os.path.exists(".env.local"):
        print("❌ .env.local file not found. Please create it with required environment variables.")
        print("   See DEPLOYMENT.md for required variables.")
        sys.exit(1)
    print("✅ .env.local file found")

    # Deploy agent
    print("\n4. Deploying agent...")
    deployment_result = deploy_agent()

    if not deployment_result["success"]:
        print(f"❌ Deployment failed: {deployment_result['error']}")
        sys.exit(1)

    # Verify deployment
    print("\n5. Verifying deployment...")
    verification_result = verify_deployment()

    if not verification_result["deployed"]:
        print(f"❌ Verification failed: {verification_result['error']}")
        sys.exit(1)

    print("\n🎉 Deployment completed successfully!")
    print("\nNext steps:")
    print("1. Test outbound calls: python dispatch_outbound_call.py +919876543210")
    print("2. Test agent dispatch: livekit-cli agent dispatch --agent-name master-agent")
    print("3. Monitor logs: livekit-cli agent logs master-agent")
    print("4. Check status: livekit-cli agent describe master-agent")


if __name__ == "__main__":
    main()
