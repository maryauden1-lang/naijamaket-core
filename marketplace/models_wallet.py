from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.core.validators import MinValueValidator


class UserWallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_deposited = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_spent = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    is_frozen = models.BooleanField(
        default=False,
        help_text="Freeze wallet debits/credits if suspicious activity is detected.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Wallet"
        verbose_name_plural = "User Wallets"

    def __str__(self):
        return f"{self.user.username} — ₦{self.balance:,.2f}"

    @classmethod
    def get_or_create_wallet(cls, user):
        wallet, _ = cls.objects.get_or_create(user=user)
        return wallet


class WalletTransaction(models.Model):
    TX_TYPE_CHOICES = (
        ("DEPOSIT", "Wallet Top-Up (Paystack)"),
        ("BOOST_SPEND", "Ad Promotion Payment"),
        ("REFUND", "Wallet Refund / Adjustment"),
    )
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESSFUL", "Successful"),
        ("FAILED", "Failed"),
    )

    reference = models.CharField(max_length=64, unique=True, db_index=True)
    wallet = models.ForeignKey(
        UserWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet_transactions",
    )
    tx_type = models.CharField(max_length=20, choices=TX_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],
    )
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.CharField(max_length=255)
    gateway_reference = models.CharField(max_length=120, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Wallet Ledger Entry"
        verbose_name_plural = "Wallet Ledger Entries"

    def __str__(self):
        return f"{self.reference} | {self.user.username} | {self.tx_type} | ₦{self.amount:,.2f} ({self.status})"