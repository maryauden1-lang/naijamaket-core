import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse


# ==========================================
# 1. SITE CONFIGURATION & CMS
# ==========================================
class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default="Naijamaket")
    tagline = models.CharField(max_length=255, default="Nigeria's Cleanest Buying & Selling Hub")
    logo = models.ImageField(
        upload_to="site_logos/", 
        blank=True, 
        null=True, 
        help_text="Upload website logo (PNG, SVG, or WebP with transparent background)"
    )
    support_phone = models.CharField(max_length=20, default="+2348000000000")
    support_whatsapp = models.CharField(max_length=20, default="2348000000000")
    support_email = models.EmailField(default="support@naijamaket.com")
    office_address = models.CharField(max_length=255, default="Lagos, Nigeria")
    
    # Social links
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    
    # Alert banner
    announcement_text = models.CharField(
        max_length=255, 
        blank=True, 
        default="⚠️ Tip: Always inspect goods physically in a public location before making payment."
    )
    show_announcement = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Global Site Setting"
        verbose_name_plural = "Global Site Settings"

    def __str__(self):
        return f"{self.site_name} Settings"


class StaticPage(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, help_text="e.g. safety-tips, privacy-policy")
    content = models.TextField(help_text="Full page content or HTML")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Custom Page (Terms, Safety, etc.)"
        verbose_name_plural = "Custom Pages"

    def get_absolute_url(self):
        try:
            return reverse('marketplace:static_page', kwargs={'slug': self.slug})
        except Exception:
            return f"/page/{self.slug}/"

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


# ==========================================
# 2. LOCATIONS (STATES & COMMERCIAL HUBS)
# ==========================================
class State(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Area(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="areas")
    name = models.CharField(max_length=100, help_text="e.g. Computer Village, Ikeja, Lekki Phase 1, Wuse 2")
    slug = models.SlugField(max_length=120, blank=True)
    is_popular = models.BooleanField(default=False, help_text="Show in popular quick-filters")

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.state.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.state.name})"


