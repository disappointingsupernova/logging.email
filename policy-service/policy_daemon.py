#!/usr/bin/env python3
"""
Postfix policy service daemon.
Runs locally on MX host, queries backend API over TLS.
Fails closed on errors.
"""
import sys
import socket
import requests
import os

BACKEND_URL = os.environ.get('BACKEND_URL', 'https://api.logging.email')
API_TOKEN = os.environ.get('API_TOKEN')
BIND_ADDRESS = os.environ.get('BIND_ADDRESS', '127.0.0.1')
BIND_PORT = int(os.environ.get('BIND_PORT', '10040'))

if not API_TOKEN:
    print("ERROR: API_TOKEN environment variable not set", file=sys.stderr)
    sys.exit(1)

def check_recipient(recipient: str) -> tuple[str, str]:
    """
    Query backend policy API.
    Returns (action, message) tuple.
    Fails closed on any error.
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/policy/check",
            json={"recipient": recipient},
            headers={"X-API-Token": API_TOKEN},
            timeout=5,
            verify=True  # Always verify TLS
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('action', 'REJECT'), data.get('message', '')
        else:
            return 'REJECT', 'Policy check failed'
            
    except Exception as e:
        # Fail closed
        print(f"Policy check error: {e}", file=sys.stderr)
        return 'REJECT', 'Policy service unavailable'

def handle_request(data: dict) -> str:
    """Process Postfix policy request"""
    request_type = data.get('request')
    
    if request_type != 'smtpd_access_policy':
        return 'action=DUNNO\n\n'
    
    recipient = data.get('recipient', '').lower().strip()
    
    if not recipient:
        return 'action=REJECT Invalid recipient\n\n'
    
    action, message = check_recipient(recipient)
    
    if action == 'OK':
        return 'action=DUNNO\n\n'
    else:
        return f'action=REJECT {message}\n\n'

def parse_postfix_request(lines: list) -> dict:
    """Parse Postfix policy protocol request"""
    data = {}
    for line in lines:
        line = line.strip()
        if '=' in line:
            key, value = line.split('=', 1)
            data[key] = value
    return data

def handle_connection(conn: socket.socket):
    """Handle single policy request"""
    try:
        lines = []
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            decoded = data.decode('utf-8', errors='ignore')
            for line in decoded.split('\n'):
                if line.strip():
                    lines.append(line)
                else:
                    # Empty line signals end of request
                    if lines:
                        request = parse_postfix_request(lines)
                        response = handle_request(request)
                        conn.sendall(response.encode('utf-8'))
                        lines = []
    except Exception as e:
        print(f"Connection error: {e}", file=sys.stderr)
    finally:
        conn.close()

def main():
    """Run policy service daemon"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((BIND_ADDRESS, BIND_PORT))
    server.listen(5)
    
    print(f"Policy service listening on {BIND_ADDRESS}:{BIND_PORT}", file=sys.stderr)
    
    while True:
        try:
            conn, addr = server.accept()
            handle_connection(conn)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
    
    server.close()

if __name__ == '__main__':
    main()
