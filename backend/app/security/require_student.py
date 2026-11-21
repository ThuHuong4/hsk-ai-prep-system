from app.security.require_roles import require_roles
from app.security.roles import Role

require_student = require_roles(Role.HOC_VIEN)