# ==========================================
# 3. CATEGORIES & SUBCATEGORIES
# ==========================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.ImageField(upload_to="category_icons/", blank=True, null=True, help_text="Upload small PNG, WebP, or SVG icon")
    icon_name = models.CharField(max_length=50, default="tag", blank=True, help_text="Fallback icon name")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        try:
            return reverse('marketplace:category_detail', kwargs={'slug': self.slug})
        except Exception:
            return f"/category/{self.slug}/"

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    icon = models.ImageField(upload_to="subcategory_icons/", blank=True, null=True, help_text="Upload small subcategory icon")

    class Meta:
        verbose_name_plural = "Sub-Categories"
        unique_together = ("category", "name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.name}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        try:
            return reverse('marketplace:subcategory_detail', kwargs={'slug': self.slug})
        except Exception:
            return f"/category/{self.category.slug}/{self.slug}/"

    def __str__(self):
        return f"{self.category.name} > {self.name}"


# ==========================================
# 4. USER PROFILES, STOREFRONTS & REVIEWS
# ==========================================
class SellerProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = (
        ("unverified", "Unverified"),
        ("pending", "Pending Verification Review"),
        ("verified", "Verified"),
        ("rejected", "Verification Rejected"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Storefront Customization
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    store_banner = models.ImageField(upload_to="store_banners/", blank=True, null=True, help_text="Cover banner for store profile")
    shop_address = models.CharField(max_length=255, blank=True, null=True, help_text="Physical store address (e.g. Shop B4, Banex Plaza)")
    
    # Social Media Handles
    facebook_handle = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. facebook.com/username or @username")
    instagram_handle = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. @username")
    tiktok_handle = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. @username")
    
    # Verification & Admin Controls
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default="unverified")
    is_nin_verified = models.BooleanField(default=False, verbose_name="NIN Verified Badge")
    is_cac_verified = models.BooleanField(default=False, verbose_name="CAC Business Verified")
    id_document = models.FileField(upload_to="verifications/", blank=True, null=True, help_text="NIN Slip or ID card for review")
    selfie_image = models.ImageField(upload_to="selfies/", blank=True, null=True, help_text="Live captured camera selfie")
    cac_document = models.FileField(upload_to="cac_verifications/", blank=True, null=True, help_text="CAC Certificate")
    verification_feedback = models.TextField(blank=True, null=True, help_text="Feedback or rejection notes from CEO/admin")
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Verification Queue Locking (For Staff)
    verification_locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="locked_verifications")
    verification_locked_at = models.DateTimeField(null=True, blank=True)
    
    bio = models.TextField(blank=True, null=True)
    response_time = models.CharField(max_length=50, default="Replies typically within 1 hour")
    is_banned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({'Verified' if self.is_nin_verified else self.get_verification_status_display()})"


class SellerReview(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_reviews")
    rating = models.PositiveSmallIntegerField(default=5, help_text="Rating 1 to 5")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.seller.username} by {self.reviewer.username} ({self.rating}★)"


# ==========================================
# 5. LISTINGS & MULTI-IMAGE MANAGEMENT
# ==========================================
class ListingQuerySet(models.QuerySet):
    def live_and_promoted_first(self):
        """
        Orders results so that active promoted listings sit at the top.
        Expired promotions transparently demote to standard chronological order.
        """
        now = timezone.now()
        return self.annotate(
            active_boost=models.Case(
                models.When(
                    is_featured=True,
                    featured_until__gt=now,
                    then=models.Value(1)
                ),
                default=models.Value(0),
                output_field=models.IntegerField(),
            )
        ).order_by('-active_boost', '-created_at')


class ListingManager(models.Manager):
    def get_queryset(self):
        return ListingQuerySet(self.model, using=self._db)

    def live_and_promoted_first(self):
        return self.get_queryset().live_and_promoted_first()


class Listing(models.Model):
    CONDITION_CHOICES = (
        ("brand_new", "Brand New"),
        ("tokunbo", "Foreign Used (Tokunbo)"),
        ("nigerian_used", "Nigerian Used"),
    )

    STATUS_CHOICES = (
        ("active", "Active / Approved"),
        ("pending", "Pending Moderation"),
        ("rejected", "Rejected"),
        ("sold", "Sold"),
    )

    PROMOTION_BADGE_CHOICES = (
        ("TOP_AD", "Top Ad"),
        ("FEATURED", "Featured"),
        ("URGENT", "Urgent"),
    )

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="listings")
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="listings")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # In Naira
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True, null=True, default="tokunbo")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True)
    
    # Dynamic JSON Metadata for Category-Specific Attributes (Jobs, Property, Vehicles)
    extra_fields = models.JSONField(default=dict, blank=True)
    
    # Status & Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.CharField(max_length=255, blank=True, null=True)
    
    # Monetization & Top Promotion Placement
    is_featured = models.BooleanField(default=False, db_index=True)
    featured_until = models.DateTimeField(blank=True, null=True, db_index=True)
    promotion_badge = models.CharField(
        max_length=20, 
        choices=PROMOTION_BADGE_CHOICES, 
        default="FEATURED", 
        blank=True
    )

    views_count = models.PositiveIntegerField(default=0)
    
    # Automated Staff Queue Locking System
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="locked_listings")
    locked_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_listings")
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ListingManager()

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Listing.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        try:
            return reverse('marketplace:listing_detail', kwargs={'slug': self.slug})
        except Exception:
            return f"/listing/{self.slug}/"

    def is_locked(self):
        """Check if listing is currently locked by a staff member for less than 10 minutes"""
        if self.locked_by and self.locked_at:
            return (timezone.now() - self.locked_at).total_seconds() < 600
        return False

    @property
    def is_currently_featured(self) -> bool:
        """Determines active status against real-time clock without database write locks"""
        if self.is_featured and self.featured_until:
            return timezone.now() < self.featured_until
        return False

    @property
    def is_job(self):
        if not self.category:
            return False
        return "job" in self.category.slug.lower()

    @property
    def is_property(self):
        if not self.category:
            return False
        return "prop" in self.category.slug.lower() or "real-estate" in self.category.slug.lower()

    @property
    def salary_display(self):
        if self.is_job and self.extra_fields:
            min_sal = self.extra_fields.get("min_salary")
            max_sal = self.extra_fields.get("max_salary")
            if min_sal and max_sal:
                return f"₦{int(float(min_sal)):,} - ₦{int(float(max_sal)):,}"
            elif min_sal:
                return f"From ₦{int(float(min_sal)):,}"
            elif max_sal:
                return f"Up to ₦{int(float(max_sal)):,}"
        return f"₦{self.price:,.2f}"

    def __str__(self):
        return f"{self.title} - ₦{self.price} ({self.get_status_display()})"


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="listings/%Y/%m/")
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_cover", "id"]

    def __str__(self):
        return f"Image for {self.listing.title}"


# ==========================================
# 6. SAVED ADS / FAVORITES WISHLIST
# ==========================================
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "listing")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} saved {self.listing.title}"


