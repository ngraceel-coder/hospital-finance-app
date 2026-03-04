import { run as topicPlanner } from './steps/a-topic-planner';
import { run as questionGenerator } from './steps/b-question-generator';
import { run as draftWriter } from './steps/c-draft-writer';
import { run as factChecker } from './steps/d-fact-checker';
import { run as policyReviewer } from './steps/e-policy-reviewer';
import { run as seoPackager } from './steps/f-seo-packager';

const STEPS = [
  { name: 'topicPlanner', run: topicPlanner },
  { name: 'questionGenerator', run: questionGenerator },
  { name: 'draftWriter', run: draftWriter },
  { name: 'factChecker', run: factChecker },
  { name: 'policyReviewer', run: policyReviewer },
  { name: 'seoPackager', run: seoPackager },
];

/**
 * 블로그 파이프라인 실행
 *
 * @param {Object} options
 * @param {string} options.obsidianNote - 옵시디언 논문 요약 노트 (필수)
 * @param {string} [options.startFrom] - 시작할 스텝 이름 (기본: 'topicPlanner')
 * @param {string} [options.stopAfter] - 멈출 스텝 이름 (기본: 마지막까지)
 * @param {Object} [options.context] - 이전 실행 결과를 이어받을 컨텍스트
 * @param {Function} [options.onStep] - 각 스텝 완료 시 콜백 (name, result) => void
 * @returns {Object} 최종 컨텍스트 (모든 스텝 결과 포함)
 */
export async function runPipeline({
  obsidianNote,
  startFrom,
  stopAfter,
  context = {},
  onStep,
} = {}) {
  const ctx = { obsidianNote, ...context };

  let started = !startFrom;

  for (const step of STEPS) {
    if (!started) {
      if (step.name === startFrom) {
        started = true;
      } else {
        continue;
      }
    }

    if (onStep) {
      onStep(step.name, 'start');
    }

    const result = await step.run(ctx);
    Object.assign(ctx, result);

    if (onStep) {
      onStep(step.name, 'done', result);
    }

    if (stopAfter && step.name === stopAfter) {
      break;
    }
  }

  return ctx;
}

export { STEPS };
