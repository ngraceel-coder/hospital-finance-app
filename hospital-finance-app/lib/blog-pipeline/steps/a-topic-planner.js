import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(obsidianNote) {
  return `[역할] 너는 네이버 블로그 글감 기획자이다.
[목표] 아래 입력(논문 요약 노트)에서 부모가 검색할 법한 주제를 노출 친화적으로 재구성한다.

[입력]
- 논문요약노트:
${obsidianNote}

[작업]
1) 논문에서 부모 관심사로 변환 가능한 핵심 개념을 3~7개 추출한다.
2) 각 개념을 '부모 검색 문장'으로 바꾼다. (예: "아이가 자꾸 소리 지르는 이유", "감각 예민한 아이 수면")
3) 네이버 블로그에 적합한 주제 후보를 5개 만든다.
4) 각 후보에 대해:
   - 예상 독자 불안 포인트(한 문장)
   - 글에서 제공할 약속(한 문장: "이 글을 읽고 얻는 것")
   - 위험 표현 체크(과장/단정/치료효과 주장 가능성) 한 줄 경고
를 붙인다.

[출력 형식]
- 후보 1~5를 번호로 제시한다.
- 마지막에 "이번 글로 가장 적합한 1개"를 추천하고 이유를 2줄로 설명한다.`;
}

export async function run(context) {
  const { obsidianNote } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(obsidianNote) },
    ],
    temperature: 0.7,
  });

  const result = response.choices[0].message.content;
  return { topicCandidates: result };
}
