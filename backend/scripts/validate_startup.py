#!/usr/bin/env python3
"""CLI tool for validating backend startup configuration"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.startup_validation import (
    check_env_file, validate_config, check_mysql, check_redis,
    check_mongodb, check_rabbitmq
)

def main():
    print("=" * 60)
    print("Backend Startup Validation")
    print("=" * 60)
    print()
    
    checks = [
        ("Environment file", check_env_file),
        ("Configuration", validate_config),
        ("MySQL", check_mysql),
        ("Redis", check_redis),
        ("MongoDB", check_mongodb),
        ("RabbitMQ", check_rabbitmq),
    ]
    
    results = []
    for name, check in checks:
        try:
            result = check()
            results.append(result)
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {name}")
        except Exception as e:
            results.append(False)
            print(f"[FAIL] {name}: {e}")
    
    print()
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[OK] All checks passed ({passed}/{total})")
        sys.exit(0)
    else:
        print(f"[FAIL] {total - passed} check(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
