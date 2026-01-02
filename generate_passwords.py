#!/usr/bin/env python3
"""
Generate hashed passwords for auth.yaml
Run this once to set up passwords for martin and christoph
"""

import streamlit_authenticator as stauth

print("=== MatchHub Password Generator ===\n")

# Generate hashed passwords
passwords = {
    "martin": "martin123",      # Change these to your desired passwords
    "christoph": "christoph123"
}

print("Kopiere diese Hashes in data/auth.yaml:\n")

for username, password in passwords.items():
    hashed = stauth.Hasher.hash(password)
    print(f"{username}:")
    print(f"  password: {hashed}")
    print()

print("---")
print("WICHTIG: Ändere die Passwörter in diesem Script vor dem Hashen!")
print("Dann lösche dieses Script oder speichere es sicher.")
