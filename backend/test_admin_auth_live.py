"""
Live integration tests for the admin auth endpoints.
Requires the backend to be running at http://localhost:8000.
Default test password: AdminAJU2026!  (set via ADMIN_PASSWORD_HASH in .env)
"""
import json
import sys
import requests

BASE = "http://localhost:8000"
PASSWORD = "AdminAJU2026!"

def ok(label): print(f"  PASS  {label}")
def fail(label, detail): print(f"  FAIL  {label}: {detail}"); return 1


def run():
    errors = 0
    token = None

    # 1. Health check
    r = requests.get(f"{BASE}/health")
    if r.status_code == 200:
        ok("Health check")
    else:
        errors += fail("Health check", r.text)

    # 2. Unauthenticated /me → must 401
    r = requests.get(f"{BASE}/api/v1/admin/auth/me")
    if r.status_code == 401:
        ok("Unauthenticated /me → 401")
    else:
        errors += fail("Unauthenticated /me", f"got {r.status_code}")

    # 3. Login with wrong password → must 401
    r = requests.post(f"{BASE}/api/v1/admin/auth/login", json={"password": "wrongpassword"})
    if r.status_code == 401:
        ok("Wrong password → 401")
    else:
        errors += fail("Wrong password", f"got {r.status_code}")

    # 4. Login with correct password → must 200 + token
    r = requests.post(f"{BASE}/api/v1/admin/auth/login", json={"password": PASSWORD})
    if r.status_code == 200 and "access_token" in r.json():
        token = r.json()["access_token"]
        ok("Correct password → 200 + token")
    else:
        errors += fail("Login", f"got {r.status_code}: {r.text}")
        print(f"\n{'='*50}\nAUTH TESTS: 0 passed, {errors} failed (cannot continue without token)\n{'='*50}")
        return errors

    auth_headers = {"Authorization": f"Bearer {token}"}

    # 5. Authenticated /me → must 200
    r = requests.get(f"{BASE}/api/v1/admin/auth/me", headers=auth_headers)
    if r.status_code == 200 and r.json().get("authenticated"):
        ok("Authenticated /me → 200")
    else:
        errors += fail("Authenticated /me", f"got {r.status_code}: {r.text}")

    # 6. Forged/invalid token → must 401
    r = requests.get(f"{BASE}/api/v1/admin/auth/me", headers={"Authorization": "Bearer forged.jwt.token"})
    if r.status_code == 401:
        ok("Forged token → 401")
    else:
        errors += fail("Forged token", f"got {r.status_code}")

    # 7. Password change: wrong current password → must 400
    r = requests.post(
        f"{BASE}/api/v1/admin/auth/password",
        headers=auth_headers,
        json={"current_password": "wrongcurrent", "new_password": "NewPassword123!"}
    )
    if r.status_code == 400:
        ok("Wrong current password on change → 400")
    else:
        errors += fail("Bad current password", f"got {r.status_code}: {r.text}")

    # 8. Password change: too short → must 400
    r = requests.post(
        f"{BASE}/api/v1/admin/auth/password",
        headers=auth_headers,
        json={"current_password": PASSWORD, "new_password": "short"}
    )
    if r.status_code == 400:
        ok("Short new password → 400")
    else:
        errors += fail("Short password", f"got {r.status_code}: {r.text}")

    # 9. Password change: same as current → must 400
    r = requests.post(
        f"{BASE}/api/v1/admin/auth/password",
        headers=auth_headers,
        json={"current_password": PASSWORD, "new_password": PASSWORD}
    )
    if r.status_code == 400:
        ok("Same password → 400")
    else:
        errors += fail("Same password", f"got {r.status_code}: {r.text}")

    # 10. Valid password change
    NEW_PASSWORD = "AJUAdmin2026!New"
    r = requests.post(
        f"{BASE}/api/v1/admin/auth/password",
        headers=auth_headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    )
    if r.status_code == 200:
        ok("Password change → 200")
    else:
        errors += fail("Password change", f"got {r.status_code}: {r.text}")
        # Restore and stop further tests
        print(f"\n{'='*50}\nNote: password change failed, skipping session invalidation tests\n{'='*50}")
    
    # 11. Old token should now be invalid (password_changed_at updated)
    r = requests.get(f"{BASE}/api/v1/admin/auth/me", headers=auth_headers)
    if r.status_code == 401:
        ok("Old token invalidated after password change → 401")
    else:
        errors += fail("Old token still valid after password change", f"got {r.status_code}")

    # 12. Old password should fail
    r = requests.post(f"{BASE}/api/v1/admin/auth/login", json={"password": PASSWORD})
    if r.status_code == 401:
        ok("Old password rejected after change → 401")
    else:
        errors += fail("Old password still works", f"got {r.status_code}")

    # 13. New password should succeed
    r = requests.post(f"{BASE}/api/v1/admin/auth/login", json={"password": NEW_PASSWORD})
    if r.status_code == 200 and "access_token" in r.json():
        new_token = r.json()["access_token"]
        ok("New password login → 200")
    else:
        errors += fail("New password login", f"got {r.status_code}: {r.text}")
        print(f"\n{'='*50}\nAUTH TESTS: errors={errors}\n{'='*50}")
        return errors

    new_headers = {"Authorization": f"Bearer {new_token}"}

    # 14. Logout
    r = requests.post(f"{BASE}/api/v1/admin/auth/logout", headers=new_headers)
    if r.status_code == 200:
        ok("Logout → 200")
    else:
        errors += fail("Logout", f"got {r.status_code}")

    # 15. RESTORE: reset password back to original for repeatability
    r2 = requests.post(f"{BASE}/api/v1/admin/auth/login", json={"password": NEW_PASSWORD})
    if r2.status_code == 200:
        restore_token = r2.json()["access_token"]
        r3 = requests.post(
            f"{BASE}/api/v1/admin/auth/password",
            headers={"Authorization": f"Bearer {restore_token}"},
            json={"current_password": NEW_PASSWORD, "new_password": PASSWORD}
        )
        if r3.status_code == 200:
            ok("Password restored to original (cleanup)")
        else:
            print(f"  WARN  Password restore failed: {r3.text} (run manually if needed)")

    total = 15
    passed = total - errors
    print(f"\n{'='*50}")
    print(f"AUTH TESTS: {passed} passed, {errors} failed")
    print(f"{'='*50}")
    return errors


if __name__ == "__main__":
    print("Running admin auth integration tests against http://localhost:8000 ...\n")
    sys.exit(run())
