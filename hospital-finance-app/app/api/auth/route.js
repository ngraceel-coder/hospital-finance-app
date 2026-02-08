import { NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';

export async function POST(request) {
  try {
    const { password } = await request.json();

    if (password === process.env.LOGIN_PASSWORD) {
      const token = jwt.sign(
        { authenticated: true, timestamp: Date.now() },
        process.env.JWT_SECRET,
        { expiresIn: '7d' }
      );

      return NextResponse.json({ success: true, token });
    }

    return NextResponse.json({ success: false, error: '비밀번호가 틀렸습니다.' }, { status: 401 });
  } catch (error) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function GET(request) {
  try {
    const authHeader = request.headers.get('authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    return NextResponse.json({ authenticated: true, decoded });
  } catch (error) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
}
