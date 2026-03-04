import OpenAI from 'openai';

let _openai = null;

function getOpenAI() {
  if (!_openai) {
    _openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  }
  return _openai;
}

export default getOpenAI;
