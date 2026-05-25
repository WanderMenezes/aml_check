from rest_framework.permissions import BasePermission

from apps.users.models import UserRole


class RolePermission(BasePermission):
    allowed_roles: set[str] = set()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in self.allowed_roles or request.user.is_superuser


class IsAdmin(RolePermission):
    allowed_roles = {UserRole.ADMIN}


class IsComplianceTeam(RolePermission):
    allowed_roles = {UserRole.ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.ANALYST}


class IsAnyRole(RolePermission):
    allowed_roles = {
        UserRole.ADMIN,
        UserRole.COMPLIANCE_OFFICER,
        UserRole.ANALYST,
        UserRole.VIEWER,
    }
