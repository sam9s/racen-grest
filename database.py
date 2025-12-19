"""
Database Models and Connection for GRESTA Chatbot

PostgreSQL database for:
- Conversation logs with analytics
- User feedback on responses
- Session tracking
- GREST product pricing (source of truth for prices)
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None

Base = declarative_base()


class UserAccount(Base):
    """Stores user accounts across different channels."""
    __tablename__ = "user_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(50), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    profile_image = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sessions = relationship("ChatSession", back_populates="user")
    
    __table_args__ = (
        UniqueConstraint('channel', 'external_id', name='uq_channel_external_id'),
    )


class ChatSession(Base):
    """Tracks individual chat sessions."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    channel = Column(String(50), default="web")
    
    user = relationship("UserAccount", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session")


class Conversation(Base):
    """Stores individual conversation exchanges."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.session_id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_question = Column(Text, nullable=False)
    bot_answer = Column(Text, nullable=False)
    safety_flagged = Column(Boolean, default=False, index=True)
    safety_category = Column(String(100), nullable=True)
    sources_used = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    session = relationship("ChatSession", back_populates="conversations")
    feedback = relationship("ResponseFeedback", back_populates="conversation", uselist=False)


class ResponseFeedback(Base):
    """Stores user feedback on bot responses."""
    __tablename__ = "response_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="feedback")


class AnalyticsDaily(Base):
    """Pre-aggregated daily analytics for performance."""
    __tablename__ = "analytics_daily"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    total_conversations = Column(Integer, default=0)
    unique_sessions = Column(Integer, default=0)
    safety_flags = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, nullable=True)
    positive_feedback = Column(Integer, default=0)
    negative_feedback = Column(Integer, default=0)


class ConversationSummary(Base):
    """Stores LLM-generated conversation summaries for personalization."""
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), unique=True, index=True)
    emotional_themes = Column(Text, nullable=True)
    recommended_programs = Column(Text, nullable=True)
    last_topics = Column(Text, nullable=True)
    conversation_status = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("UserAccount")


class GRESTProduct(Base):
    """
    GREST Product Pricing Table - Source of truth for product prices.
    This table stores current pricing for all GREST products (iPhones, MacBooks).
    Prices are updated here when they change, and GRESTA uses this as the authoritative source.
    """
    __tablename__ = "grest_products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    variant = Column(String(255), nullable=True)
    storage = Column(String(50), nullable=True)
    color = Column(String(100), nullable=True)
    condition = Column(String(100), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Integer, nullable=True)
    in_stock = Column(Boolean, default=True, index=True)
    warranty_months = Column(Integer, default=12)
    product_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_database():
    """Initialize database tables."""
    if engine:
        Base.metadata.create_all(bind=engine)
        return True
    return False


@contextmanager
def get_db_session():
    """Get a database session with automatic cleanup."""
    if SessionLocal is None:
        yield None
        return
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_database_available():
    """Check if database connection is available."""
    return engine is not None and DATABASE_URL is not None


def get_or_create_user(channel: str, external_id: str, email: str = None, 
                       display_name: str = None, profile_image: str = None):
    """
    Get existing user or create new one.
    Returns (user_data, created) tuple where user_data is a dict with id, display_name, etc.
    """
    with get_db_session() as db:
        if db is None:
            return None, False
        
        user = db.query(UserAccount).filter(
            UserAccount.channel == channel,
            UserAccount.external_id == external_id
        ).first()
        
        if user:
            user.last_seen = datetime.utcnow()
            if email and not user.email:
                user.email = email
            if display_name and not user.display_name:
                user.display_name = display_name
            if profile_image:
                user.profile_image = profile_image
            db.commit()
            user_data = {
                'id': user.id,
                'display_name': user.display_name,
                'email': user.email
            }
            return user_data, False
        
        user = UserAccount(
            channel=channel,
            external_id=external_id,
            email=email,
            display_name=display_name,
            profile_image=profile_image
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_data = {
            'id': user.id,
            'display_name': user.display_name,
            'email': user.email
        }
        return user_data, True


def get_user_by_email(email: str):
    """Get user by email address."""
    with get_db_session() as db:
        if db is None:
            return None
        return db.query(UserAccount).filter(UserAccount.email == email).first()


def get_user_conversation_history(user_id: int, limit: int = 20):
    """Get recent conversation history for a user."""
    with get_db_session() as db:
        if db is None:
            return []
        
        conversations = db.query(Conversation).join(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(Conversation.timestamp.desc()).limit(limit).all()
        
        return [
            {
                'question': c.user_question,
                'answer': c.bot_answer,
                'timestamp': c.timestamp.isoformat() if c.timestamp else None
            }
            for c in reversed(conversations)
        ]


def get_conversation_summary(user_id: int):
    """Get the stored conversation summary for a user."""
    with get_db_session() as db:
        if db is None:
            return None
        
        summary = db.query(ConversationSummary).filter(
            ConversationSummary.user_id == user_id
        ).first()
        
        if summary:
            return {
                'emotional_themes': summary.emotional_themes,
                'recommended_programs': summary.recommended_programs,
                'last_topics': summary.last_topics,
                'conversation_status': summary.conversation_status,
                'updated_at': summary.updated_at.isoformat() if summary.updated_at else None
            }
        return None


def upsert_conversation_summary(user_id: int, emotional_themes: str = None,
                                 recommended_programs: str = None,
                                 last_topics: str = None,
                                 conversation_status: str = None):
    """Create or update conversation summary for a user."""
    with get_db_session() as db:
        if db is None:
            return False
        
        summary = db.query(ConversationSummary).filter(
            ConversationSummary.user_id == user_id
        ).first()
        
        if summary:
            if emotional_themes is not None:
                summary.emotional_themes = emotional_themes
            if recommended_programs is not None:
                summary.recommended_programs = recommended_programs
            if last_topics is not None:
                summary.last_topics = last_topics
            if conversation_status is not None:
                summary.conversation_status = conversation_status
            summary.updated_at = datetime.utcnow()
        else:
            summary = ConversationSummary(
                user_id=user_id,
                emotional_themes=emotional_themes,
                recommended_programs=recommended_programs,
                last_topics=last_topics,
                conversation_status=conversation_status
            )
            db.add(summary)
        
        db.commit()
        return True


def get_all_products(category: str = None, in_stock_only: bool = True):
    """
    Get all GREST products, optionally filtered by category.
    Returns list of product dictionaries.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        query = db.query(GRESTProduct)
        
        if category:
            query = query.filter(GRESTProduct.category.ilike(f"%{category}%"))
        
        if in_stock_only:
            query = query.filter(GRESTProduct.in_stock == True)
        
        products = query.order_by(GRESTProduct.category, GRESTProduct.name).all()
        
        return [
            {
                'id': p.id,
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'variant': p.variant,
                'storage': p.storage,
                'color': p.color,
                'condition': p.condition,
                'price': float(p.price) if p.price else None,
                'original_price': float(p.original_price) if p.original_price else None,
                'discount_percent': p.discount_percent,
                'in_stock': p.in_stock,
                'warranty_months': p.warranty_months,
                'product_url': p.product_url,
                'image_url': p.image_url,
                'description': p.description,
                'specifications': p.specifications
            }
            for p in products
        ]


def get_product_by_name(name: str):
    """
    Search for products by name (case-insensitive partial match).
    Returns list of matching products.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        products = db.query(GRESTProduct).filter(
            GRESTProduct.name.ilike(f"%{name}%")
        ).all()
        
        return [
            {
                'id': p.id,
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'variant': p.variant,
                'storage': p.storage,
                'color': p.color,
                'condition': p.condition,
                'price': float(p.price) if p.price else None,
                'original_price': float(p.original_price) if p.original_price else None,
                'discount_percent': p.discount_percent,
                'in_stock': p.in_stock,
                'warranty_months': p.warranty_months,
                'product_url': p.product_url
            }
            for p in products
        ]


def get_product_with_specs(product_name: str):
    """
    Get product with full specifications by name (case-insensitive).
    Returns first match with specs parsed from JSON.
    """
    import json
    with get_db_session() as db:
        if db is None:
            return None
        
        product = db.query(GRESTProduct).filter(
            GRESTProduct.name.ilike(f"%{product_name}%")
        ).first()
        
        if product:
            specs = {}
            if product.specifications:
                try:
                    spec_data = json.loads(product.specifications) if isinstance(product.specifications, str) else product.specifications
                    specs = spec_data.get('specs', {})
                    specs['Storage Options'] = ', '.join(spec_data.get('storage_options', []))
                    specs['Colors Available'] = ', '.join(spec_data.get('colors', []))
                    specs['Conditions'] = ', '.join(spec_data.get('conditions', []))
                    specs['Price Range'] = spec_data.get('price_range', '')
                except:
                    pass
            
            return {
                'name': product.name,
                'category': product.category,
                'price': float(product.price) if product.price else None,
                'original_price': float(product.original_price) if product.original_price else None,
                'discount_percent': product.discount_percent,
                'warranty_months': product.warranty_months,
                'product_url': product.product_url,
                'specs': specs
            }
        return None


def get_product_by_sku(sku: str):
    """Get a single product by its SKU."""
    with get_db_session() as db:
        if db is None:
            return None
        
        product = db.query(GRESTProduct).filter(
            GRESTProduct.sku == sku
        ).first()
        
        if product:
            return {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'variant': product.variant,
                'storage': product.storage,
                'color': product.color,
                'condition': product.condition,
                'price': float(product.price) if product.price else None,
                'original_price': float(product.original_price) if product.original_price else None,
                'discount_percent': product.discount_percent,
                'in_stock': product.in_stock,
                'warranty_months': product.warranty_months,
                'product_url': product.product_url,
                'image_url': product.image_url,
                'description': product.description,
                'specifications': product.specifications
            }
        return None


def upsert_product(sku: str, name: str, category: str, price: float, **kwargs):
    """
    Create or update a GREST product.
    Used for syncing product data from external sources.
    """
    with get_db_session() as db:
        if db is None:
            return False
        
        product = db.query(GRESTProduct).filter(
            GRESTProduct.sku == sku
        ).first()
        
        if product:
            product.name = name
            product.category = category
            product.price = price
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            product.updated_at = datetime.utcnow()
        else:
            product = GRESTProduct(
                sku=sku,
                name=name,
                category=category,
                price=price,
                **kwargs
            )
            db.add(product)
        
        db.commit()
        return True


def search_products_for_chatbot(query: str):
    """
    Search products for the chatbot to provide pricing info.
    Returns formatted product info suitable for LLM context.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        search_terms = query.lower().split()
        
        products = db.query(GRESTProduct).filter(
            GRESTProduct.in_stock == True
        ).all()
        
        matching_products = []
        for p in products:
            product_text = f"{p.name} {p.category} {p.variant or ''} {p.storage or ''} {p.color or ''}".lower()
            
            if any(term in product_text for term in search_terms):
                matching_products.append({
                    'name': p.name,
                    'category': p.category,
                    'storage': p.storage,
                    'color': p.color,
                    'condition': p.condition,
                    'price': float(p.price) if p.price else None,
                    'original_price': float(p.original_price) if p.original_price else None,
                    'discount_percent': p.discount_percent,
                    'warranty_months': p.warranty_months,
                    'product_url': p.product_url,
                    'image_url': p.image_url,
                    'in_stock': p.in_stock
                })
        
        return matching_products[:10]


def get_price_range_by_category(category: str):
    """
    Get price range for a product category (e.g., 'iPhone 14', 'MacBook').
    Returns min and max prices.
    """
    with get_db_session() as db:
        if db is None:
            return None
        
        from sqlalchemy import func
        
        result = db.query(
            func.min(GRESTProduct.price),
            func.max(GRESTProduct.price)
        ).filter(
            GRESTProduct.category.ilike(f"%{category}%"),
            GRESTProduct.in_stock == True
        ).first()
        
        if result and result[0] is not None:
            return {
                'category': category,
                'min_price': float(result[0]),
                'max_price': float(result[1])
            }
        return None


def get_products_under_price(max_price: float, category: str = None):
    """
    Get all products under a certain price.
    Optionally filter by category (iPhone, iPad, MacBook).
    Returns list sorted by price ascending.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        query = db.query(GRESTProduct).filter(
            GRESTProduct.price <= max_price,
            GRESTProduct.in_stock == True
        )
        
        if category:
            query = query.filter(GRESTProduct.category.ilike(f"%{category}%"))
        
        products = query.order_by(GRESTProduct.price.asc()).all()
        
        return [
            {
                'name': p.name,
                'price': float(p.price),
                'original_price': float(p.original_price) if p.original_price else None,
                'discount_percent': p.discount_percent,
                'category': p.category,
                'storage': p.storage,
                'condition': p.condition,
                'color': p.color,
                'product_url': p.product_url,
                'image_url': p.image_url,
                'specifications': p.specifications
            }
            for p in products
        ]


def get_products_in_price_range(min_price: float, max_price: float, category: str = None):
    """
    Get products within a price range.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        query = db.query(GRESTProduct).filter(
            GRESTProduct.price >= min_price,
            GRESTProduct.price <= max_price,
            GRESTProduct.in_stock == True
        )
        
        if category:
            query = query.filter(GRESTProduct.category.ilike(f"%{category}%"))
        
        products = query.order_by(GRESTProduct.price.asc()).all()
        
        return [
            {
                'name': p.name,
                'price': float(p.price),
                'original_price': float(p.original_price) if p.original_price else None,
                'discount_percent': p.discount_percent,
                'category': p.category,
                'storage': p.storage,
                'condition': p.condition,
                'color': p.color,
                'product_url': p.product_url,
                'image_url': p.image_url
            }
            for p in products
        ]


def get_cheapest_product(category: str = None):
    """
    Get the cheapest product, optionally filtered by category.
    """
    with get_db_session() as db:
        if db is None:
            return None
        
        query = db.query(GRESTProduct).filter(GRESTProduct.in_stock == True)
        
        if category:
            query = query.filter(GRESTProduct.category.ilike(f"%{category}%"))
        
        product = query.order_by(GRESTProduct.price.asc()).first()
        
        if product:
            return {
                'name': product.name,
                'price': float(product.price),
                'original_price': float(product.original_price) if product.original_price else None,
                'discount_percent': product.discount_percent,
                'category': product.category,
                'storage': product.storage,
                'condition': product.condition,
                'color': product.color,
                'product_url': product.product_url,
                'image_url': product.image_url,
                'specifications': product.specifications
            }
        return None


def get_all_products_formatted():
    """
    Get all products formatted for chatbot context.
    Returns a string suitable for LLM context injection.
    """
    with get_db_session() as db:
        if db is None:
            return "Product database not available."
        
        products = db.query(GRESTProduct).filter(
            GRESTProduct.in_stock == True
        ).order_by(GRESTProduct.price.asc()).all()
        
        if not products:
            return "No products available."
        
        lines = ["GREST PRODUCT CATALOG (Current Prices):"]
        lines.append("=" * 50)
        
        for p in products:
            discount_text = f" (Save {p.discount_percent}%)" if p.discount_percent else ""
            variant_info = ""
            if p.storage or p.condition:
                parts = []
                if p.storage:
                    parts.append(p.storage)
                if p.condition:
                    parts.append(p.condition)
                variant_info = f" ({', '.join(parts)})"
            lines.append(f"- {p.name}{variant_info}: Rs. {int(p.price):,}{discount_text}")
            lines.append(f"  URL: {p.product_url}")
        
        lines.append("=" * 50)
        lines.append(f"Total: {len(products)} products | Prices start from Rs. {int(products[0].price):,}")
        
        return "\n".join(lines)


def search_product_by_specs(model_name: str, storage: str = None, condition: str = None, include_out_of_stock: bool = False):
    """
    Search for a specific product variant by model name, storage, and condition.
    If condition is not specified, returns the cheapest in-stock variant.
    If specific condition is requested but out of stock, returns it with out_of_stock flag.
    
    Matching priority:
    1. Exact name match (e.g., "iPhone 12" matches "Apple iPhone 12" but NOT "Apple iPhone 12 mini")
    2. Contains match as fallback
    """
    with get_db_session() as db:
        if db is None:
            return None
        
        from sqlalchemy import func, case
        
        model_normalized = model_name.strip()
        
        model_lower = model_normalized.lower()
        
        all_suffixes = ['mini', 'pro max', 'pro', 'plus', 'ultra', 'se', 'new', 'max', 'air']
        
        exclude_suffixes = []
        for suffix in all_suffixes:
            if suffix not in model_lower:
                exclude_suffixes.append(suffix)
        
        if 'pro max' in model_lower:
            if 'pro' in exclude_suffixes:
                exclude_suffixes.remove('pro')
            if 'max' in exclude_suffixes:
                exclude_suffixes.remove('max')
        
        def build_base_query(in_stock_only=True):
            q = db.query(GRESTProduct).filter(
                GRESTProduct.name.ilike(f"%{model_normalized}%")
            )
            if in_stock_only:
                q = q.filter(GRESTProduct.in_stock == True)
            
            for suffix in exclude_suffixes:
                q = q.filter(~GRESTProduct.name.ilike(f"% {suffix}%"))
            
            if storage:
                storage_clean = storage.upper().replace(' ', '').replace('GB', ' GB').replace('TB', ' TB').strip()
                if 'GB' not in storage_clean and 'TB' not in storage_clean:
                    storage_clean = f"{storage} GB"
                q = q.filter(GRESTProduct.storage.ilike(f"%{storage_clean.strip()}%"))
            
            if condition:
                q = q.filter(GRESTProduct.condition.ilike(f"%{condition}%"))
            
            return q
        
        product = build_base_query(in_stock_only=True).order_by(GRESTProduct.price.asc()).first()
        out_of_stock = False
        
        if not product and condition:
            product = build_base_query(in_stock_only=False).order_by(GRESTProduct.price.asc()).first()
            if product:
                out_of_stock = True
        
        if product:
            return {
                'name': product.name,
                'storage': product.storage,
                'color': product.color,
                'condition': product.condition,
                'price': float(product.price),
                'original_price': float(product.original_price) if product.original_price else None,
                'discount_percent': product.discount_percent,
                'category': product.category,
                'product_url': product.product_url,
                'image_url': product.image_url,
                'variant': product.variant,
                'in_stock': not out_of_stock,
                'out_of_stock': out_of_stock
            }
        return None


def get_product_variants(model_name: str, storage: str = None):
    """
    Get all condition variants for a product model (optionally filtered by storage).
    Returns list sorted by condition (Fair, Good, Superb).
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        from sqlalchemy import func
        
        model_normalized = model_name.strip()
        model_lower = model_normalized.lower()
        
        all_suffixes = ['mini', 'pro max', 'pro', 'plus', 'ultra', 'se', 'new', 'max', 'air']
        
        exclude_suffixes = []
        for suffix in all_suffixes:
            if suffix not in model_lower:
                exclude_suffixes.append(suffix)
        
        if 'pro max' in model_lower:
            if 'pro' in exclude_suffixes:
                exclude_suffixes.remove('pro')
            if 'max' in exclude_suffixes:
                exclude_suffixes.remove('max')
        
        query = db.query(GRESTProduct).filter(
            GRESTProduct.name.ilike(f"%{model_normalized}%"),
            GRESTProduct.in_stock == True
        )
        
        for suffix in exclude_suffixes:
            query = query.filter(~GRESTProduct.name.ilike(f"% {suffix}%"))
        
        if storage:
            storage_clean = storage.upper().replace(' ', '').replace('GB', ' GB').replace('TB', ' TB').strip()
            if 'GB' not in storage_clean and 'TB' not in storage_clean:
                storage_clean = f"{storage} GB"
            query = query.filter(GRESTProduct.storage.ilike(f"%{storage_clean.strip()}%"))
        
        condition_order = {'Fair': 1, 'Good': 2, 'Superb': 3}
        products = query.all()
        
        result = {}
        for p in products:
            key = (p.storage, p.condition)
            if key not in result or p.price < result[key]['price']:
                result[key] = {
                    'name': p.name,
                    'storage': p.storage,
                    'color': p.color,
                    'condition': p.condition,
                    'price': float(p.price),
                    'original_price': float(p.original_price) if p.original_price else None,
                    'discount_percent': p.discount_percent,
                    'product_url': p.product_url,
                    'image_url': p.image_url
                }
        
        sorted_variants = sorted(
            result.values(),
            key=lambda x: (x['storage'] or '', condition_order.get(x['condition'], 99))
        )
        
        return sorted_variants


def get_storage_options_for_model(model_name: str):
    """
    Get all available storage options for a product model.
    Returns distinct storage values.
    """
    with get_db_session() as db:
        if db is None:
            return []
        
        from sqlalchemy import distinct
        
        model_normalized = model_name.strip()
        model_lower = model_normalized.lower()
        
        all_suffixes = ['mini', 'pro max', 'pro', 'plus', 'ultra', 'se', 'new', 'max', 'air']
        
        exclude_suffixes = []
        for suffix in all_suffixes:
            if suffix not in model_lower:
                exclude_suffixes.append(suffix)
        
        if 'pro max' in model_lower:
            if 'pro' in exclude_suffixes:
                exclude_suffixes.remove('pro')
            if 'max' in exclude_suffixes:
                exclude_suffixes.remove('max')
        
        query = db.query(distinct(GRESTProduct.storage)).filter(
            GRESTProduct.name.ilike(f"%{model_normalized}%"),
            GRESTProduct.in_stock == True,
            GRESTProduct.storage.isnot(None)
        )
        
        for suffix in exclude_suffixes:
            query = query.filter(~GRESTProduct.name.ilike(f"% {suffix}%"))
        
        storages = query.all()
        
        return [s[0] for s in storages if s[0]]
