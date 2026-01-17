"""
Quick Start Test Script
Run this first to verify basic setup before running full test suite
"""

import sys
import os
import subprocess

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

def check_python_version():
    """Check Python version"""
    print("\n🐍 Checking Python version...")

    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro}")
        print(f"   Required: Python 3.9 or higher")
        return False

def check_docker():
    """Check if Docker is installed and running"""
    print("\n🐳 Checking Docker...")

    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {result.stdout.strip()}")

            # Try to ping docker daemon
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Docker daemon is running")
                return True
            else:
                print(f"   ⚠️ Docker is installed but daemon is not running")
                print(f"   Start Docker Desktop and try again")
                return False
        else:
            print(f"   ❌ Docker not found")
            return False
    except FileNotFoundError:
        print(f"   ❌ Docker not installed")
        print(f"   Install from: https://www.docker.com/products/docker-desktop")
        return False

def check_env_file():
    """Check if .env file exists"""
    print("\n⚙️ Checking environment configuration...")

    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_example_path = os.path.join(os.path.dirname(__file__), '..', '.env.example')

    if os.path.exists(env_path):
        print(f"   ✅ .env file exists")

        # Check for required variables
        from dotenv import load_dotenv
        load_dotenv(env_path)

        required_vars = [
            'OPENAI_API_KEY',
            'KAFKA_BOOTSTRAP_SERVERS',
            'POSTGRES_CONNECTION_STRING'
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            print(f"   ⚠️ Missing required variables: {', '.join(missing)}")
            print(f"   Edit .env and add these variables")
            return False
        else:
            print(f"   ✅ All required variables are set")
            return True

    else:
        print(f"   ❌ .env file not found")
        if os.path.exists(env_example_path):
            print(f"   💡 Copy .env.example to .env and fill in your credentials:")
            print(f"      cp .env.example .env")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n📦 Checking Python dependencies...")

    required_packages = [
        'redis',
        'qdrant_client',
        'openai',
        'crewai',
        'confluent_kafka',
        'psycopg2',
        'dotenv'  # python-dotenv package, but imports as 'dotenv'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)

    if missing:
        print(f"\n   💡 Install missing packages:")
        print(f"      pip install {' '.join(missing)}")
        print(f"   OR install all requirements:")
        print(f"      pip install -r requirements.txt")
        return False
    else:
        return True

def check_docker_services():
    """Check if Docker services are running"""
    print("\n🔧 Checking Docker services...")

    try:
        # Check for Redis
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=redis-fraud', '--format', '{{.Names}}'],
            capture_output=True,
            text=True
        )

        if 'redis-fraud' in result.stdout:
            print(f"   ✅ Redis container running")
            redis_running = True
        else:
            print(f"   ⚠️ Redis container not running")
            redis_running = False

        # Check for Qdrant
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=qdrant-fraud', '--format', '{{.Names}}'],
            capture_output=True,
            text=True
        )

        if 'qdrant-fraud' in result.stdout:
            print(f"   ✅ Qdrant container running")
            qdrant_running = True
        else:
            print(f"   ⚠️ Qdrant container not running")
            qdrant_running = False

        if not redis_running or not qdrant_running:
            print(f"\n   💡 Start services:")
            print(f"      cd projC")
            print(f"      docker-compose up -d redis qdrant")
            return False
        else:
            return True

    except Exception as e:
        print(f"   ❌ Error checking Docker services: {e}")
        return False

def quick_start_test():
    """Run quick start tests"""

    print("\n" + "="*70)
    print("🚀 QUICK START TEST - Option C Fraud Detection")
    print("="*70)

    print("\nThis script will verify your basic setup before running full tests.\n")

    results = {}

    # Run checks
    results['python'] = check_python_version()
    results['docker'] = check_docker()
    results['env'] = check_env_file()
    results['dependencies'] = check_dependencies()
    results['services'] = check_docker_services()

    # Summary
    print("\n" + "="*70)
    print("📊 QUICK START TEST SUMMARY")
    print("="*70)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check.upper():<20} {status}")

    print("="*70)

    if all_passed:
        print("\n✅ ALL CHECKS PASSED!")
        print("\n🎉 Your environment is ready!")
        print("\n📝 Next steps:")
        print("   1. Run unit tests:")
        print("      python tests/test_redis_memory.py")
        print("      python tests/test_qdrant_knowledge.py")
        print("\n   2. Run full test suite:")
        print("      python tests/run_all_tests.py")
        print("\n   3. Start fraud detection:")
        print("      docker-compose up -d")

        return 0
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\n💡 Fix the issues above and run this script again")
        print("\n🔧 Common fixes:")

        if not results['python']:
            print("   - Install Python 3.9+: https://www.python.org/downloads/")

        if not results['docker']:
            print("   - Install Docker: https://www.docker.com/products/docker-desktop")

        if not results['env']:
            print("   - Create .env file: cp .env.example .env")
            print("   - Edit .env and add your API keys")

        if not results['dependencies']:
            print("   - Install packages: pip install -r requirements.txt")

        if not results['services']:
            print("   - Start services: docker-compose up -d redis qdrant")

        return 1

if __name__ == "__main__":
    exit_code = quick_start_test()
    sys.exit(exit_code)
