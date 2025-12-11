import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const ADMIN_EMAILS = (process.env.ADMIN_EMAILS || '').split(',').map(e => e.trim().toLowerCase());

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    
    const userEmail = session.user.email.toLowerCase();
    if (ADMIN_EMAILS.length > 0 && ADMIN_EMAILS[0] !== '' && !ADMIN_EMAILS.includes(userEmail)) {
      return NextResponse.json({ error: 'Forbidden - Admin access required' }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const range = searchParams.get('range') || '7d';
    const page = searchParams.get('page') || '1';
    const limit = searchParams.get('limit') || '50';

    const response = await fetch(
      `${BACKEND_URL}/api/admin/conversations?range=${range}&page=${page}&limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Internal-Api-Key': process.env.INTERNAL_API_KEY || '',
        },
      }
    );

    if (!response.ok) {
      console.error(`[Admin Conversations] Backend returned status ${response.status}`);
      return NextResponse.json({ error: 'Backend error' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Admin Conversations] Error:', error);
    return NextResponse.json({ error: 'Failed to fetch conversations' }, { status: 500 });
  }
}
