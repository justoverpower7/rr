#!/usr/bin/env python3
"""
Test tunnel connection
"""
import subprocess
import time
import threading

def test_serveo():
    print("Testing serveo connection...")
    
    process = subprocess.Popen(
        ['ssh', '-o', 'StrictHostKeyChecking=no', '-R', '80:localhost:5000', 'serveo.net'],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("Waiting for serveo URL...")
    
    # Read output
    for i, line in enumerate(process.stdout):
        print(f"Line {i}: {line.strip()}")
        if 'https://' in line and 'serveo.net' in line:
            url = line.strip()
            print(f"Found URL: {url}")
            break
        if i > 10:  # Limit output
            break
    
    return process

if __name__ == "__main__":
    # Start Flask server first
    print("Start Flask server on port 5000 first, then run this test")
    test_serveo()
