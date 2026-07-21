class ReadOnlyAdminMixin:
    """Allow staff to inspect audit records without mutating or deleting them."""

    def has_add_permission(self, request) -> bool:  # type: ignore[no-untyped-def]
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # type: ignore[no-untyped-def]
        return request.method in {"GET", "HEAD", "OPTIONS"}
