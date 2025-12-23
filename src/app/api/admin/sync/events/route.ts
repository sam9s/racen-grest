import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const DASHBOARD_EMAIL = process.env.DASHBOARD_EMAIL || '';

async function isAuthorized(): Promise<boolean> {
  const cookieStore = await cookies();
  const adminToken = cookieStore.get('admin_token');
  if (adminToken?.value) {
    try {
      const decoded = Buffer.from(adminToken.value, 'base64').toString();
      const [email] = decoded.split(':');
      if (email.toLowerCase() === DASHBOARD_EMAIL.toLowerCase()) {
        return true;
      }
    } catch {
    }
  }
  return false;
}

export async function GET(request: NextRequest) {
  try {
    if (!await isAuthorized()) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';

    const response = await fetch(`${BACKEND_URL}/api/admin/sync/events?limit=${limit}`, {
      headers: {
        'X-Internal-Api-Key': process.env.INTERNAL_API_KEY || '',
      },
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to fetch sync events' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Sync Events] Error:', error);
    return NextResponse.json({ error: 'Failed to fetch sync events' }, { status: 500 });
  }
}
