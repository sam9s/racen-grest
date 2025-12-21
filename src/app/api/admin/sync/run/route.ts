import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const ADMIN_EMAILS = (process.env.ADMIN_EMAILS || '').split(',').map(e => e.trim().toLowerCase());
const DASHBOARD_EMAIL = process.env.DASHBOARD_EMAIL || '';

async function isAuthorized(): Promise<{ authorized: boolean; email: string | null }> {
  const googleSession = await getServerSession(authOptions);
  if (googleSession?.user?.email) {
    const userEmail = googleSession.user.email.toLowerCase();
    if (ADMIN_EMAILS.includes(userEmail)) {
      return { authorized: true, email: userEmail };
    }
  }
  
  const cookieStore = await cookies();
  const adminToken = cookieStore.get('admin_token');
  if (adminToken?.value) {
    try {
      const decoded = Buffer.from(adminToken.value, 'base64').toString();
      const [email] = decoded.split(':');
      if (email.toLowerCase() === DASHBOARD_EMAIL.toLowerCase()) {
        return { authorized: true, email: email.toLowerCase() };
      }
    } catch {
    }
  }
  
  return { authorized: false, email: null };
}

export async function POST(request: NextRequest) {
  try {
    const { authorized, email } = await isAuthorized();
    if (!authorized) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json().catch(() => ({}));

    const response = await fetch(`${BACKEND_URL}/api/admin/sync/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Api-Key': process.env.INTERNAL_API_KEY || '',
      },
      body: JSON.stringify({
        triggeredBy: email || body.triggeredBy || 'admin',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(errorData, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Sync Run] Error:', error);
    return NextResponse.json({ error: 'Failed to trigger sync' }, { status: 500 });
  }
}
