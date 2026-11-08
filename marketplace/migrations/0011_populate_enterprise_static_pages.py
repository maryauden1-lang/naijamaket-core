from django.db import migrations

def create_static_pages(apps, schema_editor):
    StaticPage = apps.get_model('marketplace', 'StaticPage')
    pages = {
        'about-us': {
            'title': "About Naijasale | Nigeria's Verified Digital Marketplace",
            'content': "<h2>Empowering Seamless Commerce Across Nigeria</h2><p><strong>Naijasale</strong> is an enterprise peer-to-peer commerce and classifieds ecosystem engineered to bridge the gap between verified local sellers, artisans, and discerning consumers across all 36 states and the FCT.</p><h3>Our Core Mission</h3><p>We solve the critical friction points of modern e-commerce in West Africa: <strong>transparency, verified identity, and secure communication</strong>. We provide individuals, registered MSMEs, and independent merchants with institutional-grade digital storefront tools, leveling the playing field for authentic Nigerian business.</p>"
        },
        'safety-tips': {
            'title': 'Trust, Security & Safe Trading Architecture',
            'content': "<h2>Our Commitment to Customer Protection</h2><p>At Naijasale, trust is not an afterthought—it is the foundation of our engineering. We actively deploy fraud monitoring heuristics and community moderation protocols to ensure a safe, legitimate trading venue for all participants.</p><h3>The Golden Rules for Safe Transactions</h3><ol><li><strong>Inspect First, Pay Second:</strong> Never transfer funds, issue mobile money deposits, or send delivery fees in advance of physically inspecting the item.</li><li><strong>Meet in High-Traffic Public Locations:</strong> Complete face-to-face handovers in well-lit, public environments with security.</li><li><strong>Keep All Correspondence on Naijasale:</strong> Communicate strictly through the Naijasale chat.</li></ol>"
        },
        'terms-of-service': {
            'title': 'Terms of Service & User Covenant',
            'content': '<h2>Contractual Agreement & Operating Standards</h2><p>By accessing or interacting with the Naijasale platform ("Service"), you enter into a binding agreement governed by the laws of the Federal Republic of Nigeria.</p><h3>1. User Verification & Account Integrity</h3><p>Users must provide accurate, verifiable identity details upon registration.</p><h3>2. Prohibited Items</h3><p>Zero tolerance for stolen property, counterfeits, drugs, weapons, or predatory schemes.</p>'
        },
        'privacy-policy': {
            'title': 'Global Privacy Policy & Data Governance',
            'content': '<h2>Data Protection Compliance Statement</h2><p>Naijasale upholds international information security frameworks and requirements under the <strong>Nigeria Data Protection Act (NDPA)</strong>.</p><h3>Zero-Sale Data Guarantee</h3><p>Your personal information is processed strictly to enable secure trading. <strong>Naijasale never sells, rents, or monetizes user databases.</strong></p>'
        },
        'seller-verification': {
            'title': 'Seller Verification & Merchant Standards',
            'content': '<h2>Verified Merchant Framework</h2><p>The <strong>Naijasale Verified Seller</strong> program builds trust, reduces fraud, and helps legitimate merchants stand out to buyers nationwide.</p><h3>Verification Steps</h3><ol><li>Account & phone binding via OTP.</li><li>Valid government ID verification (NIN, Drivers License, Voters Card, Passport).</li><li>Business registration confirmation (CAC) for commercial vendors.</li></ol>'
        }
    }
    for slug, data in pages.items():
        StaticPage.objects.update_or_create(
            slug=slug,
            defaults={'title': data['title'], 'content': data['content']}
        )

class Migration(migrations.Migration):
    dependencies = [
        ('marketplace', '0010_alter_conversation_unique_together_and_more'),
    ]
    operations = [
        migrations.RunPython(create_static_pages, reverse_code=migrations.RunPython.noop),
    ]