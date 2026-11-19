"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from auth import AuthManager, Role, User

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

auth_manager = AuthManager.from_environment()
for configured_user in auth_manager.users.values():
    unknown_activities = configured_user.activities.difference(activities)
    if unknown_activities:
        raise RuntimeError(
            f"User {configured_user.username} has unknown activity assignments: "
            f"{', '.join(sorted(unknown_activities))}"
        )

bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    role: Role
    password: str = Field(min_length=12, max_length=128)
    activities: list[str] = Field(default_factory=list)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_manager.authenticate(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_administrator(user: User = Depends(get_current_user)) -> User:
    if user.role != "administrator":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def require_activity_access(user: User, activity_name: str) -> None:
    if user.role == "staff" and activity_name not in user.activities:
        raise HTTPException(
            status_code=403,
            detail="Staff can only manage their assigned activities",
        )


def resolve_target_email(user: User, email: str | None, activity_name: str) -> str:
    if user.role == "student":
        if email is not None and email.casefold() != user.email.casefold():
            raise HTTPException(
                status_code=403,
                detail="Students can only manage their own registrations",
            )
        return user.email

    require_activity_access(user, activity_name)
    if not email:
        raise HTTPException(
            status_code=422,
            detail="An email address is required for staff and administrators",
        )
    return email


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(request: LoginRequest):
    token = auth_manager.login(request.username, request.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = auth_manager.authenticate(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Could not create session")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 8 * 60 * 60,
        "user": auth_manager.public_user(user),
    }


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    auth_manager.logout(credentials.credentials)
    return {"message": f"Logged out {user.username}"}


@app.get("/auth/me")
def get_authenticated_user(user: User = Depends(get_current_user)):
    return auth_manager.public_user(user)


@app.get("/users")
def list_users(_: User = Depends(require_administrator)):
    return [
        auth_manager.public_user(user)
        for user in sorted(auth_manager.users.values(), key=lambda item: item.username)
    ]


@app.post("/users", status_code=201)
def create_user(
    request: CreateUserRequest,
    _: User = Depends(require_administrator),
):
    if (
        "@" not in request.email
        or request.email.startswith("@")
        or request.email.endswith("@")
        or any(character.isspace() for character in request.email)
    ):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    if len(set(request.activities)) != len(request.activities):
        raise HTTPException(status_code=422, detail="Activity assignments must be unique")
    if any(activity not in activities for activity in request.activities):
        raise HTTPException(status_code=422, detail="Unknown activity assignment")
    if request.role != "staff" and request.activities:
        raise HTTPException(
            status_code=422,
            detail="Only staff accounts can have activity assignments",
        )

    try:
        user = auth_manager.create_user(
            username=request.username,
            email=request.email,
            role=request.role,
            password=request.password,
            activities=set(request.activities),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return auth_manager.public_user(user)


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str | None = None,
    user: User = Depends(get_current_user),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    email = resolve_target_email(user, email, activity_name)

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str | None = None,
    user: User = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    email = resolve_target_email(user, email, activity_name)

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
