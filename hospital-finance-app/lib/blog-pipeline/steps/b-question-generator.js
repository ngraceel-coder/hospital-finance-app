import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(topic, obsidianNote) {
  return `[역할] 너는 부모 상담 스크립트 작성자이다.
[목표] 선택된 주제에 대해 부모가 실제로 던질 질문을 생성해 글의 골격을 만든다.

[입력]
- 선택주제: ${topic}
- 논문요약노트:
${obsidianNote}

[작업]
1) 부모 질문을 8~12개 만든다.
2) 질문은 난이도 순으로 배열한다:
   - (초반) "지금 당장 불안한 질문"
   - (중반) "왜 그런지 이해하려는 질문"
   - (후반) "그래서 뭘 해야 하는지 질문"
3) 질문에는 비난/낙인/죄책감 유발 표현을 넣지 않는다.

[출력 형식]
- Q1~Q12 목록
- 마지막에 "이 질문 흐름으로 글을 구성하면 좋은 이유" 3줄`;
}

export async function run(context) {
  const { selectedTopic, obsidianNote } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(selectedTopic, obsidianNote) },
    ],
    temperature: 0.7,
  });

  const result = response.choices[0].message.content;
  return { parentQuestions: result };
}
