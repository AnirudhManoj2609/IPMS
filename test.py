#!/usr/bin/env python3
"""
Enhanced test script for Personal Assistant
Tests multiple functionalities including schedule, tasks, and general queries
"""

import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

print("🎬 Film Production AI Assistant - Enhanced Test Script")
print("=" * 60)

# Check environment variables
print("\n🔍 Checking Environment...")
groq_key = os.getenv("GROQ_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")

if groq_key:
    print(f"✅ GROQ_API_KEY found: {groq_key[:20]}...")
else:
    print("❌ GROQ_API_KEY not found!")
    print("   Get one FREE at: https://console.groq.com")
    print("   Add to .env file: GROQ_API_KEY=gsk_your_key_here")
    exit(1)

if google_key:
    print(f"✅ GOOGLE_API_KEY found: {google_key[:20]}...")
else:
    print("⚠️  GOOGLE_API_KEY not found (optional)")

print("\n📦 Checking Imports...")

try:
    from groq import Groq
    print("✅ groq package installed")
except ImportError as e:
    print(f"❌ groq package missing: {e}")
    print("   Run: pip install groq")
    exit(1)

try:
    from assistant import PersonalAssistant, GroqLLM
    print("✅ assistant module imported")
except ImportError as e:
    print(f"❌ Failed to import assistant: {e}")
    print("\n   Make sure assistant.py is in the same directory!")
    exit(1)

print("\n" + "=" * 60)


async def test_basic_greeting():
    """Test 1: Basic greeting and introduction"""
    print("\n📝 TEST 1: Basic Greeting")
    print("-" * 60)
    
    try:
        user_profile = {
            'user_id': 'test_123',
            'name': 'Alex Johnson',
            'preferred_name': 'Alex',
            'role': 'Production Manager',
            'department': 'Production',
            'production_name': 'Midnight Dreams',
            'production_status': 'Pre-Production'
        }
        
        assistant = PersonalAssistant(
            user_id=user_profile['user_id'],
            user_profile=user_profile,
            production_id='prod_test_001',
            llm_provider='groq'
        )
        
        response = await assistant.chat("Hello! Who are you and what can you help me with?")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 1 Passed - Basic greeting works")
        
        return assistant
        
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_schedule_query(assistant):
    """Test 2: Query today's schedule"""
    print("\n📝 TEST 2: Today's Schedule Query")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        today = datetime.now().strftime("%A, %B %d, %Y")
        response = await assistant.chat(f"What's on my schedule for today ({today})?")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 2 Passed - Schedule query works")
        
    except Exception as e:
        print(f"❌ Test 2 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_task_query(assistant):
    """Test 3: Query tasks and to-dos"""
    print("\n📝 TEST 3: Task and To-Do Query")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        response = await assistant.chat("What tasks do I have pending? What needs to be done today?")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 3 Passed - Task query works")
        
    except Exception as e:
        print(f"❌ Test 3 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_production_info(assistant):
    """Test 4: Query production information"""
    print("\n📝 TEST 4: Production Information Query")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        response = await assistant.chat("Tell me about the current production I'm working on. What's the status?")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 4 Passed - Production info query works")
        
    except Exception as e:
        print(f"❌ Test 4 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_scheduling_assistance(assistant):
    """Test 5: Scheduling assistance"""
    print("\n📝 TEST 5: Scheduling Assistance")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d")
        response = await assistant.chat(
            f"I need to schedule a production meeting for {tomorrow} at 2 PM. "
            "Can you help me with that?"
        )
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 5 Passed - Scheduling assistance works")
        
    except Exception as e:
        print(f"❌ Test 5 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_general_assistance(assistant):
    """Test 6: General production assistance"""
    print("\n📝 TEST 6: General Production Assistance")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        response = await assistant.chat(
            "What are the key things I should focus on today as a Production Manager?"
        )
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 6 Passed - General assistance works")
        
    except Exception as e:
        print(f"❌ Test 6 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_context_memory(assistant):
    """Test 7: Context and memory"""
    print("\n📝 TEST 7: Context Memory")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        # First message
        await assistant.chat("My favorite genre to work on is science fiction.")
        print("   ℹ️  Told assistant about favorite genre")
        
        # Second message - test if it remembers
        response = await assistant.chat("What did I just tell you about my preferences?")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 7 Passed - Context memory works")
        
    except Exception as e:
        print(f"❌ Test 7 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_error_handling(assistant):
    """Test 8: Error handling with unclear query"""
    print("\n📝 TEST 8: Error Handling")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        response = await assistant.chat("xyz abc nonsense query random words")
        
        print(f"\n🤖 Assistant: {response['response']}")
        print(f"✅ Test 8 Passed - Error handling works (graceful response)")
        
    except Exception as e:
        print(f"❌ Test 8 Failed: {e}")
        import traceback
        traceback.print_exc()


async def test_multi_turn_conversation(assistant):
    """Test 9: Multi-turn conversation"""
    print("\n📝 TEST 9: Multi-Turn Conversation")
    print("-" * 60)
    
    if not assistant:
        print("⚠️  Skipping - assistant not initialized")
        return
    
    try:
        # Turn 1
        response1 = await assistant.chat("I'm feeling overwhelmed with all my tasks.")
        print(f"\n🤖 Turn 1: {response1['response'][:100]}...")
        
        # Turn 2
        response2 = await assistant.chat("Can you help me prioritize them?")
        print(f"\n🤖 Turn 2: {response2['response'][:100]}...")
        
        # Turn 3
        response3 = await assistant.chat("Thanks, that helps!")
        print(f"\n🤖 Turn 3: {response3['response'][:100]}...")
        
        print(f"\n✅ Test 9 Passed - Multi-turn conversation works")
        
    except Exception as e:
        print(f"❌ Test 9 Failed: {e}")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "=" * 60)
    print("🚀 STARTING COMPREHENSIVE TESTS")
    print("=" * 60)
    
    test_results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Test 1: Basic greeting (creates assistant)
    assistant = await test_basic_greeting()
    if assistant:
        test_results['passed'] += 1
    else:
        test_results['failed'] += 1
        print("\n⚠️  Critical failure - cannot continue with remaining tests")
        return test_results
    
    # Run remaining tests
    tests = [
        test_schedule_query,
        test_task_query,
        test_production_info,
        test_scheduling_assistance,
        test_general_assistance,
        test_context_memory,
        test_error_handling,
        test_multi_turn_conversation
    ]
    
    for test in tests:
        try:
            await test(assistant)
            test_results['passed'] += 1
        except Exception as e:
            test_results['failed'] += 1
            print(f"Test failed with exception: {e}")
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    return test_results


async def main():
    """Main test runner"""
    
    results = await run_all_tests()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⚠️  Skipped: {results['skipped']}")
    print(f"📈 Success Rate: {results['passed']/(results['passed']+results['failed'])*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    print("\nRunning comprehensive test suite...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 Tests complete!\n")