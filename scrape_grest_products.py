"""
GREST Product Scraper - Uses Shopify JSON API to populate PostgreSQL database.
Run this script to update product pricing and specifications.
"""

import json
import requests
from database import get_db_session, GRESTProduct, init_database

PRODUCT_SLUGS = [
    "iphone-16",
    "iphone-15",
    "refurbished-apple-iphone-14",
    "refurbished-apple-iphone-14-plus",
    "refurbished-apple-iphone-14-pro",
    "refurbished-apple-iphone-14-pro-max",
    "refurbished-apple-iphone-13",
    "refurbished-apple-iphone-13-mini",
    "refurbished-iphone-13-pro",
    "apple-iphone-13-pro-max",
    "refurbished-apple-iphone-12",
    "refurbished-iphone-12-mini",
    "refurbished-apple-iphone-12-pro",
    "refurbished-apple-iphone-12-pro-max",
    "refurbished-iphone-11",
    "refurbished-apple-iphone-11-pro",
    "refurbished-apple-iphone-11-pro-max",
    "apple-ipad-a2602-a13-bionic-9th-gen-wifi202164gb10-2",
    "apple-ipad-pro-a1934-a12x-bionic-1st-gen-wifi-cellular-201864gb11-1",
]

def fetch_product_json(slug):
    """Fetch product data from Shopify JSON API."""
    url = f"https://grest.in/products/{slug}.json"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json().get('product', {})
    except Exception as e:
        print(f"Error fetching {slug}: {e}")
        return None

def extract_specs_from_body(body_html):
    """Extract specifications from product body HTML."""
    specs = {}
    if not body_html:
        return specs
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body_html, 'html.parser')
    
    rows = soup.find_all('tr')
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if key and value:
                specs[key] = value
    
    return specs

def get_category(title):
    """Determine product category from title."""
    title_lower = title.lower()
    if 'ipad' in title_lower:
        return 'iPad'
    elif 'macbook' in title_lower:
        return 'MacBook'
    elif 'iphone' in title_lower:
        return 'iPhone'
    return 'Other'

def get_price_range(variants):
    """Get min and max prices from all variants."""
    prices = []
    for v in variants:
        try:
            price = float(v.get('price', 0))
            if price > 0:
                prices.append(price)
        except:
            pass
    
    if prices:
        return min(prices), max(prices)
    return None, None

def populate_database():
    """Fetch all products from Shopify API and populate database."""
    init_database()
    
    print(f"Fetching {len(PRODUCT_SLUGS)} products from Shopify API...")
    
    products_added = 0
    products_updated = 0
    
    for slug in PRODUCT_SLUGS:
        print(f"Fetching: {slug}")
        product = fetch_product_json(slug)
        
        if not product:
            print(f"  -> Failed to fetch")
            continue
        
        title = product.get('title', '')
        if not title:
            print(f"  -> No title found")
            continue
        
        variants = product.get('variants', [])
        min_price, max_price = get_price_range(variants)
        
        if not min_price:
            print(f"  -> No price found")
            continue
        
        first_variant = variants[0] if variants else {}
        compare_price = None
        try:
            compare_price = float(first_variant.get('compare_at_price', 0))
        except:
            pass
        
        discount = None
        if compare_price and min_price and compare_price > min_price:
            discount = int(((compare_price - min_price) / compare_price) * 100)
        
        specs = extract_specs_from_body(product.get('body_html', ''))
        
        storage_options = set()
        colors = set()
        conditions = set()
        
        for v in variants:
            opt1 = v.get('option1', '')
            opt2 = v.get('option2', '')
            opt3 = v.get('option3', '')
            
            for opt in [opt1, opt2, opt3]:
                if opt:
                    opt_lower = opt.lower()
                    if 'gb' in opt_lower or 'tb' in opt_lower:
                        storage_options.add(opt)
                    elif opt_lower in ['fair', 'good', 'superb', 'excellent']:
                        conditions.add(opt)
                    elif opt_lower not in ['', 'default']:
                        colors.add(opt)
        
        images = product.get('images', [])
        image_url = images[0].get('src', '') if images else None
        
        category = get_category(title)
        product_url = f"https://grest.in/products/{slug}"
        sku = slug.upper().replace('-', '_')[:50]
        
        product_data = {
            'name': title,
            'min_price': min_price,
            'max_price': max_price,
            'compare_price': compare_price,
            'discount': discount,
            'category': category,
            'storage_options': list(storage_options),
            'colors': list(colors),
            'conditions': list(conditions),
            'variant_count': len(variants),
            'specs': specs,
            'image_url': image_url,
            'product_url': product_url,
        }
        
        with get_db_session() as db:
            if db is None:
                print("Database not available!")
                return
            
            existing = db.query(GRESTProduct).filter(GRESTProduct.sku == sku).first()
            
            specs_json = json.dumps({
                'specs': specs,
                'storage_options': list(storage_options),
                'colors': list(colors),
                'conditions': list(conditions),
                'variant_count': len(variants),
                'price_range': f"Rs. {int(min_price):,} - Rs. {int(max_price):,}" if max_price != min_price else f"Rs. {int(min_price):,}"
            })
            
            if existing:
                existing.name = title
                existing.price = min_price
                existing.original_price = compare_price
                existing.discount_percent = discount
                existing.category = category
                existing.specifications = specs_json
                existing.product_url = product_url
                existing.image_url = image_url
                existing.in_stock = True
                products_updated += 1
                print(f"  -> Updated: {title} - Starting Rs. {int(min_price):,}")
            else:
                new_product = GRESTProduct(
                    sku=sku,
                    name=title,
                    category=category,
                    price=min_price,
                    original_price=compare_price,
                    discount_percent=discount,
                    in_stock=True,
                    warranty_months=6,
                    product_url=product_url,
                    image_url=image_url,
                    specifications=specs_json,
                )
                db.add(new_product)
                products_added += 1
                print(f"  -> Added: {title} - Starting Rs. {int(min_price):,}")
    
    print(f"\n{'='*50}")
    print(f"Summary: {products_added} added, {products_updated} updated")
    print(f"{'='*50}")
    
    with get_db_session() as db:
        if db:
            total = db.query(GRESTProduct).count()
            print(f"Total products in database: {total}")
            
            print("\nSample products:")
            products = db.query(GRESTProduct).order_by(GRESTProduct.price).limit(5).all()
            for p in products:
                print(f"  - {p.name}: Rs. {int(p.price):,} ({p.category})")

if __name__ == "__main__":
    populate_database()
