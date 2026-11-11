from app.security.require_roles import require_roles
from app.security.roles import Role

require_admin = require_roles(Role.QUAN_TRI_VIEN)