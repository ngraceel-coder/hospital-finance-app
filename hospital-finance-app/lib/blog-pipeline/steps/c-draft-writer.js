import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(topic, parentQuestions, obsidianNote) {
  return `[역할] 너는 소아청소년과 의사 블로거이다.
[목표] 부모가 이해할 수 있는 1500자 내외 네이버 블로그 글 초안을 쓴다.

[입력]
- 선택주제: ${topic}
- 부모질문목록:
${parentQuestions}
- 논문요약노트:
${obsidianNote}

[글 구조(반드시 이 순서)]
1) 문제 제기: 부모가 '검색하게 된 장면'을 짧은 스토리로 시작한다.
2) 부모 공감: "그럴 수 있다"를 과학/현실 기반으로 공감한다(감정 과잉 금지).
3) 과학 설명: 논문에서 핵심 개념을 2~3개로 정리해 설명한다.
   - 의학용어는 최소화
   - 꼭 필요한 용어가 나오면 즉시 쉬운 말로 번역
   - 논문 한계(일반화 주의) 1문장 포함
4) 실제 양육 팁: 오늘부터 할 수 있는 행동 가이드 3~5개(구체적 행동 중심).
5) 정리: 현실 적용 메시지 3가지(교훈/안심/실행방법)로 마무리한다.

[금지/주의]
- "반드시/무조건/100%" 같은 단정 금지
- 치료효과를 확정적으로 표현 금지
- 특정 제품/시술 홍보처럼 보이게 금지
- 공포 조장 금지

[출력]
- 제목 없이 본문만 작성(약 1500자 ±15%)`;
}

export async function run(context) {
  const { selectedTopic, parentQuestions, obsidianNote } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(selectedTopic, parentQuestions, obsidianNote) },
    ],
    temperature: 0.7,
  });

  const result = response.choices[0].message.content;
  return { draft: result };
}
