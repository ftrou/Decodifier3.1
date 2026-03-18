from app.api.routes.auth import login_user, refresh_session
from app.api.routes.projects import list_projects


ROUTES = {
    "POST /auth/login": login_user,
    "POST /auth/refresh": refresh_session,
    "GET /projects": list_projects,
}
