import mimetypes
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from .models import Listing


def flyer_listing_image_proxy_view(request, listing_id):
    """
    Serves a listing's cover photo from the same origin (naijasale.com)
    so mobile Safari / iPhone <canvas> can render it into a WhatsApp Status
    flyer without cross-origin (CORS) blocking.
    """
    listing = get_object_or_404(Listing, id=listing_id)
    cover = listing.images.filter(is_cover=True).first() or listing.images.first()
    if not cover or not cover.image:
        raise Http404("No image available")

    try:
        with cover.image.open("rb") as img_file:
            data = img_file.read()
        content_type, _ = mimetypes.guess_type(cover.image.name)
        response = HttpResponse(data, content_type=content_type or "image/jpeg")
        response["Cache-Control"] = "public, max-age=3600"
        return response
    except Exception:
        raise Http404("Unable to read listing image")