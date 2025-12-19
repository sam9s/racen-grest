"""
GREST Product Scraper - Uses Shopify Admin API to populate PostgreSQL database.
Run this script to update product pricing and specifications.

Requires environment variables:
- SHOPIFY_ACCESS_TOKEN: Admin API access token
- SHOPIFY_STORE_URL: Store URL (e.g., grestmobile.myshopify.com)
"""

import os
import json
import requests
from database import get_db_session, GRESTProduct, init_database

SHOPIFY_STORE_URL = os.environ.get('SHOPIFY_STORE_URL', 'grestmobile.myshopify.com')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
API_VERSION = '2024-10'

def get_shopify_headers():
    """Get headers for Shopify Admin API requests."""
    return {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }

def fetch_all_products():
    """Fetch ALL products from Shopify Admin API with pagination."""
    if not SHOPIFY_ACCESS_TOKEN:
        print("ERROR: SHOPIFY_ACCESS_TOKEN not set!")
        return []
    
    all_products = []
    base_url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/products.json"
    
    params = {'limit': 250}
    
    while True:
        response = requests.get(base_url, headers=get_shopify_headers(), params=params)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text[:200]}")
            break
        
        data = response.json()
        products = data.get('products', [])
        all_products.extend(products)
        
        print(f"Fetched {len(products)} products (total: {len(all_products)})")
        
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            import re
            next_match = re.search(r'<([^>]+)>; rel="next"', link_header)
            if next_match:
                base_url = next_match.group(1)
                params = {}
            else:
                break
        else:
            break
    
    return all_products

def extract_specs_from_body(body_html):
    """Extract specifications from product body HTML."""
    specs = {}
    if not body_html:
        return specs
    
    try:
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
        
        for text in soup.stripped_strings:
            if ':' in text and len(text) < 100:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    if key and value and key not in specs:
                        specs[key] = value
    except Exception as e:
        print(f"  Spec extraction error: {e}")
    
    return specs

def fetch_product_metafields(product_id):
    """Fetch metafields for a specific product from Shopify Admin API."""
    if not SHOPIFY_ACCESS_TOKEN:
        return {}
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
    
    try:
        response = requests.get(url, headers=get_shopify_headers())
        if response.status_code == 200:
            metafields = response.json().get('metafields', [])
            specs = {}
            for mf in metafields:
                namespace = mf.get('namespace', '')
                key = mf.get('key', '')
                value = mf.get('value', '')
                
                if namespace == 'custom' and value:
                    spec_name = key.replace('_', ' ').title()
                    specs[spec_name] = value
                elif namespace == 'global' and key == 'description_tag':
                    specs['Meta Description'] = value
            
            return specs
    except Exception as e:
        print(f"  Metafield fetch error: {e}")
    
    return {}

def get_category(title, product_type=''):
    """Determine product category from title and product_type."""
    combined = f"{title} {product_type}".lower()
    
    if 'ipad' in combined:
        return 'iPad'
    elif 'macbook' in combined:
        return 'MacBook'
    elif 'iphone' in combined:
        return 'iPhone'
    elif 'watch' in combined:
        return 'Apple Watch'
    elif 'airpod' in combined:
        return 'AirPods'
    elif 'protection' in combined or 'damage' in combined or 'warranty' in combined:
        return 'Protection Plan'
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

def parse_variant_options(variants):
    """Extract storage, colors, and conditions from variants."""
    storage_options = set()
    colors = set()
    conditions = set()
    
    for v in variants:
        for opt_key in ['option1', 'option2', 'option3']:
            opt = v.get(opt_key, '')
            if opt:
                opt_lower = opt.lower()
                if 'gb' in opt_lower or 'tb' in opt_lower:
                    storage_options.add(opt)
                elif opt_lower in ['fair', 'good', 'superb', 'excellent', 'like new', 'refurbished']:
                    conditions.add(opt)
                elif opt_lower not in ['', 'default', 'title']:
                    colors.add(opt)
    
    return list(storage_options), list(colors), list(conditions)

