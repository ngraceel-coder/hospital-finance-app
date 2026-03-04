import getOpenAI from '@/lib/openai';
import SYSTEM_PROMPT from '../system-prompt';

function buildPrompt(finalDraft, keywords) {
  const keywordsSection = keywords
    ? `- 핵심키워드: ${keywords}`
    : '- 핵심키워드: (본문에서 추출)';

  return `[역할] 너는 네이버 블로그 SEO 카피라이터이다.
[목표] 본문과 일치하는 노출 친화적인 제목과 해시태그를 만든다.

[입력]
- 최종본문:
${finalDraft}
${keywordsSection}

[작업]
1) 제목 5개 생성:
   - (A) 정보형
   - (B) 질문형(부모 검색 문장형)
   - (C) 공감형(불안 완화형)
   - (D) 가이드형("~하는 법")
   - (E) 스토리형(짧은 장면 제시)
2) 제목은 과장 금지, 본문 내용과 1:1로 맞아야 한다.
3) 해시태그 15개:
   - 너무 의료 전문으로만 가지 말고(부모용)
   - 너무 일반 육아로만 흐리지 말기(브랜딩)
   - 중복 최소화

[출력 형식]
- 제목 후보 1~5
- 해시태그 15개(한 줄로)`;
}

export async function run(context) {
  const { draft, keywords } = context;

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: buildPrompt(draft, keywords) },
    ],
    temperature: 0.7,
  });

  const result = response.choices[0].message.content;
  return { seoPackage: result };
}
