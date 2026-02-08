import { NextResponse } from 'next/server';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get('image');

    if (!file) {
      return NextResponse.json({ error: '이미지가 없습니다.' }, { status: 400 });
    }

    // 이미지를 base64로 변환
    const bytes = await file.arrayBuffer();
    const base64 = Buffer.from(bytes).toString('base64');

    // 파일 타입 확인
    const mimeType = file.type || 'image/png';

    // OpenAI API 호출 (GPT-4o-mini - 가장 저렴)
    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 2000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image_url',
              image_url: {
                url: `data:${mimeType};base64,${base64}`,
              },
            },
            {
              type: 'text',
              text: `이 은행 거래내역 이미지를 분석해서 JSON 형식으로 추출해주세요.

각 거래마다 다음 정보를 추출하세요:
- date: 날짜 (YYYY-MM-DD 형식)
- time: 시간 (HH:MM:SS 형식)
- type: "입금" 또는 "출금"
- amount: 금액 (숫자만, 콤마 없이)
- description: 거래처/상대방 이름
- memo: 메모가 있으면 포함
- balance: 잔액 (숫자만)
- category: 아래 분류 규칙에 따라 자동 분류

분류 규칙:
- 노지혜, 온소아청소년: "내부이체"
- 더편한샵, 지엔팜, 보령바이오파마, 동아에스티, 블루팜코리아, 홍익무역, 블루엠텍, 크레스콤, 레노메디, 해아람, 다한다: "의약품/의료용품"
- 녹십자의료재단: "검사비"
- 급여, 프리랜서, 김진, 김다정, 김다혜, 김재영, 박지은, 이지현, 하미선, 노슬기: "인건비"
- 국민연금, 건강보험, 고용보험, 산재보험, 4대보험: "4대보험"
- 월세, 임대, 관리비, 기숙사: "임대료" (직원 기숙사 포함)
- 국세, 지방세, 세무, 부가세, 원천세: "세금"
- 이자, 대출, 상환, 경남은행, 우리은행, 기업은행, 롯데캐피탈: "대출이자"
- 기부, 모금: "기부금"
- 식대, 배달, 음식점, 식당: "식비"
- 광고, 마케팅: "광고비"
- 청소: "관리비/청소"
- 카드, VAN, 이지스, NICE, KB국민, 신한, 삼성, 현대, 롯데, BC, 하나, NH농협: "카드매출"
- 국민건강, 건강보험, 심평원: "심평원"
- 그 외 입금: "기타수입"
- 그 외 출금: "기타운영비"

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "transactions": [
    {
      "date": "2026-01-22",
      "time": "18:34:47",
      "type": "입금",
      "amount": 6000000,
      "description": "노지혜(온소아청소년)",
      "memo": "",
      "balance": 6223748,
      "category": "내부이체"
    }
  ],
  "bank": "KB스타뱅킹"
}`,
            },
          ],
        },
      ],
    });

    // OpenAI 응답에서 JSON 추출
    const content = response.choices[0].message.content;

    // JSON 파싱 시도
    let result;
    try {
      // JSON 부분만 추출 (```json ... ``` 형식일 수도 있음)
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        result = JSON.parse(jsonMatch[0]);
      } else {
        result = JSON.parse(content);
      }
    } catch (parseError) {
      console.error('JSON 파싱 오류:', parseError);
      return NextResponse.json({
        error: 'JSON 파싱 실패',
        rawContent: content,
      }, { status: 500 });
    }

    return NextResponse.json(result);

  } catch (error) {
    console.error('OCR 오류:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