# ==========================================
# 7. IN-APP MESSAGING SYSTEM (REAL-TIME CHAT & OFFERS)
# ==========================================
class Conversation(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="conversations", null=True, blank=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        item_title = self.listing.title if self.listing else "Support & System Message"
        return f"Chat for {item_title} ({self.buyer.username} & {self.seller.username})"


class Message(models.Model):
    MESSAGE_TYPES = (
        ("text", "Standard Message"),
        ("offer", "Price Offer"),
    )
    OFFER_STATUS = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Offer negotiation additions
    msg_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default="text")
    offer_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    offer_status = models.CharField(max_length=10, choices=OFFER_STATUS, default="pending")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.sender.username} at {self.created_at.strftime('%H:%M')}"


# ==========================================
# 8. SAFETY, FRAUD & REPORTING
# ==========================================
class ReportedListing(models.Model):
    REPORT_REASONS = (
        ("fraud", "Suspected Scam / Fraud"),
        ("fake_price", "Fake / Unrealistic Price"),
        ("prohibited", "Prohibited / Illegal Item"),
        ("unavailable", "Item is already sold / not available"),
        ("abusive_behavior", "Abusive / Harassing Seller Behavior"),
        ("counterfeit", "Counterfeit or Fake Product"),
        ("other", "Other Safety Concern"),
    )

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=50, choices=REPORT_REASONS)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_reports")
    resolution_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report: {self.listing.title} ({self.get_reason_display()})"


# ==========================================
# 9. ENTERPRISE STAFF WORKSPACE & AUDIT ENGINE
# ==========================================
class StaffProfile(models.Model):
    ROLE_CHOICES = (
        ("moderator", "Ad Reviewer / Content Moderator"),
        ("verification_officer", "KYC & Identity Verification Officer"),
        ("customer_support", "Customer Support & Dispute Handler"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="moderator")
    employee_id = models.CharField(max_length=20, unique=True, help_text="e.g. NM-STF-001")
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Instant CEO Kill-Switch: Untick to lock staff out immediately")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} [{self.get_role_display()}]"


class StaffActivityLog(models.Model):
    ACTION_CHOICES = (
        ("approve_ad", "Approved Listing"),
        ("reject_ad", "Rejected Listing"),
        ("verify_nin", "Approved NIN Verification"),
        ("reject_nin", "Rejected NIN Verification"),
        ("resolve_report", "Resolved Dispute / Report"),
        ("ban_user", "Suspended / Banned User Account"),
        ("unban_user", "Reactivated User Account"),
    )

    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="staff_logs")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_object_id = models.CharField(max_length=100, help_text="ID or Title of the Ad/User touched")
    details = models.TextField(help_text="Details, feedback, or rejection reasons given")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Staff Activity Audit Log"
        verbose_name_plural = "Staff Activity Audit Logs"

    def __str__(self):
        return f"{self.staff.username} -> {self.get_action_display()} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# ==========================================
# 10. MONETIZATION, TOP ADS & PAYMENT LEDGER
# ==========================================
class PromotionPlan(models.Model):
    """
    Tiered promotion plans for sellers to boost their ads to the top.
    """
    BADGE_CHOICES = (
        ("TOP_AD", "Top Ad"),
        ("FEATURED", "Featured"),
        ("URGENT", "Urgent"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. 7-Day Top Placement")
    duration_days = models.PositiveIntegerField(help_text="Duration in days (e.g. 3, 7, 30)")
    price_ngn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Price in Nigerian Naira"
    )
    price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Price in USD (for international/crypto payments)"
    )
    badge_type = models.CharField(max_length=20, choices=BADGE_CHOICES, default="FEATURED")
    description = models.TextField(blank=True, help_text="Short description of benefits")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price_ngn"]
        verbose_name = "Promotion Plan"
        verbose_name_plural = "Promotion Plans"

    def __str__(self):
        return f"{self.name} - ₦{self.price_ngn:,.2f} ({self.duration_days} Days)"


class PaymentTransaction(models.Model):
    """
    Audit-proof transaction ledger tracking every single monetization payment.
    """
    GATEWAY_CHOICES = (
        ("PAYSTACK", "Paystack"),
        ("FLUTTERWAVE", "Flutterwave"),
        ("NOWPAYMENTS", "NowPayments (Crypto)"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESSFUL", "Successful"),
        ("FAILED", "Failed"),
        ("EXPIRED", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="Our unique merchant reference code"
    )
    gateway_reference = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        db_index=True,
        help_text="Reference returned by the payment gateway"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monetization_transactions"
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="The listing being promoted"
    )
    plan = models.ForeignKey(
        PromotionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    gateway = models.CharField(max_length=30, choices=GATEWAY_CHOICES, default="PAYSTACK")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    
    # Gateway response storage & audit
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full JSON payload received from payment gateway webhook/verification"
    )
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["gateway", "status"]),
        ]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"

    def __str__(self):
        return f"[{self.gateway}] {self.reference} - {self.currency} {self.amount_paid:,.2f} ({self.status})"