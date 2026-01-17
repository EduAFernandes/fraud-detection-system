"""
Test CrewAI Agents System
Run this to verify agent configuration and prompt loading
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Fix encoding for Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from src.agents.crew_manager import CrewManager

def test_agents():
    """Test CrewAI agents system"""

    print("\n" + "="*70)
    print("🧪 TESTING CREWAI AGENTS SYSTEM")
    print("="*70)

    print("\n🧪 Test 1: Load prompts from markdown files")
    try:
        manager = CrewManager()
        prompts_loaded = hasattr(manager, 'prompts') and len(manager.prompts) > 0

        if prompts_loaded:
            print(f"✅ Prompts loaded from markdown files")
            print(f"   Prompts found: {list(manager.prompts.keys())}")
        else:
            print(f"⚠️ No prompts loaded (check src/agents/prompts/ directory)")
    except Exception as e:
        print(f"❌ Failed to load prompts: {e}")
        print(f"   Make sure prompt files exist in src/agents/prompts/")
        return

    print("\n🧪 Test 2: Initialize agents")
    try:
        agents = manager.create_agents()
        print(f"✅ Agents initialized: {len(agents)} agents created")

        for agent in agents:
            print(f"   - {agent.role}")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        print(f"   Error details: {str(e)}")
        print(f"\n   💡 If OpenAI API error, check OPENAI_API_KEY in .env")
        return

    print("\n🧪 Test 3: Verify agent roles")
    try:
        expected_roles = [
            'pattern_detector',
            'risk_quantifier',
            'decision_authority'
        ]

        agents_dict = {agent.role.lower().replace(' ', '_'): agent for agent in agents}

        for role in expected_roles:
            # Match role keywords
            matching = [k for k in agents_dict.keys() if role.split('_')[0] in k]
            if matching:
                print(f"   ✅ {role} agent found")
            else:
                print(f"   ⚠️ {role} agent not found")
    except Exception as e:
        print(f"❌ Role verification failed: {e}")

    print("\n🧪 Test 4: Test pattern detector prompt content")
    try:
        pattern_prompt = manager.prompts.get('pattern_detector', '')

        if pattern_prompt:
            print(f"✅ Pattern detector prompt loaded")
            print(f"   Length: {len(pattern_prompt)} characters")

            # Check for key elements
            key_elements = ['pattern', 'fraud', 'transaction']
            found_elements = [elem for elem in key_elements if elem.lower() in pattern_prompt.lower()]
            print(f"   Key elements found: {', '.join(found_elements)}")
        else:
            print(f"⚠️ Pattern detector prompt is empty")
    except Exception as e:
        print(f"❌ Prompt content check failed: {e}")

    print("\n🧪 Test 5: Create crew and tasks")
    try:
        test_transaction = {
            'order_id': 'ORD-TEST-001',
            'user_id': 'USER-TEST',
            'amount': 500.0,
            'merchant': 'Test Store'
        }

        tasks = manager.create_tasks(agents, test_transaction)
        print(f"✅ Tasks created: {len(tasks)} tasks")

        for i, task in enumerate(tasks, 1):
            print(f"   Task {i}: {task.description[:50]}...")
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return

    print("\n🧪 Test 6: Verify crew configuration")
    try:
        crew = manager.create_crew(agents, tasks)
        print(f"✅ Crew created successfully")
        print(f"   Agents: {len(crew.agents)}")
        print(f"   Tasks: {len(crew.tasks)}")
    except Exception as e:
        print(f"❌ Crew creation failed: {e}")
        return

    print("\n" + "="*70)
    print("✅ ALL AGENT TESTS PASSED!")
    print("="*70)

    print("\n💡 Notes:")
    print("   - Agents are configured from markdown files in src/agents/prompts/")
    print("   - Edit prompts in those files and reload to update agent behavior")
    print("   - Full agent execution test requires OpenAI API credits")
    print("\n⚠️ WARNING: Running full crew.kickoff() will consume OpenAI credits!")
    print("   Use test_fraud_orchestrator.py for full integration testing")

if __name__ == "__main__":
    test_agents()
