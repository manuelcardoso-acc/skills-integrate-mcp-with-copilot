# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign in with student, staff, or administrator accounts
- Sign up for activities and unregister according to the signed-in user's role
- Assign staff accounts to the activities they are allowed to manage
- Manage user accounts as an administrator

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a password hash for the initial administrator account from the `src` directory:

   ```
   python -c "from getpass import getpass; from auth import hash_password; print(hash_password(getpass()))"
   ```

3. Configure the initial administrator using its password hash (never put a plaintext password in this setting):

   ```sh
   export APP_USERS_JSON='[{"username":"admin","email":"admin@mergington.edu","role":"administrator","password_hash":"<paste-generated-hash>"}]'
   ```

4. Run the application from the `src` directory:

   ```
   uvicorn app:app --reload
   ```

5. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

For production, serve the application over HTTPS and provide `APP_USERS_JSON` through a protected environment configuration. Password hashes use PBKDF2-HMAC-SHA256 with a per-password random salt. API-created users and active sessions are held in memory and will be lost when the process restarts.

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/activities` | Public list of activities and participants |
| POST | `/auth/login` | Exchange a username and password for a bearer token |
| GET | `/auth/me` | Get the signed-in user's profile |
| POST | `/auth/logout` | Revoke the current in-memory session |
| POST | `/activities/{activity_name}/signup` | Sign up as a student, or register a participant as authorized staff |
| DELETE | `/activities/{activity_name}/unregister` | Unregister yourself as a student, or manage a participant as authorized staff |
| GET | `/users` | List accounts (administrator only; password hashes are never returned) |
| POST | `/users` | Create an account (administrator only) |

Include the login token as `Authorization: Bearer <token>` on protected requests. Students can only register or unregister their own account. Staff can manage participants only for assigned activities; administrators can manage users and all activity registrations. To create a staff account, include its assigned activity names in the administrator's `POST /users` request. New account passwords must be at least 12 characters.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
