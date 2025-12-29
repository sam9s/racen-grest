import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

async function isAdminAuthenticated(): Promise<boolean> {
  const cookieStore = await cookies();
  const adminSession = cookieStore.get('admin_session');
  if (!adminSession) return false;
  
  try {
    const session = JSON.parse(adminSession.value);
    const allowedEmails = (process.env.DASHBOARD_EMAIL || '').split(',').map(e => e.trim().toLowerCase());
    return allowedEmails.includes(session.email?.toLowerCase());
  } catch {
    return false;
  }
}

export async function GET() {
  if (!await isAdminAuthenticated()) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/security`, {
      headers: {
        'X-Internal-Api-Key': process.env.INTERNAL_API_KEY || '',
      },
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to fetch security data' }, { status: 500 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch security data:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
