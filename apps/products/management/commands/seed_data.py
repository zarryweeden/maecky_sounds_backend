"""
Management command to seed the database with realistic demo data.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # Clear existing data first
"""
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with demo categories, brands, products, blog posts, and users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write(self.style.WARNING("Flushing existing data..."))
            self._flush()

        self.stdout.write(self.style.MIGRATE_HEADING("Starting seed..."))
        self._seed_superuser()
        self._seed_users()
        self._seed_categories()
        self._seed_brands()
        self._seed_tags()
        self._seed_products()
        self._seed_blog()
        self._seed_coupons()
        self.stdout.write(self.style.SUCCESS("\n✓ Seed complete! Store is ready.\n"))

    # ── Flush ──────────────────────────────────────────────────────────────────

    def _flush(self):
        from apps.products.models import Product, Category, Brand, Tag
        from apps.blog.models import BlogPost, BlogCategory
        from apps.coupons.models import Coupon
        from apps.orders.models import Order, Cart
        from apps.reviews.models import Review

        Review.objects.all().delete()
        Order.objects.all().delete()
        Cart.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()
        Tag.objects.all().delete()
        BlogPost.objects.all().delete()
        BlogCategory.objects.all().delete()
        Coupon.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS("  ✓ Flushed"))

    # ── Superuser ──────────────────────────────────────────────────────────────

    def _seed_superuser(self):
        email = "admin@maeckysounds.co.ke"
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password="admin123",
                full_name="Maecky Admin",
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Superuser created: {email} / admin123"))
        else:
            self.stdout.write(f"  → Superuser already exists: {email}")

    # ── Regular Users ──────────────────────────────────────────────────────────

    def _seed_users(self):
        from apps.users.models import Address

        sample_users = [
            {"email": "john.kamau@gmail.com",   "full_name": "John Kamau",    "phone": "0712345678"},
            {"email": "aisha.wanjiku@gmail.com", "full_name": "Aisha Wanjiku", "phone": "0723456789"},
            {"email": "david.ochieng@gmail.com", "full_name": "David Ochieng", "phone": "0734567890"},
            {"email": "grace.njeri@gmail.com",   "full_name": "Grace Njeri",   "phone": "0745678901"},
            {"email": "brian.otieno@gmail.com",  "full_name": "Brian Otieno",  "phone": "0756789012"},
        ]

        cities = [
            ("Nairobi", "Nairobi County"),
            ("Mombasa", "Mombasa County"),
            ("Kisumu",  "Kisumu County"),
            ("Nakuru",  "Nakuru County"),
            ("Eldoret", "Uasin Gishu County"),
        ]

        for i, u_data in enumerate(sample_users):
            user, created = User.objects.get_or_create(
                email=u_data["email"],
                defaults={
                    "full_name": u_data["full_name"],
                    "phone": u_data["phone"],
                    "email_verified": True,
                    "newsletter_subscribed": random.choice([True, False]),
                },
            )
            if created:
                user.set_password("password123")
                user.save()

                city, county = cities[i % len(cities)]
                Address.objects.create(
                    user=user,
                    label="Home",
                    full_name=u_data["full_name"],
                    phone=u_data["phone"],
                    address_line1=f"{random.randint(1, 200)} Kenyatta Avenue",
                    city=city,
                    county=county,
                    postal_code=f"0{random.randint(1000, 9999)}0",
                    is_default=True,
                )

        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(sample_users)} sample users created"))

    # ── Categories ─────────────────────────────────────────────────────────────

    def _seed_categories(self):
        from apps.products.models import Category

        top_level = [
            {"name": "Guitars",             "icon": "🎸", "description": "Electric, acoustic, and bass guitars from the world's top makers."},
            {"name": "Keyboards & Pianos",  "icon": "🎹", "description": "Digital pianos, synthesizers, and MIDI keyboards for every level."},
            {"name": "Drums & Percussion",  "icon": "🥁", "description": "Acoustic kits, electronic drums, and hand percussion."},
            {"name": "Wind Instruments",    "icon": "🎷", "description": "Saxophones, trumpets, flutes, and more brass & woodwind."},
            {"name": "String Instruments",  "icon": "🎻", "description": "Violins, cellos, ukuleles, and orchestral strings."},
            {"name": "Studio & Recording",  "icon": "🎙", "description": "Microphones, audio interfaces, monitors, and recording software."},
            {"name": "DJ Equipment",        "icon": "🎧", "description": "Controllers, turntables, mixers, and DJ headphones."},
            {"name": "Accessories",         "icon": "🎵", "description": "Strings, tuners, stands, cases, cables, and effects."},
        ]

        subcategories = {
            "Guitars":            ["Electric Guitars", "Acoustic Guitars", "Bass Guitars", "Classical Guitars"],
            "Keyboards & Pianos": ["Digital Pianos", "Portable Keyboards", "Synthesizers", "MIDI Controllers"],
            "Drums & Percussion": ["Electronic Drum Kits", "Acoustic Drum Kits", "Cajon & Hand Drums", "Cymbals & Hardware"],
            "Wind Instruments":   ["Saxophones", "Trumpets & Brass", "Flutes & Woodwind", "Harmonicas"],
            "String Instruments": ["Violins", "Cellos & Double Bass", "Ukuleles", "Mandolins & Banjos"],
            "Studio & Recording": ["Microphones", "Audio Interfaces", "Studio Monitors", "Recording Software"],
            "DJ Equipment":       ["DJ Controllers", "Turntables", "DJ Mixers", "DJ Headphones"],
            "Accessories":        ["Guitar Strings", "Tuners & Metronomes", "Stands & Mounts", "Effects & Pedals", "Cables & Connectors", "Cases & Bags"],
        }

        self._categories = {}
        for i, cat_data in enumerate(top_level):
            cat, _ = Category.objects.get_or_create(
                slug=slugify(cat_data["name"]),
                defaults={
                    "name": cat_data["name"],
                    "icon": cat_data["icon"],
                    "description": cat_data["description"],
                    "sort_order": i,
                    "is_active": True,
                },
            )
            self._categories[cat_data["name"]] = cat

            for j, sub_name in enumerate(subcategories.get(cat_data["name"], [])):
                sub, _ = Category.objects.get_or_create(
                    slug=slugify(sub_name),
                    defaults={
                        "name": sub_name,
                        "parent": cat,
                        "sort_order": j,
                        "is_active": True,
                    },
                )

        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(top_level)} top-level categories + subcategories created"))

    # ── Brands ─────────────────────────────────────────────────────────────────

    def _seed_brands(self):
        from apps.products.models import Brand

        brands_data = [
            {"name": "Fender",              "website": "https://www.fender.com"},
            {"name": "Gibson",              "website": "https://www.gibson.com"},
            {"name": "Yamaha",              "website": "https://www.yamaha.com"},
            {"name": "Roland",              "website": "https://www.roland.com"},
            {"name": "Casio",               "website": "https://www.casio.com"},
            {"name": "Pearl",               "website": "https://www.pearldrum.com"},
            {"name": "Shure",               "website": "https://www.shure.com"},
            {"name": "Rode",                "website": "https://www.rode.com"},
            {"name": "Pioneer DJ",          "website": "https://www.pioneerdj.com"},
            {"name": "Korg",                "website": "https://www.korg.com"},
            {"name": "Taylor",              "website": "https://www.taylorguitars.com"},
            {"name": "Ibanez",              "website": "https://www.ibanez.com"},
            {"name": "Focusrite",           "website": "https://focusrite.com"},
            {"name": "Native Instruments",  "website": "https://www.native-instruments.com"},
            {"name": "Boss",                "website": "https://www.boss.info"},
            {"name": "D'Addario",           "website": "https://www.daddario.com"},
            {"name": "Seiko",               "website": "https://www.seiko.com"},
        ]

        self._brands = {}
        for i, b in enumerate(brands_data):
            brand, _ = Brand.objects.get_or_create(
                slug=slugify(b["name"]),
                defaults={
                    "name": b["name"],
                    "website": b["website"],
                    "is_active": True,
                    "sort_order": i,
                },
            )
            self._brands[b["name"]] = brand

        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(brands_data)} brands created"))

    # ── Tags ───────────────────────────────────────────────────────────────────

    def _seed_tags(self):
        from apps.products.models import Tag

        tag_names = [
            "electric", "acoustic", "beginner", "intermediate", "professional",
            "recording", "live", "studio", "vintage", "modern", "budget",
            "premium", "kenya", "nairobi", "bestseller", "new-arrival",
            "weighted-keys", "portable", "wireless", "usb",
        ]
        self._tags = {}
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name},
            )
            self._tags[name] = tag

        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(tag_names)} tags created"))

    # ── Products ───────────────────────────────────────────────────────────────

    def _seed_products(self):
        from apps.products.models import Product, ProductSpecification, ProductImage
        from apps.inventory.models import Inventory

        products_data = self._get_products_data()
        created_count = 0

        for p_data in products_data:
            cat_name = p_data.pop("category")
            brand_name = p_data.pop("brand")
            specs = p_data.pop("specifications", {})
            tag_names = p_data.pop("tags", [])
            stock = p_data.pop("stock", random.randint(5, 30))

            category = self._categories.get(cat_name)
            brand = self._brands.get(brand_name)

            if not category or not brand:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping '{p_data['name']}': category/brand not found")
                )
                continue

            slug = slugify(p_data["name"])
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    **p_data,
                    "category": category,
                    "brand": brand,
                    "is_active": True,
                },
            )

            if created:
                # Specifications
                for i, (key, value) in enumerate(specs.items()):
                    ProductSpecification.objects.create(
                        product=product,
                        key=key,
                        value=value,
                        sort_order=i,
                    )

                # Tags
                for tag_name in tag_names:
                    if tag_name in self._tags:
                        product.tags.add(self._tags[tag_name])

                # Inventory
                inv, _ = Inventory.objects.get_or_create(
                    product=product,
                    defaults={
                        "quantity": stock,
                        "low_stock_threshold": 5,
                        "track_inventory": True,
                    },
                )
                if not _:
                    inv.quantity = stock
                    inv.save(update_fields=["quantity"])

                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ {created_count} products created"))
        self._seed_reviews()

    def _get_products_data(self):
        return [
            {
                "name": "Fender Player Stratocaster",
                "sku": "MS-FND-STRT-001",
                "category": "Guitars",
                "brand": "Fender",
                "price": 145000,
                "sale_price": 119000,
                "short_description": "Classic Fender tone, modern playability.",
                "description": "The Player Stratocaster puts classic Fender tone and feel in your hands with a Pure Vintage tremolo and three single-coil pickups. The definitive beginner-to-pro instrument refined over decades of player feedback.",
                "is_featured": True,
                "is_new": False,
                "is_hot": True,
                "condition": "new",
                "tags": ["electric", "intermediate"],
                "stock": 8,
                "specifications": {
                    "Body Material": "Alder",
                    "Neck": "Maple, Modern C Shape",
                    "Fingerboard": "Maple",
                    "Frets": "22 Medium Jumbo",
                    "Scale Length": "648mm (25.5\")",
                    "Pickups": "3× Player Series Alnico 5 Single-Coil",
                    "Bridge": "Classic Tremolo with Bent Steel Saddles",
                    "Finish": "3-Color Sunburst",
                    "Weight": "3.8 kg",
                },
            },
            {
                "name": "Gibson Les Paul Standard 50s",
                "sku": "MS-GBN-LP50-002",
                "category": "Guitars",
                "brand": "Gibson",
                "price": 285000,
                "sale_price": None,
                "short_description": "Vintage tone meets modern craftsmanship.",
                "description": "Built to 1950s specs, the Les Paul Standard 50s features a solid mahogany body with maple top, rounded 50s neck profile, and legendary Burstbucker humbuckers.",
                "is_featured": True,
                "is_new": False,
                "is_hot": True,
                "condition": "new",
                "tags": ["electric", "professional", "premium"],
                "stock": 3,
                "specifications": {
                    "Body": "Solid Mahogany with Maple Cap",
                    "Neck": "Mahogany, 50s Rounded Profile",
                    "Fingerboard": "Rosewood",
                    "Frets": "22 Medium Jumbo",
                    "Scale Length": "628mm (24.75\")",
                    "Pickups": "Burstbucker 1 (Neck) + Burstbucker 2 (Bridge)",
                    "Controls": "2× Volume, 2× Tone, 3-Way Toggle",
                    "Finish": "Honey Burst",
                    "Weight": "4.2 kg",
                },
            },
            {
                "name": "Yamaha FG800 Acoustic Guitar",
                "sku": "MS-YMH-FG800-003",
                "category": "Guitars",
                "brand": "Yamaha",
                "price": 38000,
                "sale_price": None,
                "short_description": "Solid spruce top delivering warm, resonant sound.",
                "description": "Yamaha's best-selling acoustic guitar featuring a solid Sitka spruce top with scalloped bracing for rich, full, projecting tone that improves with age.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["acoustic", "beginner"],
                "stock": 14,
                "specifications": {
                    "Top": "Solid Sitka Spruce",
                    "Back & Sides": "Nato",
                    "Body Style": "Dreadnought",
                    "Frets": "20",
                    "Bracing": "Scalloped Pattern",
                    "Finish": "Natural",
                },
            },
            {
                "name": "Fender FA-125CE Acoustic-Electric",
                "sku": "MS-FND-FA125-004",
                "category": "Guitars",
                "brand": "Fender",
                "price": 28500,
                "sale_price": 24999,
                "short_description": "The perfect first acoustic-electric guitar.",
                "description": "Great-sounding, easy-playing acoustic-electric for the budding guitarist. Spruce top projects clearly while the Fishman Isys III pickup ensures you sound great plugged in.",
                "is_featured": False,
                "is_new": True,
                "is_hot": False,
                "condition": "new",
                "tags": ["acoustic", "beginner"],
                "stock": 20,
                "specifications": {
                    "Top": "Spruce",
                    "Back & Sides": "Mahogany",
                    "Body Style": "Dreadnought",
                    "Electronics": "Fishman Isys III",
                    "Frets": "20",
                    "Finish": "Natural Gloss",
                },
            },
            {
                "name": "Taylor 214ce Acoustic-Electric",
                "sku": "MS-TYL-214CE-005",
                "category": "Guitars",
                "brand": "Taylor",
                "price": 132000,
                "sale_price": None,
                "short_description": "Rich projection, effortless playability.",
                "description": "The 214ce Grand Auditorium features a solid Sitka spruce top with layered rosewood back and sides. Taylor's Expression System 2 pickup captures the natural tone without sounding processed.",
                "is_featured": True,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["acoustic", "professional"],
                "stock": 5,
                "specifications": {
                    "Top": "Solid Sitka Spruce",
                    "Back & Sides": "Layered Rosewood",
                    "Body Style": "Grand Auditorium",
                    "Electronics": "Taylor Expression System 2",
                    "Scale Length": "648mm",
                    "Nut Width": "42.8mm",
                },
            },
            {
                "name": "Ibanez AEWC400 Comfort Body",
                "sku": "MS-IBZ-AEWC400-006",
                "category": "Guitars",
                "brand": "Ibanez",
                "price": 65000,
                "sale_price": 58000,
                "short_description": "Stylish comfort acoustic with superb amplified tone.",
                "description": "The AEWC400 features Ibanez's comfort-contoured body, solid Sitka spruce top, and Fishman Sonicore pickup for clear, natural reproduction when amplified.",
                "is_featured": False,
                "is_new": True,
                "is_hot": False,
                "condition": "new",
                "tags": ["acoustic", "intermediate"],
                "stock": 6,
                "specifications": {
                    "Top": "Solid Sitka Spruce",
                    "Back & Sides": "Flamed Maple",
                    "Body Style": "Comfort-Contoured",
                    "Electronics": "Fishman Sonicore + Ibanez AEQ210T",
                    "Finish": "Transparent Black Sunburst",
                },
            },
            {
                "name": "Yamaha P-45 Digital Piano",
                "sku": "MS-YMH-P45-007",
                "category": "Keyboards & Pianos",
                "brand": "Yamaha",
                "price": 58000,
                "sale_price": 49000,
                "short_description": "Authentic piano feel at an accessible price.",
                "description": "The P-45 features Yamaha's Graded Hammer Standard action — heavier in the low end, lighter in the high end — with AWM Stereo Sampling for authentic piano tone.",
                "is_featured": True,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["weighted-keys", "beginner"],
                "stock": 15,
                "specifications": {
                    "Keys": "88 Graded Hammer Standard Weighted",
                    "Polyphony": "64-note",
                    "Voices": "10",
                    "Connectivity": "USB to Host, Sustain Pedal",
                    "Speakers": "12W × 2",
                    "Weight": "11.5 kg",
                },
            },
            {
                "name": "Roland FP-30X Digital Piano",
                "sku": "MS-RLD-FP30X-008",
                "category": "Keyboards & Pianos",
                "brand": "Roland",
                "price": 98000,
                "sale_price": 88000,
                "short_description": "Studio-quality grand piano sound in a portable body.",
                "description": "The FP-30X features Roland's PHA-4 Standard keyboard action with Escapement and Ivory Feel. The SuperNATURAL Piano sound engine models acoustic grand piano resonances with stunning realism.",
                "is_featured": True,
                "is_new": False,
                "is_hot": True,
                "condition": "new",
                "tags": ["weighted-keys", "professional", "portable"],
                "stock": 5,
                "specifications": {
                    "Keys": "88 PHA-4 Standard with Escapement & Ivory Feel",
                    "Sound Generator": "SuperNATURAL Piano Modelling",
                    "Polyphony": "256-note",
                    "Speakers": "11W × 2",
                    "Bluetooth": "Audio + MIDI",
                    "Weight": "14 kg",
                },
            },
            {
                "name": "Casio CT-X700 61-Key Keyboard",
                "sku": "MS-CSO-CTX700-009",
                "category": "Keyboards & Pianos",
                "brand": "Casio",
                "price": 22000,
                "sale_price": None,
                "short_description": "Versatile 61-key keyboard for all skill levels.",
                "description": "600 high-quality tones powered by Casio's AiX Sound Source. 195 rhythms and a comprehensive lesson system make this the ideal starter keyboard.",
                "is_featured": False,
                "is_new": True,
                "is_hot": False,
                "condition": "new",
                "tags": ["beginner", "portable"],
                "stock": 12,
                "specifications": {
                    "Keys": "61 (Touch Sensitive)",
                    "Tones": "600",
                    "Rhythms": "195",
                    "Polyphony": "48-note",
                    "Connectivity": "USB, Headphone Out",
                    "Weight": "3.8 kg",
                },
            },
            {
                "name": "Roland TD-17KVX Electronic Drum Kit",
                "sku": "MS-RLD-TD17KVX-010",
                "category": "Drums & Percussion",
                "brand": "Roland",
                "price": 195000,
                "sale_price": None,
                "short_description": "Pro-grade electronic drums for serious players.",
                "description": "The TD-17KVX raises the bar with mesh heads on all pads, providing a realistic and quiet playing experience perfect for Nairobi apartment practice.",
                "is_featured": True,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["professional", "recording"],
                "stock": 2,
                "specifications": {
                    "Snare": "PD-128S-BC Mesh Snare",
                    "Tom Pads": "PDX-8 × 3 (8\" Mesh)",
                    "Hi-Hat": "VH-10 V-Hi-Hat",
                    "Cymbals": "CY-14C-T (Crash), CY-13R (Ride)",
                    "Sound Module": "TD-17",
                    "Connectivity": "USB (Audio/MIDI)",
                },
            },
            {
                "name": "Pearl Export EXX Rock Drum Kit",
                "sku": "MS-PRL-EXX-011",
                "category": "Drums & Percussion",
                "brand": "Pearl",
                "price": 145000,
                "sale_price": 129000,
                "short_description": "Complete professional rock drum kit, ready to play.",
                "description": "The Pearl Export EXX delivers professional Pearl craftsmanship and tone using SST (Superior Shell Technology) for consistent roundness and tuning stability.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["professional", "live"],
                "stock": 2,
                "specifications": {
                    "Bass Drum": "22\" × 18\"",
                    "Snare": "14\" × 5.5\" Steel",
                    "Toms": "10\" × 7\", 12\" × 8\"",
                    "Floor Tom": "16\" × 16\"",
                    "Hardware": "Full hardware pack included",
                },
            },
            {
                "name": "Yamaha YAS-280 Alto Saxophone",
                "sku": "MS-YMH-YAS280-012",
                "category": "Wind Instruments",
                "brand": "Yamaha",
                "price": 95000,
                "sale_price": None,
                "short_description": "Professional quality tone for student players.",
                "description": "The YAS-280 combines advantages of more advanced Yamaha models with a student-friendly design. Improved neck and body taper for accurate intonation across the full range.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["beginner", "intermediate"],
                "stock": 4,
                "specifications": {
                    "Material": "Yellow Brass Body",
                    "Finish": "Gold Lacquer",
                    "Keys": "High F# key included",
                    "Key Touches": "Mother of Pearl",
                    "Case": "Moulded ABS",
                },
            },
            {
                "name": "Shure SM58 Vocal Microphone",
                "sku": "MS-SHR-SM58-013",
                "category": "Studio & Recording",
                "brand": "Shure",
                "price": 18500,
                "sale_price": 15999,
                "short_description": "The world's most trusted vocal mic.",
                "description": "The SM58 is the world's most widely used vocal microphone. Tailored frequency response — brightened midrange and deep bass rolloff — delivers clean, warm vocal reproduction.",
                "is_featured": True,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["recording", "live", "professional"],
                "stock": 30,
                "specifications": {
                    "Type": "Dynamic Cardioid",
                    "Frequency": "50–15,000 Hz",
                    "Impedance": "150 ohms",
                    "Output": "XLR 3-pin",
                    "Weight": "298g",
                },
            },
            {
                "name": "Rode NT1-A Studio Condenser",
                "sku": "MS-RDE-NT1A-014",
                "category": "Studio & Recording",
                "brand": "Rode",
                "price": 32000,
                "sale_price": None,
                "short_description": "Ultra-quiet studio condenser for pristine recordings.",
                "description": "The NT1-A is acclaimed as the world's quietest studio microphone — just 5dBA self-noise. Ideal for vocals, acoustic instruments, and voice-overs.",
                "is_featured": True,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["recording", "studio", "professional"],
                "stock": 9,
                "specifications": {
                    "Type": "Large-Diaphragm Condenser",
                    "Polar Pattern": "Cardioid",
                    "Self-Noise": "5dBA",
                    "Frequency": "20Hz–20kHz",
                    "Phantom Power": "48V Required",
                    "Includes": "SM6 Shockmount, Pop Filter, XLR Cable",
                },
            },
            {
                "name": "Focusrite Scarlett 2i2 4th Gen",
                "sku": "MS-FCR-S2I2-015",
                "category": "Studio & Recording",
                "brand": "Focusrite",
                "price": 24500,
                "sale_price": None,
                "short_description": "The world's #1 audio interface, now even better.",
                "description": "The Scarlett 2i2 4th Gen adds better preamps, 32-bit/192kHz recording, and Air mode for a brighter sound inspired by Focusrite's iconic ISA transformer preamps.",
                "is_featured": True,
                "is_new": True,
                "is_hot": False,
                "condition": "new",
                "tags": ["recording", "studio", "usb"],
                "stock": 18,
                "specifications": {
                    "Inputs": "2× Combo XLR/Jack",
                    "Outputs": "2× 6.35mm TRS Jack",
                    "Sample Rate": "Up to 192kHz",
                    "Bit Depth": "32-bit float",
                    "Dynamic Range": "111dB",
                    "Connectivity": "USB-C",
                },
            },
            {
                "name": "Native Instruments Komplete 14",
                "sku": "MS-NI-K14-016",
                "category": "Studio & Recording",
                "brand": "Native Instruments",
                "price": 42000,
                "sale_price": 35000,
                "short_description": "The complete professional music production toolkit.",
                "description": "Komplete 14 — 130+ instruments and effects for any genre and workflow. From Kontakt sample libraries to Massive X synthesis. The industry-standard production bundle.",
                "is_featured": True,
                "is_new": True,
                "is_hot": True,
                "condition": "new",
                "tags": ["recording", "studio", "professional"],
                "stock": 999,
                "specifications": {
                    "Total Products": "130+",
                    "Instruments": "75",
                    "Effects": "55",
                    "Storage Required": "~770 GB",
                    "Formats": "Standalone, VST3, AU, AAX",
                    "Activation": "Native Access (Online)",
                },
            },
            {
                "name": "Pioneer DDJ-400 DJ Controller",
                "sku": "MS-PNR-DDJ400-017",
                "category": "DJ Equipment",
                "brand": "Pioneer DJ",
                "price": 58000,
                "sale_price": 52000,
                "short_description": "Start your DJ journey the right way.",
                "description": "2-channel rekordbox DJ controller with full-size jog wheels, beat FX lever, and built-in tutorial functions. The perfect entry point for aspiring DJs.",
                "is_featured": True,
                "is_new": False,
                "is_hot": True,
                "condition": "new",
                "tags": ["beginner", "live"],
                "stock": 7,
                "specifications": {
                    "Channels": "2",
                    "Jog Wheels": "Full-size (140mm)",
                    "Software": "rekordbox DJ (included)",
                    "Master Output": "RCA + 3.5mm",
                    "Connectivity": "USB-B (Bus Powered)",
                    "Weight": "2.4 kg",
                },
            },
            {
                "name": "Boss GT-1 Guitar Multi-Effects",
                "sku": "MS-BSS-GT1-018",
                "category": "Accessories",
                "brand": "Boss",
                "price": 32000,
                "sale_price": 28000,
                "short_description": "100+ BOSS effects in a portable floor unit.",
                "description": "The GT-1 packs 108 amp models, 100+ effects, a 38-second looper, and up to 5 hours of battery life into an ultra-portable package.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["electric", "live"],
                "stock": 8,
                "specifications": {
                    "Effects": "100+ COSM Amp Models + Boss Effects",
                    "Amp Models": "108",
                    "Looper": "38 seconds",
                    "Battery Life": "5 hours (AA × 4)",
                    "USB": "Audio Interface + Patch Editor",
                    "Weight": "820g",
                },
            },
            {
                "name": "D'Addario EXL110 Strings 10-Pack",
                "sku": "MS-DAD-EXL110-019",
                "category": "Accessories",
                "brand": "D'Addario",
                "price": 6500,
                "sale_price": 5500,
                "short_description": "The world's best-selling electric guitar strings.",
                "description": "EXL110 Regular Light — nickel-plated steel wrap wire over hex core. Bright attack, mid-range punch, extended longevity. The world's most popular electric strings.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["electric", "beginner"],
                "stock": 100,
                "specifications": {
                    "Gauges": ".010 .013 .017 .026 .036 .046",
                    "Material": "Nickel-Plated Steel",
                    "Core": "Round Hex Core",
                    "Pack Size": "10 sets",
                    "Tension": "Regular Light",
                },
            },
            {
                "name": "Seiko SAT500 Clip-On Tuner",
                "sku": "MS-SKO-SAT500-020",
                "category": "Accessories",
                "brand": "Seiko",
                "price": 2500,
                "sale_price": None,
                "short_description": "Fast, accurate clip-on tuning for any instrument.",
                "description": "Highly sensitive chromatic clip-on tuner compatible with all instruments. 360-degree rotating display for easy reading from any angle. Accurate to ±1 cent.",
                "is_featured": False,
                "is_new": False,
                "is_hot": False,
                "condition": "new",
                "tags": ["beginner", "portable"],
                "stock": 50,
                "specifications": {
                    "Display": "Backlit LCD",
                    "Modes": "Chromatic, Guitar, Bass, Violin, Ukulele",
                    "Calibration": "410–480 Hz (A4)",
                    "Battery": "CR2032 (3V)",
                    "Clip": "360° Rotating",
                    "Accuracy": "±1 cent",
                },
            },
        ]

    def _seed_reviews(self):
        from apps.products.models import Product
        from apps.reviews.models import Review

        review_texts = [
            (5, "Absolutely love this! Arrived in perfect condition and Maecky Sounds delivered the next day. Would buy again without hesitation."),
            (5, "Quality is incredible for the price. My students are already seeing results. Highly recommend to anyone in Nairobi."),
            (4, "Solid build, sounds great. Needed minor setup out of the box but after that it plays like a dream."),
            (5, "I've bought from Maecky Sounds three times now and the service is always top-notch. This product did not disappoint."),
            (4, "Great value for money. Consistent quality and fast delivery. Would definitely buy again."),
            (5, "Exceeded my expectations. The packaging was excellent and it arrived in pristine condition."),
            (3, "Decent product overall. A few minor cosmetic issues but nothing that affects performance. Good price point."),
            (5, "Perfect! This is exactly what I was looking for. The quality speaks for itself at this price range."),
        ]

        users = list(User.objects.filter(is_staff=False, is_active=True))
        products = list(Product.objects.filter(is_active=True)[:10])

        review_count = 0
        for product in products:
            sample_reviews = random.sample(review_texts, random.randint(2, 4))
            random.shuffle(users)
            for i, (rating, text) in enumerate(sample_reviews):
                if i >= len(users):
                    break
                _, created = Review.objects.get_or_create(
                    product=product,
                    user=users[i],
                    defaults={
                        "rating": rating,
                        "body": text,
                        "is_approved": True,
                        "is_verified": random.choice([True, False]),
                    },
                )
                if created:
                    review_count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ {review_count} product reviews created"))

    # ── Blog ───────────────────────────────────────────────────────────────────

    def _seed_blog(self):
        from apps.blog.models import BlogCategory, BlogPost

        admin_user = User.objects.filter(is_superuser=True).first()

        categories_data = [
            "Gear Guides", "Recording", "Music Production",
            "Community", "Maintenance",
        ]
        blog_categories = {}
        for name in categories_data:
            cat, _ = BlogCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name},
            )
            blog_categories[name] = cat

        posts_data = [
            {
                "title": "Top 10 Guitars for Kenyan Beginners in 2026",
                "category": "Gear Guides",
                "excerpt": "Starting your guitar journey in Kenya? We've rounded up the best beginner guitars available at Maecky Sounds — from entry-level acoustics to versatile electrics.",
                "body": """Whether you're dreaming of playing at a local church, a Nairobi bar stage, or just for your family on weekends, the right guitar will make all the difference in your early months.

We've played and tested every guitar on this list in our Nairobi store, and each represents the best value at its price point for Kenyan musicians.

**1. Yamaha FG800 (KES 38,000)** — The best all-around beginner acoustic. Solid spruce top, easy playability, and a tone that improves with age.

**2. Fender FA-125CE (KES 24,999)** — If you want acoustic-electric under KES 25K, this is your answer.

**3. Fender Player Stratocaster (KES 119,000 on sale)** — If your budget stretches this far, the Player Strat is the last beginner guitar you'll ever need.""",
                "tags": "guitars,kenya,beginners,buying-guide",
                "is_featured": True,
            },
            {
                "title": "Setting Up Your Home Recording Studio in Nairobi",
                "category": "Recording",
                "excerpt": "A professional-sounding home studio doesn't require a massive budget. Here's everything you need to get started recording in Nairobi.",
                "body": """The explosion of Afrobeats and Gengetone has created massive demand for affordable home recording in Kenya. The good news? You can build a genuinely professional-sounding studio for under KES 100,000.

**The Core 4 Components:**

1. **Audio Interface** — The Focusrite Scarlett 2i2 (KES 24,500) is the gold standard. Clean preamps, reliable drivers.

2. **Microphone** — The Rode NT1-A (KES 32,000) gives studio-quality recordings at a fraction of professional studio costs.

3. **Headphones** — Closed-back headphones are essential for tracking in Nairobi's noisy environment.

4. **DAW Software** — Native Instruments Komplete 14 (KES 35,000 on sale) includes everything you need.""",
                "tags": "studio,recording,home-studio,nairobi",
                "is_featured": False,
            },
            {
                "title": "Acoustic vs Electric: Which Guitar Should You Buy First?",
                "category": "Gear Guides",
                "excerpt": "The eternal beginner question, definitively answered. Pros, cons, and our honest Nairobi-specific recommendation.",
                "body": """This is the question we get asked most often in our Nairobi store. There's no single right answer, but there's a right answer for you.

**Start with Acoustic If:**
- You want to play folk, fingerpicking, or traditional Kenyan music
- You'll be playing without amplification most of the time
- You're on a tighter budget (no amp needed)

**Start with Electric If:**
- Rock, blues, or funk is your primary goal
- You want to play in a band sooner rather than later

**Our Honest Recommendation:** For most Nairobi beginners who aren't sure yet, start with the Yamaha FG800 acoustic.""",
                "tags": "acoustic,electric,beginner,buying-guide",
                "is_featured": False,
            },
            {
                "title": "The Rise of Afrobeats Production: Tools of the Trade",
                "category": "Music Production",
                "excerpt": "Afrobeats is taking the world by storm. We break down the gear and software behind the genre's signature sound.",
                "body": """Kenya and Nigeria are leading a global music revolution. The tools have never been more accessible.

**The Afrobeats Drum Sound**

The foundation of any Afrobeats track is the drums. Roland drum machines are widely used for their punchy, compressed kick sounds. For organic feel, many producers layer live hand percussion.

**The Chords and Melody**

The signature bright, gated synth chords of Afrobeats are produced with VST synthesizers like Massive or Sylenth1. The Roland FP-30X digital piano is perfect for playing in those chord stabs.""",
                "tags": "afrobeats,production,kenya,nairobi",
                "is_featured": False,
            },
            {
                "title": "How to Care for Your Guitar in Kenya's Climate",
                "category": "Maintenance",
                "excerpt": "Kenya's humidity variation, dust, and temperature swings can damage instruments. Here's how to keep your guitar healthy year-round.",
                "body": """Kenya's climate presents unique challenges for instrument maintenance that most international guides don't address.

**Humidity is Your Main Enemy**

Most quality acoustic guitars are built at 45-55% relative humidity. In Nairobi's dry season (June-August), indoor humidity can drop below 30%, causing wood to contract, raising action and potentially cracking the top.

**What to Do:**
1. Invest in a soundhole humidifier (KES 800-1,500 at Maecky Sounds)
2. Store your guitar in its case when not playing
3. Keep away from direct sunlight and air conditioning vents

**String Maintenance**

Kenya's humidity and the oils on your hands accelerate string corrosion. Wipe strings with a dry cloth after every session. Change strings every 2-3 months if you play daily.""",
                "tags": "maintenance,guitar,kenya,humidity",
                "is_featured": False,
            },
        ]

        count = 0
        for p_data in posts_data:
            cat = blog_categories[p_data.pop("category")]
            post, created = BlogPost.objects.get_or_create(
                slug=slugify(p_data["title"]),
                defaults={
                    **p_data,
                    "category": cat,
                    "author": admin_user,
                    "status": BlogPost.Status.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ {count} blog posts created"))

    # ── Coupons ────────────────────────────────────────────────────────────────

    def _seed_coupons(self):
        from apps.coupons.models import Coupon

        coupons_data = [
            {
                "code": "WELCOME10",
                "description": "10% off your first order — welcome to Maecky Sounds!",
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": 10,
                "minimum_order": 5000,
                "valid_from": timezone.now(),
                "valid_until": timezone.now().replace(year=timezone.now().year + 1),
                "is_active": True,
            },
            {
                "code": "SAVE20",
                "description": "20% off orders over KES 50,000.",
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": 20,
                "minimum_order": 50000,
                "maximum_discount": 20000,
                "valid_from": timezone.now(),
                "valid_until": timezone.now().replace(year=timezone.now().year + 1),
                "is_active": True,
            },
            {
                "code": "FREESHIP",
                "description": "Free shipping on any order.",
                "discount_type": Coupon.DiscountType.FREE_SHIP,
                "discount_value": 0,
                "minimum_order": 0,
                "valid_from": timezone.now(),
                "valid_until": timezone.now().replace(year=timezone.now().year + 1),
                "is_active": True,
            },
            {
                "code": "NAIROBI15",
                "description": "15% off for Nairobi Music Festival — limited time.",
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": 15,
                "minimum_order": 10000,
                "usage_limit": 200,
                "valid_from": timezone.now(),
                "valid_until": timezone.now().replace(year=timezone.now().year + 1),
                "is_active": True,
            },
        ]

        count = 0
        for c_data in coupons_data:
            _, created = Coupon.objects.get_or_create(
                code=c_data["code"],
                defaults=c_data,
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ {count} coupon codes created (WELCOME10, SAVE20, FREESHIP, NAIROBI15)"))