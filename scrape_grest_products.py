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

def parse_variant_options_single(variant):
    """Extract storage, color, and condition from a single variant."""
    storage = None
    color = None
    condition = None
    
    for opt_key in ['option1', 'option2', 'option3']:
        opt = variant.get(opt_key, '')
        if opt:
            opt_lower = opt.lower().strip()
            if 'gb' in opt_lower or 'tb' in opt_lower:
                storage = opt.strip()
            elif opt_lower in ['fair', 'good', 'superb', 'excellent', 'like new', 'refurbished']:
                condition = opt.strip()
            elif opt_lower not in ['', 'default', 'title', 'random']:
                if not color:
                    color = opt.strip()
    
    return storage, color, condition


def populate_database():
    """Fetch all products from Shopify Admin API and populate database with per-variant rows."""
    init_database()
    
    print("=" * 60)
    print("GREST Product Sync - Shopify Admin API (Per-Variant)")
    print("=" * 60)
    print(f"Store: {SHOPIFY_STORE_URL}")
    print()
    
    all_products = fetch_all_products()
    
    if not all_products:
        print("No products fetched. Check API credentials.")
        return
    
    print(f"\nProcessing {len(all_products)} products...")
    print("-" * 60)
    
    variants_added = 0
    variants_updated = 0
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
        if not variants:
            print(f"  Skipping (no variants): {title[:50]}")
            products_skipped += 1
            continue
        
        specs = extract_specs_from_body(product.get('body_html', ''))
        
        images = product.get('images', [])
        image_url = images[0].get('src', '') if images else None
        
        base_product_url = f"https://grest.in/products/{handle}"
        
        min_price, max_price = get_price_range(variants)
        storage_options, colors, conditions = parse_variant_options(variants)
        
        specs_json = json.dumps({
            'specs': specs,
            'storage_options': storage_options,
            'colors': colors,
            'conditions': conditions,
            'variant_count': len(variants),
            'product_type': product_type,
            'tags': product.get('tags', ''),
            'price_range': f"Rs. {int(min_price):,} - Rs. {int(max_price):,}" if max_price and min_price and max_price != min_price else f"Rs. {int(min_price):,}" if min_price else ""
        })
        
        with get_db_session() as db:
            if db is None:
                print("Database not available!")
                return
            
            for variant in variants:
                variant_id = variant.get('id')
                variant_price = None
                try:
                    variant_price = float(variant.get('price', 0))
                except:
                    pass
                
                if not variant_price or variant_price <= 0:
                    continue
                
                compare_price = None
                try:
                    cp = variant.get('compare_at_price')
                    if cp:
                        compare_price = float(cp)
                except:
                    pass
                
                discount = None
                if compare_price and variant_price and compare_price > variant_price:
                    discount = int(((compare_price - variant_price) / compare_price) * 100)
                
                storage, color, condition = parse_variant_options_single(variant)
                
                inventory_qty = variant.get('inventory_quantity', 0)
                inventory_policy = variant.get('inventory_policy', '')
                in_stock = inventory_qty > 0 or inventory_policy == 'continue'
                
                sku = f"SHOPIFY_{product_id}_{variant_id}"
                product_url = f"{base_product_url}?variant={variant_id}"
                
                variant_title_parts = [title]
                if storage:
                    variant_title_parts.append(storage)
                if condition:
                    variant_title_parts.append(condition)
                variant_name = ' - '.join(variant_title_parts) if len(variant_title_parts) > 1 else title
                
                existing = db.query(GRESTProduct).filter(GRESTProduct.sku == sku).first()
                
                if existing:
                    existing.name = title
                    existing.price = variant_price
                    existing.original_price = compare_price
                    existing.discount_percent = discount
                    existing.category = category
                    existing.storage = storage
                    existing.color = color
                    existing.condition = condition
                    existing.variant = variant_name
                    existing.specifications = specs_json
                    existing.product_url = product_url
                    existing.image_url = image_url
                    existing.in_stock = in_stock
                    variants_updated += 1
                else:
                    new_variant = GRESTProduct(
                        sku=sku,
                        name=title,
                        category=category,
                        variant=variant_name,
                        storage=storage,
                        color=color,
                        condition=condition,
                        price=variant_price,
                        original_price=compare_price,
                        discount_percent=discount,
                        in_stock=in_stock,
                        warranty_months=12,
                        product_url=product_url,
                        image_url=image_url,
                        specifications=specs_json,
                    )
                    db.add(new_variant)
                    variants_added += 1
        
        print(f"  Processed: {title[:40]} ({len(variants)} variants)")
    
    print()
    print("=" * 60)
    print("SYNC COMPLETE (Per-Variant)")
    print("=" * 60)
    print(f"Variants Added: {variants_added}")
    print(f"Variants Updated: {variants_updated}")
    print(f"Products Skipped: {products_skipped}")
    print()
    
    with get_db_session() as db:
        if db:
            total = db.query(GRESTProduct).count()
            print(f"Total variants in database: {total}")
            
            print("\nVariants by category:")
            categories = db.query(GRESTProduct.category).distinct().all()
            for (cat,) in categories:
                count = db.query(GRESTProduct).filter(GRESTProduct.category == cat).count()
                print(f"  - {cat}: {count}")
            
            print("\nVariants by condition:")
            conditions = db.query(GRESTProduct.condition).distinct().all()
            for (cond,) in conditions:
                count = db.query(GRESTProduct).filter(GRESTProduct.condition == cond).count()
                print(f"  - {cond or 'Unknown'}: {count}")
            
            print("\nVariants by storage:")
            storages = db.query(GRESTProduct.storage).distinct().all()
            for (stor,) in storages:
                count = db.query(GRESTProduct).filter(GRESTProduct.storage == stor).count()
                print(f"  - {stor or 'Unknown'}: {count}")
            
            print("\nPrice samples:")
            sample = db.query(GRESTProduct).filter(
                GRESTProduct.name.ilike('%iPhone 12%'),
                GRESTProduct.storage == '128 GB',
                GRESTProduct.condition == 'Fair'
            ).first()
            if sample:
                print(f"  iPhone 12 128GB Fair: Rs. {int(sample.price):,}")
            
            sample2 = db.query(GRESTProduct).filter(
                GRESTProduct.name.ilike('%iPhone 12%'),
                GRESTProduct.storage == '256 GB',
                GRESTProduct.condition == 'Superb'
            ).first()
            if sample2:
                print(f"  iPhone 12 256GB Superb: Rs. {int(sample2.price):,}")

if __name__ == "__main__":
    populate_database()
