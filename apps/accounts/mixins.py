# apps/accounts/mixins.py

from django.core.exceptions import PermissionDenied

class AdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_admin:  # 👈 sen yozgan property ishlayapti
            raise PermissionDenied  # 🔥 403

        return super().dispatch(request, *args, **kwargs)