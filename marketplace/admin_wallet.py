from django.contrib import admin
from .models_wallet import UserWallet, WalletTransaction


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "total_deposited", "total_spent", "is_frozen", "updated_at")
    search_fields = ("user__username", "user__email")
    list_filter = ("is_frozen",)
    readonly_fields = ("user", "balance", "total_deposited", "total_spent", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "user",
        "tx_type",
        "amount",
        "balance_before",
        "balance_after",
        "status",
        "created_at",
    )
    list_filter = ("tx_type", "status", "created_at")
    search_fields = ("reference", "gateway_reference", "user__username", "user__email", "description")
    readonly_fields = (
        "reference",
        "wallet",
        "user",
        "tx_type",
        "status",
        "amount",
        "balance_before",
        "balance_after",
        "description",
        "gateway_reference",
        "ip_address",
        "created_at",
        "completed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False