from django.db import migrations

def create_static_pages(apps, schema_editor):
    StaticPage = apps.get_model('marketplace', 'StaticPage')
    pages = {
        'about-us': {
            'title': "About Naijasale | Nigeria's Verified Digital Marketplace",
            'content': """<h2>Empowering Seamless Commerce Across Nigeria</h2>
<p><strong>Naijasale</strong> is an enterprise peer-to-peer commerce and classifieds ecosystem engineered to bridge the gap between verified local sellers, artisans, and discerning consumers across all 36 states and the Federal Capital Territory.</p>
<h3>Our Core Mission</h3>
<p>We solve the critical friction points of modern e-commerce in West Africa: <strong>transparency, verified identity, and secure communication</strong>. We provide individuals, registered MSMEs, and independent merchants with institutional-grade digital storefront tools, leveling the playing field for authentic Nigerian business.</p>
<h3>Why Naijasale Sets the Benchmark</h3>
<ul>
  <li><strong>Rigorous Seller Verification:</strong> Multi-tiered identity and contact checks designed to suppress anonymous bad actors and foster absolute buyer trust.</li>
  <li><strong>Encrypted Communications:</strong> Closed-loop on-platform messaging and offer negotiation systems to protect buyer-seller confidentiality.</li>
  <li><strong>Data Integrity & Zero Spam:</strong> Intelligent listing audits that actively filter duplicate, counterfeit, or misleading catalog entries.</li>
  <li><strong>Localized Logistics Readiness:</strong> Built to serve community-level exchanges from Lagos Island commercial hubs to Kano municipal corridors.</li>
</ul>
<p>Whether you are liquidating enterprise inventory, sourcing verified electronics, or scaling a neighborhood retail brand, Naijasale delivers the institutional backbone required to trade with absolute confidence.</p>"""
        },
        'safety-tips': {
            'title': "Trust, Security & Safe Trading Architecture",
            'content': """<h2>Our Commitment to Customer Protection</h2>
<p>At Naijasale, trust is not an afterthought—it is the foundation of our engineering. We actively deploy fraud monitoring heuristics and community moderation protocols to ensure a safe, legitimate trading venue for all participants.</p>
<h3>The Golden Rules for Safe Transactions</h3>
<ol>
  <li><strong>Inspect First, Pay Second:</strong> Never transfer funds, issue mobile money deposits, or send delivery fees in advance of physically inspecting the item and verifying its working condition.</li>
  <li><strong>Meet in High-Traffic Public Locations:</strong> Complete face-to-face handovers in well-lit, public environments with security—such as shopping malls, bank premises, or verified commercial centers.</li>
  <li><strong>Keep All Correspondence on Naijasale:</strong> Communicate strictly through the Naijasale chat. External channels eliminate our ability to provide administrative dispute logs or security audits.</li>
  <li><strong>Verify Realistic Market Valuations:</strong> Premium items offered at unrealistically cheap prices are often scams or counterfeit goods. Verify receipts and ownership documents.</li>
  <li><strong>Safeguard Sensitive Identifiers:</strong> Naijasale staff will never ask for your login password, OTP codes, BVN, or ATM PIN.</li>
</ol>
<h3>Immediate Incident Reporting</h3>
<p>Our Trust & Compliance team reviews flagged postings 24/7. If you spot a suspicious user or item, click <strong>Report Ad</strong> immediately to trigger an administrative review and account freeze.</p>"""
        },
        'terms-of-service': {
            'title': "Terms of Service & User Covenant",
            'content': """<h2>Contractual Agreement & Operating Standards</h2>
<p>By accessing or interacting with the Naijasale platform ("Service"), you enter into a binding agreement governed by the laws of the Federal Republic of Nigeria.</p>
<h3>1. User Verification & Account Integrity</h3>
<p>Users must provide accurate, verifiable identity details upon registration. You are solely responsible for maintaining account confidentiality. Any transactional commitments or listings issued through your account remain your legal liability.</p>
<h3>2. Prohibited Items & Merchant Conduct</h3>
<p>Naijasale strictly enforces zero-tolerance restrictions on prohibited merchandise, including:</p>
<ul>
  <li>Stolen or unverified property lacking legal chain-of-custody.</li>
  <li>Counterfeit, replica, or trademark-infringing items.</li>
  <li>Controlled narcotics, unregistered pharmaceuticals, weapons, and illicit materials.</li>
  <li>Deceptive financial schemes, advance-fee requests, or predatory solicitations.</li>
</ul>
<p>Violators face permanent system bans, IP blacklisting, and referral to relevant regulatory and law enforcement authorities.</p>
<h3>3. Limitation of Liability</h3>
<p>Naijasale operates as a technology host and discovery platform connecting independent buyers and verified third-party merchants. Naijasale does not manufacture, warehouse, or physically possess listed items.</p>"""
        },
        'privacy-policy': {
            'title': "Global Privacy Policy & Data Governance",
            'content': """<h2>Data Protection Compliance Statement</h2>
<p>Naijasale is committed to upholding international information security frameworks and compliance requirements mandated by the <strong>Nigeria Data Protection Act (NDPA)</strong>.</p>
<h3>Information We Process</h3>
<ul>
  <li><strong>Account Credentials:</strong> Authenticated email addresses, verified telephone contacts, and cryptographic password hashes.</li>
  <li><strong>Operational Telemetry:</strong> Device identifiers, IP headers, and security logs used exclusively for fraud detection.</li>
  <li><strong>Transactional Messaging:</strong> Secure chat archives preserved to assist user dispute resolution and prevent spam.</li>
</ul>
<h3>Zero-Sale Data Guarantee</h3>
<p>Your personal information is processed strictly to enable secure marketplace trading. <strong>Naijasale never sells, rents, or monetizes user databases to third-party advertisers or marketing agencies.</strong></p>
<h3>Your Rights</h3>
<p>You retain the lawful right to request an audit of your data, update your information, or request account deactivation. Contact our Compliance desk at <strong>privacy@naijasale.com</strong> for data privacy inquiries.</p>"""
        },
        'seller-verification': {
            'title': "Seller Verification & Merchant Standards",
            'content': """<h2>Verified Merchant Framework</h2>
<p>The <strong>Naijasale Verified Seller</strong> program builds trust, reduces fraud, and helps legitimate merchants stand out to buyers nationwide.</p>
<h3>Why Verification Matters</h3>
<p>Buyers prefer verified sellers. Verified merchants gain increased listing prominence, higher conversion rates, and a <strong>Verified Badge</strong> on their profile and items.</p>
<h3>The Verification Steps</h3>
<ol>
  <li><strong>Account & Phone Binding:</strong> Confirm ownership through verified email and a registered Nigerian telephone line via secure OTP.</li>
  <li><strong>Identity Confirmation:</strong> Submit valid government-issued identification (NIN, Driver License, Voter Card, or International Passport) matching your profile credentials.</li>
  <li><strong>Business Registration (Optional for MSMEs):</strong> Registered businesses can submit CAC registration documents to earn enterprise seller status and custom storefront tools.</li>
  <li><strong>Administrative Review:</strong> Our Compliance & Trust team reviews credentials within 24 to 48 business hours.</li>
</ol>
<h3>Merchant Code of Conduct</h3>
<p>Verified status is a privilege. Accounts face immediate revocation, security flags, or bans if involved in misleading pricing, selling counterfeit items, or attempting off-platform advance-fee schemes.</p>"""
        }
    }
    for slug, data in pages.items():
        StaticPage.objects.update_or_create(
            slug=slug,
            defaults={'title': data['title'], 'content': data['content'].strip()}
        )

class Migration(migrations.Migration):
    dependencies = [
        ('marketplace', '0010_alter_conversation_unique_together_and_more'),
    ]
    operations = [
        migrations.RunPython(create_static_pages, reverse_code=migrations.RunPython.noop),
    ]