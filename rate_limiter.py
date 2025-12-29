"""
=============================================================================
RACEN Rate Limiter - Security Module for Conversational AI Chatbots
=============================================================================

Part of: RACEN (Rapid Automation Client Engagement Network)
         A product line under Raven Solutions Business Process Automation

Applicable Bots: Jovee, SOMERA, GRESTA, Naira, and all future RACEN chatbots

-----------------------------------------------------------------------------
PROTECTS AGAINST:
- DDoS attacks (flooding the API)
- API cost abuse (draining OpenAI/LLM credits)
- Automated scripts and bots

FEATURES:
- IP-based rate limiting (configurable thresholds)
- Session-based message counting
- IP logging for monitoring and forensics
- Simple math CAPTCHA challenge (widget-compatible, no page refresh)
- PostgreSQL persistence (survives server restarts)

DEFAULT THRESHOLDS:
- 10 requests per minute (soft limit)
- 50 requests per hour (triggers 10-min block)
- 100 requests per day (triggers 24-hour block)
- CAPTCHA after 20 messages in session
- 200 messages per session per day

-----------------------------------------------------------------------------
STORAGE: PostgreSQL (persistent across restarts)
Tables: rate_limit_requests, rate_limit_blocks, rate_limit_captchas, rate_limit_captcha_verified

CREATED: December 27, 2024
UPDATED: December 29, 2024 - Added PostgreSQL persistence
DOCUMENTATION: See docs/RACEN_SECURITY_ACTION_PLAN.md
=============================================================================
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
import random
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rate_limiter")


def get_db_connection():
    """Get a PostgreSQL database connection."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not set")
        return None
    try:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 10,
        requests_per_hour: int = 50,
        requests_per_day: int = 100,
        captcha_threshold: int = 20,
        block_duration_minutes: int = 10,
        session_daily_limit: int = 200
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.captcha_threshold = captcha_threshold
        self.block_duration = timedelta(minutes=block_duration_minutes)
        self.session_daily_limit = session_daily_limit
    
    def _count_requests_in_window(self, ip: str, seconds: int) -> int:
        """Count requests from IP in the given time window."""
        conn = get_db_connection()
        if not conn:
            return 0
        try:
            with conn.cursor() as cur:
                cutoff = datetime.utcnow() - timedelta(seconds=seconds)
                cur.execute(
                    "SELECT COUNT(*) as count FROM rate_limit_requests WHERE ip_address = %s AND created_at > %s",
                    (ip, cutoff)
                )
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error counting requests: {e}")
            return 0
        finally:
            conn.close()
    
    def _count_session_messages_in_day(self, session_id: str) -> int:
        """Count session messages in the last 24 hours."""
        conn = get_db_connection()
        if not conn:
            return 0
        try:
            with conn.cursor() as cur:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                cur.execute(
                    "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                    (session_id, cutoff)
                )
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error counting session messages: {e}")
            return 0
        finally:
            conn.close()
    
    def _count_messages_since_captcha(self, session_id: str) -> int:
        """Count messages since last CAPTCHA verification."""
        conn = get_db_connection()
        if not conn:
            return 0
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT verified_at FROM rate_limit_captcha_verified WHERE session_id = %s",
                    (session_id,)
                )
                verified_result = cur.fetchone()
                
                if verified_result:
                    verified_at = verified_result['verified_at']
                    cur.execute(
                        "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                        (session_id, verified_at)
                    )
                else:
                    cutoff = datetime.utcnow() - timedelta(hours=24)
                    cur.execute(
                        "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                        (session_id, cutoff)
                    )
                
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error counting messages since captcha: {e}")
            return 0
        finally:
            conn.close()
    
    def _is_ip_blocked(self, ip: str) -> Tuple[bool, Optional[datetime]]:
        """Check if IP is currently blocked."""
        conn = get_db_connection()
        if not conn:
            return False, None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT blocked_until FROM rate_limit_blocks WHERE ip_address = %s",
                    (ip,)
                )
                result = cur.fetchone()
                if result and result['blocked_until'] > datetime.utcnow():
                    return True, result['blocked_until']
                elif result:
                    cur.execute("DELETE FROM rate_limit_blocks WHERE ip_address = %s", (ip,))
                    conn.commit()
                return False, None
        except Exception as e:
            logger.error(f"Error checking blocked IP: {e}")
            return False, None
        finally:
            conn.close()
    
    def _block_ip(self, ip: str, until: datetime, reason: str):
        """Block an IP address until a specific time."""
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO rate_limit_blocks (ip_address, blocked_until, reason) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s, reason = %s""",
                    (ip, until, reason, until, reason)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error blocking IP: {e}")
        finally:
            conn.close()
    
    def _get_pending_captcha(self, session_id: str) -> Optional[dict]:
        """Get pending CAPTCHA for a session."""
        conn = get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT question, answer FROM rate_limit_captchas WHERE session_id = %s",
                    (session_id,)
                )
                result = cur.fetchone()
                if result:
                    return {"type": "math", "question": result['question'], "answer": result['answer']}
                return None
        except Exception as e:
            logger.error(f"Error getting pending captcha: {e}")
            return None
        finally:
            conn.close()
    
    def _save_captcha(self, session_id: str, question: str, answer: str):
        """Save a CAPTCHA challenge."""
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO rate_limit_captchas (session_id, question, answer) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (session_id) DO UPDATE SET question = %s, answer = %s, created_at = CURRENT_TIMESTAMP""",
                    (session_id, question, answer, question, answer)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving captcha: {e}")
        finally:
            conn.close()
    
    def log_request(self, ip: str, session_id: str, endpoint: str, message_preview: str = ""):
        """Log a request for monitoring and forensics."""
        conn = get_db_connection()
        if not conn:
            logger.info(f"[Request] IP={ip}, Session={session_id[:16] if session_id else 'N/A'}..., Endpoint={endpoint}")
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO rate_limit_requests (ip_address, session_id, endpoint, message_preview) 
                       VALUES (%s, %s, %s, %s)""",
                    (ip, session_id, endpoint, message_preview[:100] if message_preview else "")
                )
                conn.commit()
            logger.info(f"[Request] IP={ip}, Session={session_id[:16] if session_id else 'N/A'}..., Endpoint={endpoint}")
        except Exception as e:
            logger.error(f"Error logging request: {e}")
        finally:
            conn.close()
    
    def check_rate_limit(self, ip: str, session_id: str = None) -> Tuple[bool, str, Optional[dict]]:
        """
        Check if the request should be allowed.
        Uses a single database connection for all checks.
        
        Returns:
            Tuple of (allowed, reason, captcha_challenge)
            - allowed: True if request is allowed
            - reason: Human-readable reason if blocked
            - captcha_challenge: If not None, user must solve this first
        """
        conn = get_db_connection()
        if not conn:
            return True, "", None
        
        try:
            with conn.cursor() as cur:
                now = datetime.utcnow()
                
                cur.execute(
                    "SELECT blocked_until FROM rate_limit_blocks WHERE ip_address = %s",
                    (ip,)
                )
                block_result = cur.fetchone()
                if block_result and block_result['blocked_until'] > now:
                    remaining = (block_result['blocked_until'] - now).seconds // 60
                    logger.warning(f"[Blocked] IP={ip} blocked for {remaining} more minutes")
                    return False, f"Too many requests. Please try again in {remaining} minutes.", None
                elif block_result:
                    cur.execute("DELETE FROM rate_limit_blocks WHERE ip_address = %s", (ip,))
                    conn.commit()
                
                minute_ago = now - timedelta(seconds=60)
                hour_ago = now - timedelta(hours=1)
                day_ago = now - timedelta(hours=24)
                
                cur.execute(
                    """SELECT 
                        COUNT(*) FILTER (WHERE created_at > %s) as minute_count,
                        COUNT(*) FILTER (WHERE created_at > %s) as hour_count,
                        COUNT(*) as day_count
                       FROM rate_limit_requests 
                       WHERE ip_address = %s AND created_at > %s""",
                    (minute_ago, hour_ago, ip, day_ago)
                )
                ip_counts = cur.fetchone()
                minute_count = ip_counts['minute_count'] if ip_counts else 0
                hour_count = ip_counts['hour_count'] if ip_counts else 0
                day_count = ip_counts['day_count'] if ip_counts else 0
                
                if minute_count >= self.requests_per_minute:
                    logger.warning(f"[Rate Limit] IP={ip} exceeded {self.requests_per_minute}/min limit")
                    return False, "Too many requests. Please wait a minute before trying again.", None
                
                if hour_count >= self.requests_per_hour:
                    block_until = now + self.block_duration
                    cur.execute(
                        """INSERT INTO rate_limit_blocks (ip_address, blocked_until, reason) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s, reason = %s""",
                        (ip, block_until, f"Exceeded {self.requests_per_hour}/hour limit", block_until, f"Exceeded {self.requests_per_hour}/hour limit")
                    )
                    conn.commit()
                    logger.warning(f"[Rate Limit] IP={ip} exceeded {self.requests_per_hour}/hour limit, blocked for {self.block_duration}")
                    return False, f"Rate limit exceeded. Please try again in {self.block_duration.seconds // 60} minutes.", None
                
                if day_count >= self.requests_per_day:
                    block_until = now + timedelta(hours=24)
                    cur.execute(
                        """INSERT INTO rate_limit_blocks (ip_address, blocked_until, reason) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s, reason = %s""",
                        (ip, block_until, f"Exceeded {self.requests_per_day}/day limit", block_until, f"Exceeded {self.requests_per_day}/day limit")
                    )
                    conn.commit()
                    logger.warning(f"[Rate Limit] IP={ip} exceeded {self.requests_per_day}/day limit, blocked for 24 hours")
                    return False, "Daily limit reached. Please try again tomorrow.", None
                
                if session_id:
                    cur.execute(
                        "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                        (session_id, day_ago)
                    )
                    session_result = cur.fetchone()
                    session_count = session_result['count'] if session_result else 0
                    
                    if session_count >= self.session_daily_limit:
                        logger.warning(f"[Session Limit] Session={session_id[:16]}... exceeded {self.session_daily_limit} messages in 24h")
                        return False, "You've had a great conversation today! For more help, please contact support@grest.in or visit grest.in", None
                    
                    cur.execute(
                        "SELECT verified_at FROM rate_limit_captcha_verified WHERE session_id = %s",
                        (session_id,)
                    )
                    verified_result = cur.fetchone()
                    
                    if verified_result:
                        cur.execute(
                            "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                            (session_id, verified_result['verified_at'])
                        )
                    else:
                        cur.execute(
                            "SELECT COUNT(*) as count FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
                            (session_id, day_ago)
                        )
                    
                    captcha_result = cur.fetchone()
                    messages_since_captcha = captcha_result['count'] if captcha_result else 0
                    
                    if messages_since_captcha >= self.captcha_threshold:
                        cur.execute(
                            "SELECT question FROM rate_limit_captchas WHERE session_id = %s",
                            (session_id,)
                        )
                        pending = cur.fetchone()
                        if pending:
                            return False, "Please solve the verification challenge to continue.", {"type": "math", "question": pending['question']}
                        else:
                            a = random.randint(1, 10)
                            b = random.randint(1, 10)
                            answer = a + b
                            question = f"What is {a} + {b}?"
                            cur.execute(
                                """INSERT INTO rate_limit_captchas (session_id, question, answer) 
                                   VALUES (%s, %s, %s) 
                                   ON CONFLICT (session_id) DO UPDATE SET question = %s, answer = %s, created_at = CURRENT_TIMESTAMP""",
                                (session_id, question, str(answer), question, str(answer))
                            )
                            conn.commit()
                            logger.info(f"[CAPTCHA] Triggered for session={session_id[:16]}... (count={messages_since_captcha})")
                            return False, "Please verify you're human to continue.", {"type": "math", "question": question}
                
                return True, "", None
        except Exception as e:
            logger.error(f"Error in check_rate_limit: {e}")
            return True, "", None
        finally:
            conn.close()
    
    def record_request(self, ip: str, session_id: str = None):
        """Record a successful request (already done in log_request for DB version)."""
        pass
    
    def _generate_captcha(self, session_id: str) -> dict:
        """Generate a simple math CAPTCHA."""
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        answer = a + b
        question = f"What is {a} + {b}?"
        
        self._save_captcha(session_id, question, str(answer))
        return {"type": "math", "question": question}
    
    def verify_captcha(self, session_id: str, user_answer: str) -> bool:
        """Verify a CAPTCHA answer. Resets CAPTCHA counter but preserves daily limit."""
        pending = self._get_pending_captcha(session_id)
        if not pending:
            return True
        
        expected = pending['answer']
        if user_answer.strip() == expected:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM rate_limit_captchas WHERE session_id = %s", (session_id,))
                        cur.execute(
                            """INSERT INTO rate_limit_captcha_verified (session_id, verified_at) 
                               VALUES (%s, CURRENT_TIMESTAMP) 
                               ON CONFLICT (session_id) DO UPDATE SET verified_at = CURRENT_TIMESTAMP""",
                            (session_id,)
                        )
                        conn.commit()
                except Exception as e:
                    logger.error(f"Error verifying captcha: {e}")
                finally:
                    conn.close()
            logger.info(f"[CAPTCHA] Verified for session={session_id[:16]}...")
            return True
        
        logger.warning(f"[CAPTCHA] Failed for session={session_id[:16]}...")
        return False
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics for monitoring."""
        conn = get_db_connection()
        if not conn:
            return {
                "active_ips": 0,
                "blocked_ips": 0,
                "pending_captchas": 0,
                "total_logged_requests": 0,
                "blocked_ip_list": [],
                "config": {
                    "requests_per_minute": self.requests_per_minute,
                    "requests_per_hour": self.requests_per_hour,
                    "requests_per_day": self.requests_per_day,
                    "captcha_threshold": self.captcha_threshold,
                    "session_daily_limit": self.session_daily_limit
                }
            }
        
        try:
            with conn.cursor() as cur:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                
                cur.execute(
                    "SELECT COUNT(DISTINCT ip_address) as count FROM rate_limit_requests WHERE created_at > %s",
                    (cutoff,)
                )
                active_ips = cur.fetchone()['count']
                
                cur.execute(
                    "SELECT COUNT(*) as count FROM rate_limit_blocks WHERE blocked_until > %s",
                    (datetime.utcnow(),)
                )
                blocked_ips = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM rate_limit_captchas")
                pending_captchas = cur.fetchone()['count']
                
                cur.execute(
                    "SELECT COUNT(*) as count FROM rate_limit_requests WHERE created_at > %s",
                    (cutoff,)
                )
                total_logged = cur.fetchone()['count']
                
                cur.execute(
                    "SELECT ip_address FROM rate_limit_blocks WHERE blocked_until > %s LIMIT 10",
                    (datetime.utcnow(),)
                )
                blocked_list = [row['ip_address'] for row in cur.fetchall()]
                
                return {
                    "active_ips": active_ips,
                    "blocked_ips": blocked_ips,
                    "pending_captchas": pending_captchas,
                    "total_logged_requests": total_logged,
                    "blocked_ip_list": blocked_list,
                    "config": {
                        "requests_per_minute": self.requests_per_minute,
                        "requests_per_hour": self.requests_per_hour,
                        "requests_per_day": self.requests_per_day,
                        "captcha_threshold": self.captcha_threshold,
                        "session_daily_limit": self.session_daily_limit
                    }
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "active_ips": 0,
                "blocked_ips": 0,
                "pending_captchas": 0,
                "total_logged_requests": 0,
                "blocked_ip_list": [],
                "config": {
                    "requests_per_minute": self.requests_per_minute,
                    "requests_per_hour": self.requests_per_hour,
                    "requests_per_day": self.requests_per_day,
                    "captcha_threshold": self.captcha_threshold,
                    "session_daily_limit": self.session_daily_limit
                }
            }
        finally:
            conn.close()
    
    def get_ip_activity(self, ip: str) -> dict:
        """Get activity for a specific IP."""
        is_blocked, _ = self._is_ip_blocked(ip)
        return {
            "ip": ip,
            "requests_last_minute": self._count_requests_in_window(ip, 60),
            "requests_last_hour": self._count_requests_in_window(ip, 3600),
            "requests_last_day": self._count_requests_in_window(ip, 86400),
            "is_blocked": is_blocked
        }
    
    def get_recent_requests(self, limit: int = 20) -> list:
        """Get recent request logs."""
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT ip_address, session_id, endpoint, message_preview, created_at 
                       FROM rate_limit_requests 
                       ORDER BY created_at DESC 
                       LIMIT %s""",
                    (limit,)
                )
                results = cur.fetchall()
                return [
                    {
                        "ip": row['ip_address'],
                        "session_id": row['session_id'],
                        "endpoint": row['endpoint'],
                        "message_preview": row['message_preview'],
                        "timestamp": row['created_at'].isoformat() if row['created_at'] else None
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Error getting recent requests: {e}")
            return []
        finally:
            conn.close()
    
    def get_top_ips(self, limit: int = 10) -> list:
        """Get top active IPs in the last 24 hours - optimized single query."""
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                now = datetime.utcnow()
                minute_ago = now - timedelta(seconds=60)
                hour_ago = now - timedelta(hours=1)
                day_ago = now - timedelta(hours=24)
                
                cur.execute(
                    """SELECT 
                        r.ip_address,
                        COUNT(*) as total_requests,
                        COUNT(*) FILTER (WHERE r.created_at > %s) as requests_minute,
                        COUNT(*) FILTER (WHERE r.created_at > %s) as requests_hour,
                        CASE WHEN b.ip_address IS NOT NULL AND b.blocked_until > %s THEN true ELSE false END as is_blocked
                       FROM rate_limit_requests r
                       LEFT JOIN rate_limit_blocks b ON r.ip_address = b.ip_address
                       WHERE r.created_at > %s 
                       GROUP BY r.ip_address, b.ip_address, b.blocked_until
                       ORDER BY total_requests DESC 
                       LIMIT %s""",
                    (minute_ago, hour_ago, now, day_ago, limit)
                )
                results = cur.fetchall()
                
                return [
                    {
                        "ip": row['ip_address'],
                        "requestsLastMinute": row['requests_minute'],
                        "requestsLastHour": row['requests_hour'],
                        "requestsLastDay": row['total_requests'],
                        "isBlocked": row['is_blocked']
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Error getting top IPs: {e}")
            return []
        finally:
            conn.close()
    
    def get_blocked_ips_details(self) -> list:
        """Get details of currently blocked IPs."""
        conn = get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT ip_address, blocked_until, reason 
                       FROM rate_limit_blocks 
                       WHERE blocked_until > %s""",
                    (datetime.utcnow(),)
                )
                results = cur.fetchall()
                return [
                    {
                        "ip": row['ip_address'],
                        "blockedUntil": row['blocked_until'].isoformat() if row['blocked_until'] else None,
                        "remainingMinutes": round((row['blocked_until'] - datetime.utcnow()).total_seconds() / 60, 1) if row['blocked_until'] else 0,
                        "reason": row['reason']
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Error getting blocked IPs: {e}")
            return []
        finally:
            conn.close()
    
    def reset_session(self, session_id: str):
        """Reset session data."""
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rate_limit_captchas WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM rate_limit_captcha_verified WHERE session_id = %s", (session_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting session: {e}")
        finally:
            conn.close()
    
    def cleanup_old_data(self):
        """Clean up data older than 24 hours."""
        conn = get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                cur.execute("DELETE FROM rate_limit_requests WHERE created_at < %s", (cutoff,))
                cur.execute("DELETE FROM rate_limit_blocks WHERE blocked_until < %s", (datetime.utcnow(),))
                conn.commit()
                logger.info("[Cleanup] Old rate limit data cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
        finally:
            conn.close()


rate_limiter = RateLimiter(
    requests_per_minute=10,
    requests_per_hour=50,
    requests_per_day=100,
    captcha_threshold=20,
    block_duration_minutes=10,
    session_daily_limit=200
)


def get_client_ip(request) -> str:
    """Extract client IP from Flask request, handling proxies."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or "unknown"