def populate_database():
    """Fetch all products from Shopify Admin API and populate database."""
    init_database()
    
    print("=" * 60)
    print("GREST Product Sync - Shopify Admin API")
    print("=" * 60)
    print(f"Store: {SHOPIFY_STORE_URL}")
    print()
    
    all_products = fetch_all_products()
    
    if not all_products:
        print("No products fetched. Check API credentials.")
        return
    
    print(f"\nProcessing {len(all_products)} products...")
    print("-" * 60)
    
    products_added = 0
    products_updated = 0
    products_skipped = 0
    
    for product in all_products:
        title = product.get('title', '')
        product_id = product.get('id')
        handle = product.get('handle', '')
        product_type = product.get('product_type', '')
        
        if not title or not product_id:
            products_skipped += 1
            continue
        
        category = get_category(title, product_type)
        
        if category == 'Protection Plan':
            print(f"  Skipping protection plan: {title[:50]}")
            products_skipped += 1
            continue
        
        variants = product.get('variants', [])
        min_price, max_price = get_price_range(variants)
        
        if not min_price or min_price <= 0:
            print(f"  Skipping (no price): {title[:50]}")
            products_skipped += 1
            continue
        
        first_variant = variants[0] if variants else {}
        compare_price = None
        try:
            cp = first_variant.get('compare_at_price')
            if cp:
                compare_price = float(cp)
        except:
            pass
        
        discount = None
        if compare_price and min_price and compare_price > min_price:
            discount = int(((compare_price - min_price) / compare_price) * 100)
        
        specs = extract_specs_from_body(product.get('body_html', ''))
        metafield_specs = fetch_product_metafields(product_id)
        specs.update(metafield_specs)
        storage_options, colors, conditions = parse_variant_options(variants)
        
        images = product.get('images', [])
        image_url = images[0].get('src', '') if images else None
        
        product_url = f"https://grest.in/products/{handle}"
        sku = f"SHOPIFY_{product_id}"
        
        total_inventory = sum(v.get('inventory_quantity', 0) for v in variants)
        in_stock = total_inventory > 0 or any(v.get('inventory_policy') == 'continue' for v in variants)
        
        specs_json = json.dumps({
            'specs': specs,
            'storage_options': storage_options,
            'colors': colors,
            'conditions': conditions,
            'variant_count': len(variants),
            'total_inventory': total_inventory,
            'product_type': product_type,
            'tags': product.get('tags', ''),
            'price_range': f"Rs. {int(min_price):,} - Rs. {int(max_price):,}" if max_price != min_price else f"Rs. {int(min_price):,}"
        })
        
        with get_db_session() as db:
            if db is None:
                print("Database not available!")
                return
            
            existing = db.query(GRESTProduct).filter(GRESTProduct.sku == sku).first()
            
            if existing:
                existing.name = title
                existing.price = min_price
                existing.original_price = compare_price
                existing.discount_percent = discount
                existing.category = category
                existing.specifications = specs_json
                existing.product_url = product_url
                existing.image_url = image_url
                existing.in_stock = in_stock
                products_updated += 1
                print(f"  Updated: {title[:40]} - Rs. {int(min_price):,}")
            else:
                new_product = GRESTProduct(
                    sku=sku,
                    name=title,
                    category=category,
                    price=min_price,
                    original_price=compare_price,
                    discount_percent=discount,
                    in_stock=in_stock,
                    warranty_months=6,
                    product_url=product_url,
                    image_url=image_url,
                    specifications=specs_json,
                )
                db.add(new_product)
                products_added += 1
                print(f"  Added: {title[:40]} - Rs. {int(min_price):,}")
    
    print()
    print("=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"Added: {products_added}")
    print(f"Updated: {products_updated}")
    print(f"Skipped: {products_skipped}")
    print()
    
    with get_db_session() as db:
        if db:
            total = db.query(GRESTProduct).count()
            print(f"Total products in database: {total}")
            
            print("\nProducts by category:")
            categories = db.query(GRESTProduct.category).distinct().all()
            for (cat,) in categories:
                count = db.query(GRESTProduct).filter(GRESTProduct.category == cat).count()
                print(f"  - {cat}: {count}")
            
            print("\nPrice range samples:")
            cheapest = db.query(GRESTProduct).filter(GRESTProduct.category == 'iPhone').order_by(GRESTProduct.price).first()
            if cheapest:
                print(f"  Cheapest iPhone: {cheapest.name} - Rs. {int(cheapest.price):,}")
            
            expensive = db.query(GRESTProduct).order_by(GRESTProduct.price.desc()).first()
            if expensive:
                print(f"  Most expensive: {expensive.name} - Rs. {int(expensive.price):,}")

if __name__ == "__main__":
    populate_database()
