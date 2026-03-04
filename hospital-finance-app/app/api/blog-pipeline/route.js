import { NextResponse } from 'next/server';
import { runPipeline, STEPS } from '@/lib/blog-pipeline';

export async function POST(request) {
  try {
    const body = await request.json();
    const { obsidianNote, startFrom, stopAfter, context } = body;

    if (!obsidianNote && !context?.obsidianNote) {
      return NextResponse.json(
        { error: 'obsidianNote가 필요합니다.' },
        { status: 400 }
      );
    }

    const result = await runPipeline({
      obsidianNote,
      startFrom,
      stopAfter,
      context,
    });

    return NextResponse.json({ success: true, result });
  } catch (error) {
    console.error('Blog pipeline error:', error);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    steps: STEPS.map((s) => s.name),
    usage: {
      method: 'POST',
      body: {
        obsidianNote: '(필수) 옵시디언 논문 요약 노트 텍스트',
        startFrom: '(선택) 시작 스텝: topicPlanner | questionGenerator | draftWriter | factChecker | policyReviewer | seoPackager',
        stopAfter: '(선택) 종료 스텝',
        context: '(선택) 이전 실행 결과를 이어받을 객체. selectedTopic 등 포함 가능',
      },
    },
  });
}
