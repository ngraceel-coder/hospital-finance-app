import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(finalDraft) {
  return `[역할] 너는 네이버 블로그 정책/품질 점검자이다.
[목표] 글이 과장·의학적 단정·공포 조장·상업적 홍보처럼 보이는 위험을 줄인다.

[입력]
- 본문:
${finalDraft}

[체크리스트]
- 단정/확정 표현(무조건/반드시/완치/확실) 존재 여부
- 공포 조장/극단 사례로 압박하는 문장 존재 여부
- 특정 치료/기기/제품으로 유도하는 뉘앙스 존재 여부
- 의료 조언이 개인 진료처럼 보이는 문장 존재 여부
- 과학 설명이 "권위로 찍어누르는" 말투인지 여부
- 부모 죄책감 유발 문장 존재 여부
- 제목/해시태그와 본문 주제가 불일치하는지 여부

[출력]
1) 위험 항목이 있으면 "문장 그대로 인용 + 왜 위험한지 + 대체 문장"으로 제시
2) 수정 반영한 최종 본문 출력`;
}

export async function run(context) {
  const { draft } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(draft) },
    ],
    temperature: 0.3,
  });

  const result = response.choices[0].message.content;

  // 최종 본문 추출 시도 (2) 섹션 이후)
  const finalMatch = result.match(/2\)\s*수정 반영한 최종 본문[\s\S]*?\n([\s\S]+)$/);
  const reviewedDraft = finalMatch ? finalMatch[1].trim() : result;

  return { policyReport: result, draft: reviewedDraft };
}
