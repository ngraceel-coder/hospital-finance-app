#!/usr/bin/env node

/**
 * 블로그 파이프라인 CLI 실행 스크립트
 *
 * 사용법:
 *   node scripts/run-pipeline.mjs --input=note.md
 *   node scripts/run-pipeline.mjs --input=note.md --stop-after=topicPlanner
 *   node scripts/run-pipeline.mjs --input=note.md --start-from=questionGenerator --context=context.json
 *
 * 옵션:
 *   --input       옵시디언 논문 노트 파일 경로 (필수, --start-from 없을 때)
 *   --start-from  시작 스텝 (topicPlanner|questionGenerator|draftWriter|factChecker|policyReviewer|seoPackager)
 *   --stop-after  종료 스텝
 *   --context     이전 실행 컨텍스트 JSON 파일 경로
 *   --output      결과 저장 경로 (기본: stdout + pipeline-output.json)
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

// .env 로드 (dotenv 설치 시)
try {
  const dotenv = await import('dotenv');
  dotenv.config({ path: resolve(process.cwd(), '.env') });
} catch {
  // dotenv 없으면 환경변수가 이미 설정되어 있어야 함
}

// ESM에서 Next.js alias(@/)를 사용할 수 없으므로 직접 경로로 import
const { default: OpenAI } = await import('openai');

// OpenAI 클라이언트를 환경변수로 직접 생성
const openaiClient = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// 시스템 프롬프트 직접 로드
const { default: SYSTEM_PROMPT } = await import('../lib/blog-pipeline/system-prompt.js');

// ---- 헬퍼: OpenAI 호출 ----
async function callOpenAI(userPrompt, temperature = 0.7) {
  const response = await openaiClient.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userPrompt },
    ],
    temperature,
  });
  return response.choices[0].message.content;
}

// ---- 각 스텝 프롬프트 재사용 (파일에서 import 대신 인라인) ----
const steps = [
  {
    name: 'topicPlanner',
    run: async (ctx) => {
      const result = await callOpenAI(
        `[역할] 너는 네이버 블로그 글감 기획자이다.\n[목표] 아래 입력(논문 요약 노트)에서 부모가 검색할 법한 주제를 노출 친화적으로 재구성한다.\n\n[입력]\n- 논문요약노트:\n${ctx.obsidianNote}\n\n[작업]\n1) 논문에서 부모 관심사로 변환 가능한 핵심 개념을 3~7개 추출한다.\n2) 각 개념을 '부모 검색 문장'으로 바꾼다.\n3) 네이버 블로그에 적합한 주제 후보를 5개 만든다.\n4) 각 후보에 대해:\n   - 예상 독자 불안 포인트(한 문장)\n   - 글에서 제공할 약속(한 문장)\n   - 위험 표현 체크 한 줄 경고\n를 붙인다.\n\n[출력 형식]\n- 후보 1~5를 번호로 제시한다.\n- 마지막에 "이번 글로 가장 적합한 1개"를 추천하고 이유를 2줄로 설명한다.`
      );
      return { topicCandidates: result };
    },
  },
  {
    name: 'questionGenerator',
    run: async (ctx) => {
      const result = await callOpenAI(
        `[역할] 너는 부모 상담 스크립트 작성자이다.\n[목표] 선택된 주제에 대해 부모가 실제로 던질 질문을 생성해 글의 골격을 만든다.\n\n[입력]\n- 선택주제: ${ctx.selectedTopic}\n- 논문요약노트:\n${ctx.obsidianNote}\n\n[작업]\n1) 부모 질문을 8~12개 만든다.\n2) 질문은 난이도 순으로 배열한다:\n   - (초반) "지금 당장 불안한 질문"\n   - (중반) "왜 그런지 이해하려는 질문"\n   - (후반) "그래서 뭘 해야 하는지 질문"\n3) 질문에는 비난/낙인/죄책감 유발 표현을 넣지 않는다.\n\n[출력 형식]\n- Q1~Q12 목록\n- 마지막에 "이 질문 흐름으로 글을 구성하면 좋은 이유" 3줄`
      );
      return { parentQuestions: result };
    },
  },
  {
    name: 'draftWriter',
    run: async (ctx) => {
      const result = await callOpenAI(
        `[역할] 너는 소아청소년과 의사 블로거이다.\n[목표] 부모가 이해할 수 있는 1500자 내외 네이버 블로그 글 초안을 쓴다.\n\n[입력]\n- 선택주제: ${ctx.selectedTopic}\n- 부모질문목록:\n${ctx.parentQuestions}\n- 논문요약노트:\n${ctx.obsidianNote}\n\n[글 구조(반드시 이 순서)]\n1) 문제 제기: 부모가 '검색하게 된 장면'을 짧은 스토리로 시작한다.\n2) 부모 공감: "그럴 수 있다"를 과학/현실 기반으로 공감한다.\n3) 과학 설명: 논문에서 핵심 개념을 2~3개로 정리해 설명한다.\n4) 실제 양육 팁: 오늘부터 할 수 있는 행동 가이드 3~5개.\n5) 정리: 현실 적용 메시지 3가지(교훈/안심/실행방법)로 마무리한다.\n\n[금지/주의]\n- "반드시/무조건/100%" 같은 단정 금지\n- 치료효과를 확정적으로 표현 금지\n- 특정 제품/시술 홍보처럼 보이게 금지\n- 공포 조장 금지\n\n[출력]\n- 제목 없이 본문만 작성(약 1500자 ±15%)`
      );
      return { draft: result };
    },
  },
  {
    name: 'factChecker',
    run: async (ctx) => {
      const latest = ctx.latestSourcesSummary ? `- 최신자료요약:\n${ctx.latestSourcesSummary}` : '';
      const result = await callOpenAI(
        `[역할] 너는 팩트체커이다.\n[목표] 초안의 과학적 주장과 임상적 해석을 검증하고, 과장/비약을 제거한다.\n\n[입력]\n- 초안본문:\n${ctx.draft}\n- 논문요약노트:\n${ctx.obsidianNote}\n${latest}\n\n[작업]\n1) 초안에서 "사실 주장" 문장을 8~15개 뽑는다.\n2) 각 주장에 대해 상태를 표시한다:\n   - [논문근거있음]\n   - [일반지식/임상상식]\n   - [추정/해석]\n   - [검증필요]\n3) [추정/해석]은 표현을 완화한 대체 문장을 제안한다.\n4) [검증필요]는 삭제 또는 안전 문구로 전환한다.\n5) 결과로 '수정된 본문'을 다시 출력한다.\n\n[출력 형식]\nA) 주장 점검표(간단히)\nB) 수정된 본문(1500자 범위 유지)`,
        0.3
      );
      const revisedMatch = result.match(/B\)\s*수정된 본문[\s\S]*?\n([\s\S]+)$/);
      return { factCheckReport: result, draft: revisedMatch ? revisedMatch[1].trim() : result };
    },
  },
  {
    name: 'policyReviewer',
    run: async (ctx) => {
      const result = await callOpenAI(
        `[역할] 너는 네이버 블로그 정책/품질 점검자이다.\n[목표] 글이 과장·의학적 단정·공포 조장·상업적 홍보처럼 보이는 위험을 줄인다.\n\n[입력]\n- 본문:\n${ctx.draft}\n\n[체크리스트]\n- 단정/확정 표현(무조건/반드시/완치/확실) 존재 여부\n- 공포 조장/극단 사례로 압박하는 문장 존재 여부\n- 특정 치료/기기/제품으로 유도하는 뉘앙스 존재 여부\n- 의료 조언이 개인 진료처럼 보이는 문장 존재 여부\n- 과학 설명이 "권위로 찍어누르는" 말투인지 여부\n- 부모 죄책감 유발 문장 존재 여부\n- 제목/해시태그와 본문 주제가 불일치하는지 여부\n\n[출력]\n1) 위험 항목이 있으면 "문장 그대로 인용 + 왜 위험한지 + 대체 문장"으로 제시\n2) 수정 반영한 최종 본문 출력`,
        0.3
      );
      const finalMatch = result.match(/2\)\s*수정 반영한 최종 본문[\s\S]*?\n([\s\S]+)$/);
      return { policyReport: result, draft: finalMatch ? finalMatch[1].trim() : result };
    },
  },
  {
    name: 'seoPackager',
    run: async (ctx) => {
      const kw = ctx.keywords ? `- 핵심키워드: ${ctx.keywords}` : '- 핵심키워드: (본문에서 추출)';
      const result = await callOpenAI(
        `[역할] 너는 네이버 블로그 SEO 카피라이터이다.\n[목표] 본문과 일치하는 노출 친화적인 제목과 해시태그를 만든다.\n\n[입력]\n- 최종본문:\n${ctx.draft}\n${kw}\n\n[작업]\n1) 제목 5개 생성:\n   - (A) 정보형\n   - (B) 질문형(부모 검색 문장형)\n   - (C) 공감형(불안 완화형)\n   - (D) 가이드형("~하는 법")\n   - (E) 스토리형(짧은 장면 제시)\n2) 제목은 과장 금지, 본문 내용과 1:1로 맞아야 한다.\n3) 해시태그 15개:\n   - 너무 의료 전문으로만 가지 말고(부모용)\n   - 너무 일반 육아로만 흐리지 말기(브랜딩)\n   - 중복 최소화\n\n[출력 형식]\n- 제목 후보 1~5\n- 해시태그 15개(한 줄로)`
      );
      return { seoPackage: result };
    },
  },
];

// ---- CLI 인자 파싱 ----
function parseArgs() {
  const args = {};
  for (const arg of process.argv.slice(2)) {
    const match = arg.match(/^--([^=]+)=(.+)$/);
    if (match) {
      args[match[1]] = match[2];
    }
  }
  return args;
}

// ---- 메인 ----
async function main() {
  const args = parseArgs();

  if (!args.input && !args.context) {
    console.error('사용법: node scripts/run-pipeline.mjs --input=note.md [--stop-after=topicPlanner] [--start-from=questionGenerator --context=context.json]');
    process.exit(1);
  }

  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY 환경변수가 설정되지 않았습니다.');
    process.exit(1);
  }

  // 컨텍스트 로드
  let ctx = {};
  if (args.context) {
    const contextPath = resolve(process.cwd(), args.context);
    ctx = JSON.parse(readFileSync(contextPath, 'utf-8'));
  }

  // 입력 노트 로드
  if (args.input) {
    const inputPath = resolve(process.cwd(), args.input);
    ctx.obsidianNote = readFileSync(inputPath, 'utf-8');
  }

  const startFrom = args['start-from'];
  const stopAfter = args['stop-after'];
  const outputPath = args.output || 'pipeline-output.json';

  let started = !startFrom;

  for (const step of steps) {
    if (!started) {
      if (step.name === startFrom) {
        started = true;
      } else {
        continue;
      }
    }

    console.log(`\n${'='.repeat(60)}`);
    console.log(`[${step.name}] 실행 중...`);
    console.log('='.repeat(60));

    const result = await step.run(ctx);
    Object.assign(ctx, result);

    // 각 스텝 결과 출력
    for (const [key, value] of Object.entries(result)) {
      console.log(`\n--- ${key} ---`);
      console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2));
    }

    if (stopAfter && step.name === stopAfter) {
      console.log(`\n[${stopAfter}] 이후 중단됨. 컨텍스트를 ${outputPath}에 저장합니다.`);
      break;
    }
  }

  // 결과 저장
  writeFileSync(resolve(process.cwd(), outputPath), JSON.stringify(ctx, null, 2), 'utf-8');
  console.log(`\n결과가 ${outputPath}에 저장되었습니다.`);
}

main().catch((err) => {
  console.error('파이프라인 오류:', err);
  process.exit(1);
});
