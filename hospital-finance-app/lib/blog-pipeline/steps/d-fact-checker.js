import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(draft, obsidianNote, latestSourcesSummary) {
  const latestSection = latestSourcesSummary
    ? `- 최신자료요약:\n${latestSourcesSummary}`
    : '';

  return `[역할] 너는 팩트체커이다.
[목표] 초안의 과학적 주장과 임상적 해석을 검증하고, 과장/비약을 제거한다.

[입력]
- 초안본문:
${draft}
- 논문요약노트:
${obsidianNote}
${latestSection}

[작업]
1) 초안에서 "사실 주장" 문장을 8~15개 뽑는다.
2) 각 주장에 대해 상태를 표시한다:
   - [논문근거있음]
   - [일반지식/임상상식]
   - [추정/해석]
   - [검증필요]
3) [추정/해석]은 표현을 완화한 대체 문장을 제안한다.
4) [검증필요]는 삭제 또는 "현재까지 알려진 범위에서는…" 같은 안전 문구로 전환한다.
5) 결과로 '수정된 본문'을 다시 출력한다.

[출력 형식]
A) 주장 점검표(간단히)
B) 수정된 본문(1500자 범위 유지)`;
}

export async function run(context) {
  const { draft, obsidianNote, latestSourcesSummary } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(draft, obsidianNote, latestSourcesSummary) },
    ],
    temperature: 0.3,
  });

  const result = response.choices[0].message.content;

  // 수정된 본문 부분 추출 시도 (B) 섹션 이후)
  const revisedMatch = result.match(/B\)\s*수정된 본문[\s\S]*?\n([\s\S]+)$/);
  const factCheckedDraft = revisedMatch ? revisedMatch[1].trim() : result;

  return { factCheckReport: result, draft: factCheckedDraft };
}
