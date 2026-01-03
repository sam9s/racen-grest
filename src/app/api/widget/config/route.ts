import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const CACHE_HEADERS = {
  'Cache-Control': 'no-cache, no-store, must-revalidate',
  'Pragma': 'no-cache',
  'Expires': '0',
};

export async function GET() {
  try {
    const response = await fetch(`http://localhost:8080/api/widget/config`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      return NextResponse.json(
        { enabled: true, error: 'Config fetch failed, defaulting to enabled' },
        { headers: CACHE_HEADERS }
      );
    }

    const data = await response.json();
    return NextResponse.json(data, { headers: CACHE_HEADERS });
  } catch (error) {
    console.error('Widget config error:', error);
    return NextResponse.json(
      { enabled: true, error: 'Config unavailable, defaulting to enabled' },
      { headers: CACHE_HEADERS }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const adminToken = cookieStore.get('admin_token');
    
    if (!adminToken?.value) {
      return NextResponse.json(
        { error: 'Unauthorized. Admin login required.' },
        { status: 401 }
      );
    }

    let tokenData;
    try {
      const decoded = Buffer.from(adminToken.value, 'base64').toString();
      const [email] = decoded.split(':');
      tokenData = { email };
    } catch {
      return NextResponse.json(
        { error: 'Invalid session' },
        { status: 401 }
      );
    }

    if (!tokenData.email) {
      return NextResponse.json(
        { error: 'Unauthorized. Please login to the dashboard.' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const enabled = body.enabled;

    if (typeof enabled !== 'boolean') {
      return NextResponse.json(
        { error: 'Invalid request. Expected { enabled: boolean }' },
        { status: 400 }
      );
    }

    const widgetToken = process.env.WIDGET_ADMIN_TOKEN;
    if (!widgetToken) {
      return NextResponse.json(
        { error: 'Widget admin token not configured on server.' },
        { status: 503 }
      );
    }

    const response = await fetch(`http://localhost:8080/api/widget/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': widgetToken,
      },
      body: JSON.stringify({ enabled }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      return NextResponse.json(
        { error: errorData.error || 'Failed to update widget config' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Widget config POST error:', error);
    return NextResponse.json(
      { error: 'Failed to update widget configuration' },
      { status: 500 }
    );
  }
}
