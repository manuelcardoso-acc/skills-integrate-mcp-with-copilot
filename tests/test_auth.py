import copy
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import app as activities_app
from auth import AuthManager, User, hash_password


class AuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_activities = copy.deepcopy(activities_app.activities)

    def setUp(self):
        activities_app.activities = copy.deepcopy(self.initial_activities)
        activities_app.auth_manager = AuthManager(
            [
                User(
                    username="student",
                    email="student@mergington.edu",
                    role="student",
                    password_hash=hash_password("student-password"),
                ),
                User(
                    username="staff",
                    email="staff@mergington.edu",
                    role="staff",
                    password_hash=hash_password("staff-password"),
                    activities={"Chess Club"},
                ),
                User(
                    username="admin",
                    email="admin@mergington.edu",
                    role="administrator",
                    password_hash=hash_password("administrator-password"),
                ),
            ]
        )

    def test_activity_list_remains_public(self):
        self.assertIn("Chess Club", activities_app.get_activities())

    def test_student_cannot_register_or_unregister_another_student(self):
        student = activities_app.auth_manager.users["student"]

        with self.assertRaises(HTTPException) as signup_error:
            activities_app.signup_for_activity(
                "Chess Club", "other@mergington.edu", student
            )
        self.assertEqual(signup_error.exception.status_code, 403)

        with self.assertRaises(HTTPException) as unregister_error:
            activities_app.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", student
            )
        self.assertEqual(unregister_error.exception.status_code, 403)

        result = activities_app.signup_for_activity("Chess Club", None, student)
        self.assertIn("student@mergington.edu", result["message"])

    def test_staff_can_manage_only_assigned_activities(self):
        staff = activities_app.auth_manager.users["staff"]
        result = activities_app.signup_for_activity(
            "Chess Club", "new-student@mergington.edu", staff
        )
        self.assertIn("Signed up", result["message"])

        with self.assertRaises(HTTPException) as error:
            activities_app.signup_for_activity(
                "Art Club", "new-student@mergington.edu", staff
            )
        self.assertEqual(error.exception.status_code, 403)

    def test_admin_can_create_users_without_exposing_password_hash(self):
        admin = activities_app.auth_manager.users["admin"]
        request = activities_app.CreateUserRequest(
            username="new-staff",
            email="new-staff@mergington.edu",
            role="staff",
            password="a-strong-password",
            activities=["Chess Club"],
        )

        created = activities_app.create_user(request, admin)
        users = activities_app.list_users(admin)

        self.assertEqual(created["role"], "staff")
        self.assertEqual(created["activities"], ["Chess Club"])
        self.assertNotIn("password_hash", created)
        self.assertEqual(len(users), 4)

    def test_logout_revokes_the_session(self):
        token = activities_app.auth_manager.login("student", "student-password")
        self.assertIsNotNone(token)
        self.assertIsNotNone(activities_app.auth_manager.authenticate(token))

        activities_app.auth_manager.logout(token)

        self.assertIsNone(activities_app.auth_manager.authenticate(token))


if __name__ == "__main__":
    unittest.main()
