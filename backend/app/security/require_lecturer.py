from app.security.require_roles import require_roles
from app.security.roles import Role

require_lecturer = require_roles(Role.GIANG_VIEN)