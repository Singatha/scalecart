import asyncio

from sqlalchemy import select

from .database import session_factory
from .models import Category, Product, ProductImage, ProductVariant

CATEGORY_DATA = [
    ("Home", "home", "Quiet, useful objects for considered spaces."),
    ("Kitchen", "kitchen", "Tools and tableware made for daily rituals."),
    ("Everyday", "everyday", "Durable companions for work and travel."),
]

PRODUCT_DATA = [
    {
        "category": "home",
        "name": "Woven Linen Throw",
        "slug": "woven-linen-throw",
        "description": "A weighty, breathable linen throw with a soft washed finish.",
        "sku": "THROW-LINEN-NATURAL",
        "variant": "Natural",
        "price": 129900,
        "stock": 14,
        "colour": "E7DED0",
    },
    {
        "category": "kitchen",
        "name": "Sandstone Mug",
        "slug": "sandstone-mug",
        "description": "Wheel-thrown stoneware with a warm, tactile glaze.",
        "sku": "MUG-STONE-SAND",
        "variant": "Sand",
        "price": 34900,
        "stock": 32,
        "colour": "C9B38C",
    },
    {
        "category": "home",
        "name": "Oak Catchall Tray",
        "slug": "oak-catchall-tray",
        "description": "A hand-finished solid oak tray for the small things worth keeping close.",
        "sku": "TRAY-OAK-SMALL",
        "variant": "Small",
        "price": 59900,
        "stock": 9,
        "colour": "A97850",
    },
    {
        "category": "everyday",
        "name": "Canvas Market Tote",
        "slug": "canvas-market-tote",
        "description": "Heavy cotton canvas with reinforced handles and an interior pocket.",
        "sku": "TOTE-CANVAS-OLIVE",
        "variant": "Olive",
        "price": 74900,
        "stock": 21,
        "colour": "78806A",
    },
    {
        "category": "kitchen",
        "name": "Beech Serving Board",
        "slug": "beech-serving-board",
        "description": "Responsibly sourced beech shaped and oiled by hand.",
        "sku": "BOARD-BEECH-LARGE",
        "variant": "Large",
        "price": 89900,
        "stock": 7,
        "colour": "D3B98C",
    },
    {
        "category": "everyday",
        "name": "Brass Key Clip",
        "slug": "brass-key-clip",
        "description": "A compact solid-brass clip designed to develop a rich patina.",
        "sku": "CLIP-BRASS-ONE",
        "variant": "One size",
        "price": 22900,
        "stock": 40,
        "colour": "B58A45",
    },
]


def image_url(colour: str, name: str) -> str:
    label = name.replace(" ", "+")
    return f"https://placehold.co/900x1100/{colour}/19352B?text={label}"


async def seed_catalog() -> None:
    if session_factory is None:
        raise SystemExit("DATABASE_URL is required before seeding.")
    async with session_factory() as session:
        categories: dict[str, Category] = {}
        for name, slug, description in CATEGORY_DATA:
            category = await session.scalar(select(Category).where(Category.slug == slug))
            if category is None:
                category = Category(name=name, slug=slug, description=description)
                session.add(category)
                await session.flush()
            categories[slug] = category

        created = 0
        for item in PRODUCT_DATA:
            existing = await session.scalar(select(Product.id).where(Product.slug == item["slug"]))
            if existing:
                continue
            product = Product(
                category=categories[item["category"]],
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                brand="Common Ground",
                status="active",
                featured=created < 3,
                variants=[
                    ProductVariant(
                        sku=item["sku"],
                        name=item["variant"],
                        price_amount=item["price"],
                        currency="ZAR",
                        stock_quantity=item["stock"],
                        attributes={"finish": item["variant"]},
                    )
                ],
                images=[
                    ProductImage(
                        url=image_url(item["colour"], item["name"]),
                        alt_text=item["name"],
                        position=0,
                    )
                ],
            )
            session.add(product)
            created += 1
        await session.commit()
    print(f"Catalog seed complete; {created} products created.")


if __name__ == "__main__":
    asyncio.run(seed_catalog())
