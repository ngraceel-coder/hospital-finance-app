import React, { useState, useEffect, useRef } from 'react';
import { Camera, Upload, Check, Plus, Trash2, TrendingUp, TrendingDown, Calendar, DollarSign, FileText, AlertCircle, ChevronDown, ChevronUp, Edit2, Save, X } from 'lucide-react';

// 월별 고정비 기준 (스킬에서 가져옴)
const MONTHLY_FIXED_COSTS = {
  인건비: 26000000,
  임대료: 7050000,
  '4대보험': 4500000,
  의약품: 12000000,
  대출이자: 6200000,
  '관리비/청소': 3000000,
};

// 분류 규칙 (hospital-financial-management 스킬 기반)
const INCOME_CATEGORIES = ['카드매출', '심평원', '영유아검진', '예방접종', '현금수입', '이자수입', '기타수입'];
const EXPENSE_CATEGORIES = ['인건비', '임대료', '의약품', '검사비', '4대보험', '세금', '소모품', '대출이자', '렌탈', '기부금', '식비', '광고비', '관리비/청소', '시설투자', '기타운영비'];

// 키워드 기반 자동 분류
const CLASSIFICATION_KEYWORDS = {
  // 수입
  카드매출: ['KB국민', '신한', '삼성', '현대', '롯데', 'BC', '하나', 'NH농협', '카드', 'VAN', '이지스', 'NICE'],
  심평원: ['국민건강', '건강보험', '의료급여', '심평원', '건보'],
  영유아검진: ['영유아', '영검', '검진'],
  예방접종: ['예방접종', '감염과', '보건소', '질병관리'],
  이자수입: ['이자'],
  // 지출
  인건비: ['급여', '#090급여', '프리랜서', '김진', '김다정', '김다혜', '김재영', '박지은', '이지현', '하미선', '노슬기'],
  임대료: ['월세', '임대', '관리비'],
  의약품: ['지엔팜', '보령바이오파마', '동아에스티', '블루팜코리아', '홍익무역', '더편한샵', '블루엠텍', '크레스콤', '레노메디', '해아람', '다한다'],
  검사비: ['녹십자의료재단', '검사', '시약', '의료재단'],
  '4대보험': ['국민연금', '건강보험', '고용보험', '산재보험', '4대보험'],
  세금: ['국세', '지방세', '세무', '부가세', '원천세', '종합소득세', '세무법인나은'],
  소모품: ['네이버페이', '카카오페이', '쿠팡', '온라인', '11번가'],
  대출이자: ['이자', '대출', '원금', '상환', '경남은행', '우리은행', '기업은행', '롯데캐피탈'],
  렌탈: ['렌탈', '렌트'],
  기부금: ['기부', '모금', '충북공동모금회'],
  식비: ['식대', '배달', '음식점', '식당'],
  광고비: ['광고', '마케팅', '현수막', '이동규'],
  '관리비/청소': ['관리비', '청소'],
  시설투자: ['인테리어', '에어컨', '시설', '공사', '김재성', '김형준', '박현민'],
};

// 월별 체크리스트 템플릿
const MONTHLY_CHECKLIST_TEMPLATE = [
  // 세무/회계
  { category: '세무/회계', item: '부가세 신고 (1,4,7,10월)', dueDay: 25, months: [1, 4, 7, 10] },
  { category: '세무/회계', item: '원천세 신고', dueDay: 10, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '세무/회계', item: '종합소득세 신고 (5월)', dueDay: 31, months: [5] },
  { category: '세무/회계', item: '세무법인 자료 제출', dueDay: 5, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  // 급여/인건비
  { category: '급여/인건비', item: '정규직 급여 지급', dueDay: 25, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '급여/인건비', item: '프리랜서 급여 정산', dueDay: 28, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '급여/인건비', item: '4대보험 납부', dueDay: 10, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  // 거래처 결제
  { category: '거래처', item: '의약품 대금 결제 (지엔팜 등)', dueDay: 15, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '거래처', item: '검사비 결제 (녹십자)', dueDay: 20, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '거래처', item: '의료용품 결제', dueDay: 25, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  // 임대료/관리비
  { category: '임대료/관리비', item: '임대료 납부 (기존)', dueDay: 5, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '임대료/관리비', item: '임대료 납부 (신규)', dueDay: 5, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '임대료/관리비', item: '관리비 납부', dueDay: 10, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '임대료/관리비', item: '청소비 결제', dueDay: 15, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  // 대출/금융
  { category: '대출/금융', item: '대출이자 납부 (경남은행)', dueDay: 3, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '대출/금융', item: '대출이자 납부 (기업은행)', dueDay: 5, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '대출/금융', item: '롯데캐피탈 리스료', dueDay: 10, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  // 기타
  { category: '기타', item: '기부금 납부', dueDay: 15, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '기타', item: '렌탈료 결제', dueDay: 20, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
  { category: '기타', item: '은행 거래내역 정리', dueDay: 1, months: [1,2,3,4,5,6,7,8,9,10,11,12] },
];

// 숫자 포맷팅
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(amount);
};

// 자동 분류 함수
const autoClassify = (description, type) => {
  const keywords = type === 'income' ?
    Object.entries(CLASSIFICATION_KEYWORDS).filter(([k]) => INCOME_CATEGORIES.includes(k)) :
    Object.entries(CLASSIFICATION_KEYWORDS).filter(([k]) => EXPENSE_CATEGORIES.includes(k));

  for (const [category, words] of keywords) {
    if (words.some(word => description.includes(word))) {
      return category;
    }
  }
  return type === 'income' ? '기타수입' : '기타운영비';
};

export default function HospitalFinanceApp() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [transactions, setTransactions] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [isAddingTransaction, setIsAddingTransaction] = useState(false);
  const [newTransaction, setNewTransaction] = useState({ date: '', type: 'expense', amount: '', description: '', category: '' });
  const [ocrResult, setOcrResult] = useState('');
  const [isProcessingOCR, setIsProcessingOCR] = useState(false);
  const fileInputRef = useRef(null);

  // 월별 체크리스트 초기화
  useEffect(() => {
    const monthChecklist = MONTHLY_CHECKLIST_TEMPLATE
      .filter(item => item.months.includes(currentMonth))
      .map(item => ({
        ...item,
        id: `${item.category}-${item.item}-${currentMonth}`,
        checked: false,
        dueDate: new Date(currentYear, currentMonth - 1, item.dueDay),
      }));

    // 로컬 스토리지에서 저장된 체크 상태 불러오기
    const savedChecklist = localStorage.getItem(`checklist-${currentYear}-${currentMonth}`);
    if (savedChecklist) {
      const saved = JSON.parse(savedChecklist);
      monthChecklist.forEach(item => {
        const found = saved.find(s => s.id === item.id);
        if (found) item.checked = found.checked;
      });
    }
    setChecklist(monthChecklist);
  }, [currentMonth, currentYear]);

  // 거래내역 로컬 스토리지 저장/불러오기
  useEffect(() => {
    const saved = localStorage.getItem('hospital-transactions');
    if (saved) setTransactions(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem('hospital-transactions', JSON.stringify(transactions));
  }, [transactions]);

  // 체크리스트 저장
  useEffect(() => {
    if (checklist.length > 0) {
      localStorage.setItem(`checklist-${currentYear}-${currentMonth}`, JSON.stringify(checklist));
    }
  }, [checklist, currentYear, currentMonth]);

  // 이번 달 거래 필터링
  const currentMonthTransactions = transactions.filter(t => {
    const date = new Date(t.date);
    return date.getMonth() + 1 === currentMonth && date.getFullYear() === currentYear;
  });

  // 수입/지출 합계
  const totalIncome = currentMonthTransactions.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0);
  const totalExpense = currentMonthTransactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + t.amount, 0);
  const balance = totalIncome - totalExpense;

  // 예상 지출 계산
  const totalFixedCosts = Object.values(MONTHLY_FIXED_COSTS).reduce((a, b) => a + b, 0);
  const remainingExpected = totalFixedCosts - totalExpense;

  // 분류별 지출 합계
  const expenseByCategory = currentMonthTransactions
    .filter(t => t.type === 'expense')
    .reduce((acc, t) => {
      acc[t.category] = (acc[t.category] || 0) + t.amount;
      return acc;
    }, {});

  // OCR 처리 (Tesseract.js 사용)
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessingOCR(true);
    setOcrResult('');

    try {
      // Tesseract.js 로드 및 실행
      if (!window.Tesseract) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js';
        document.body.appendChild(script);
        await new Promise(resolve => script.onload = resolve);
      }

      const { createWorker } = window.Tesseract;
      const worker = await createWorker('kor+eng');

      const imageUrl = URL.createObjectURL(file);
      const { data: { text } } = await worker.recognize(imageUrl);
      await worker.terminate();
      URL.revokeObjectURL(imageUrl);

      setOcrResult(text);

      // 텍스트에서 날짜, 금액 추출 시도
      const dateMatch = text.match(/(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})|(\d{1,2}[-/.]\d{1,2})/);
      const amountMatch = text.match(/[\d,]+원|[\d,]+\s*원/g);

      if (dateMatch || amountMatch) {
        const extractedDate = dateMatch ? dateMatch[0].replace(/[/.]/g, '-') : new Date().toISOString().split('T')[0];
        const extractedAmount = amountMatch ?
          parseInt(amountMatch[0].replace(/[,원\s]/g, '')) : 0;

        setNewTransaction(prev => ({
          ...prev,
          date: extractedDate.length === 10 ? extractedDate : `${currentYear}-${extractedDate}`,
          amount: extractedAmount || '',
          description: text.substring(0, 100),
        }));
      }
    } catch (error) {
      console.error('OCR Error:', error);
      setOcrResult('이미지 인식에 실패했습니다. 수동으로 입력해주세요.');
    } finally {
      setIsProcessingOCR(false);
    }
  };

  // 거래 추가
  const addTransaction = () => {
    if (!newTransaction.date || !newTransaction.amount) return;

    const category = newTransaction.category || autoClassify(newTransaction.description, newTransaction.type);

    setTransactions(prev => [...prev, {
      id: Date.now(),
      ...newTransaction,
      amount: parseInt(newTransaction.amount),
      category,
    }]);

    setNewTransaction({ date: '', type: 'expense', amount: '', description: '', category: '' });
    setIsAddingTransaction(false);
    setOcrResult('');
  };

  // 거래 삭제
  const deleteTransaction = (id) => {
    setTransactions(prev => prev.filter(t => t.id !== id));
  };

  // 체크리스트 토글
  const toggleChecklistItem = (id) => {
    setChecklist(prev => prev.map(item =>
      item.id === id ? { ...item, checked: !item.checked } : item
    ));
  };

  // 진행률 계산
  const checklistProgress = checklist.length > 0 ?
    Math.round((checklist.filter(c => c.checked).length / checklist.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl font-bold">🏥 온소아청소년과의원 재정관리</h1>
          <p className="text-blue-100 text-sm mt-1">{currentYear}년 {currentMonth}월</p>
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <nav className="bg-white shadow">
        <div className="max-w-6xl mx-auto flex">
          {[
            { id: 'dashboard', label: '대시보드', icon: TrendingUp },
            { id: 'transactions', label: '거래내역', icon: DollarSign },
            { id: 'checklist', label: '월별 체크리스트', icon: Calendar },
            { id: 'upload', label: '사진 업로드', icon: Camera },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-600 hover:text-blue-600'
              }`}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-6">
        {/* 월 선택 */}
        <div className="flex gap-2 mb-6">
          <select
            value={currentYear}
            onChange={(e) => setCurrentYear(parseInt(e.target.value))}
            className="border rounded px-3 py-2"
          >
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
          <select
            value={currentMonth}
            onChange={(e) => setCurrentMonth(parseInt(e.target.value))}
            className="border rounded px-3 py-2"
          >
            {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => <option key={m} value={m}>{m}월</option>)}
          </select>
        </div>

        {/* 대시보드 탭 */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* 요약 카드 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl p-6 shadow-sm border-l-4 border-green-500">
                <p className="text-gray-500 text-sm">이번 달 수입</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(totalIncome)}</p>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-sm border-l-4 border-red-500">
                <p className="text-gray-500 text-sm">이번 달 지출</p>
                <p className="text-2xl font-bold text-red-600">{formatCurrency(totalExpense)}</p>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-sm border-l-4 border-blue-500">
                <p className="text-gray-500 text-sm">순이익</p>
                <p className={`text-2xl font-bold ${balance >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {formatCurrency(balance)}
                </p>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-sm border-l-4 border-orange-500">
                <p className="text-gray-500 text-sm">예상 추가 지출</p>
                <p className="text-2xl font-bold text-orange-600">{formatCurrency(Math.max(0, remainingExpected))}</p>
              </div>
            </div>

            {/* 체크리스트 진행률 */}
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Calendar size={20} />
                이번 달 업무 진행률
              </h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-600 h-4 rounded-full transition-all"
                    style={{ width: `${checklistProgress}%` }}
                  />
                </div>
                <span className="font-bold text-lg">{checklistProgress}%</span>
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {checklist.filter(c => c.checked).length} / {checklist.length} 완료
              </p>
            </div>

            {/* 분류별 지출 */}
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <TrendingDown size={20} />
                분류별 지출 현황
              </h3>
              <div className="space-y-3">
                {Object.entries(MONTHLY_FIXED_COSTS).map(([category, expected]) => {
                  const actual = expenseByCategory[category] || 0;
                  const percentage = Math.min(100, Math.round((actual / expected) * 100));
                  return (
                    <div key={category}>
                      <div className="flex justify-between text-sm mb-1">
                        <span>{category}</span>
                        <span className={actual > expected ? 'text-red-600 font-semibold' : ''}>
                          {formatCurrency(actual)} / {formatCurrency(expected)}
                        </span>
                      </div>
                      <div className="bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            percentage > 100 ? 'bg-red-500' : percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 예측 알림 */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
              <h3 className="font-semibold mb-2 flex items-center gap-2 text-amber-800">
                <AlertCircle size={20} />
                이번 달 예측
              </h3>
              <p className="text-amber-700">
                예상 총 지출: <strong>{formatCurrency(totalFixedCosts)}</strong><br />
                현재까지 지출: <strong>{formatCurrency(totalExpense)}</strong><br />
                앞으로 필요 예상 금액: <strong>{formatCurrency(Math.max(0, remainingExpected))}</strong>
              </p>
            </div>
          </div>
        )}

        {/* 거래내역 탭 */}
        {activeTab === 'transactions' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">거래 내역</h2>
              <button
                onClick={() => setIsAddingTransaction(true)}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700"
              >
                <Plus size={18} /> 직접 추가
              </button>
            </div>

            {/* 거래 추가 폼 */}
            {isAddingTransaction && (
              <div className="bg-white rounded-xl p-6 shadow-sm border-2 border-blue-200">
                <h3 className="font-semibold mb-4">새 거래 추가</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">날짜</label>
                    <input
                      type="date"
                      value={newTransaction.date}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, date: e.target.value }))}
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">구분</label>
                    <select
                      value={newTransaction.type}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, type: e.target.value, category: '' }))}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="expense">지출</option>
                      <option value="income">수입</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">금액</label>
                    <input
                      type="number"
                      value={newTransaction.amount}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, amount: e.target.value }))}
                      placeholder="금액 입력"
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">분류</label>
                    <select
                      value={newTransaction.category}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">자동 분류</option>
                      {(newTransaction.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm text-gray-600 mb-1">내용</label>
                    <input
                      type="text"
                      value={newTransaction.description}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="거래처 또는 내용"
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={addTransaction}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700"
                  >
                    <Save size={18} /> 저장
                  </button>
                  <button
                    onClick={() => { setIsAddingTransaction(false); setNewTransaction({ date: '', type: 'expense', amount: '', description: '', category: '' }); }}
                    className="bg-gray-200 px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-gray-300"
                  >
                    <X size={18} /> 취소
                  </button>
                </div>
              </div>
            )}

            {/* 거래 목록 */}
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">날짜</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">구분</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">분류</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">내용</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600">금액</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-600">삭제</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {currentMonthTransactions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        이번 달 거래 내역이 없습니다
                      </td>
                    </tr>
                  ) : (
                    currentMonthTransactions.sort((a, b) => new Date(b.date) - new Date(a.date)).map(t => (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm">{t.date}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            t.type === 'income' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {t.type === 'income' ? '수입' : '지출'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">{t.category}</td>
                        <td className="px-4 py-3 text-sm">{t.description || '-'}</td>
                        <td className={`px-4 py-3 text-sm text-right font-semibold ${
                          t.type === 'income' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {t.type === 'income' ? '+' : '-'}{formatCurrency(t.amount)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => deleteTransaction(t.id)}
                            className="text-red-500 hover:text-red-700"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 체크리스트 탭 */}
        {activeTab === 'checklist' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">{currentMonth}월 업무 체크리스트</h2>
              <div className="text-sm text-gray-500">
                {checklist.filter(c => c.checked).length} / {checklist.length} 완료
              </div>
            </div>

            {/* 카테고리별 체크리스트 */}
            {['세무/회계', '급여/인건비', '거래처', '임대료/관리비', '대출/금융', '기타'].map(category => {
              const items = checklist.filter(c => c.category === category);
              if (items.length === 0) return null;

              return (
                <div key={category} className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <div className="bg-blue-50 px-4 py-3 font-semibold text-blue-800">
                    {category}
                  </div>
                  <div className="divide-y">
                    {items.map(item => {
                      const isOverdue = !item.checked && new Date() > item.dueDate;
                      const isUpcoming = !item.checked && new Date() <= item.dueDate &&
                        (item.dueDate - new Date()) / (1000 * 60 * 60 * 24) <= 3;

                      return (
                        <div
                          key={item.id}
                          className={`px-4 py-3 flex items-center gap-3 ${
                            isOverdue ? 'bg-red-50' : isUpcoming ? 'bg-yellow-50' : ''
                          }`}
                        >
                          <button
                            onClick={() => toggleChecklistItem(item.id)}
                            className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                              item.checked
                                ? 'bg-green-500 border-green-500 text-white'
                                : 'border-gray-300 hover:border-blue-500'
                            }`}
                          >
                            {item.checked && <Check size={14} />}
                          </button>
                          <div className="flex-1">
                            <p className={item.checked ? 'line-through text-gray-400' : ''}>
                              {item.item}
                            </p>
                            <p className={`text-xs ${isOverdue ? 'text-red-600 font-semibold' : 'text-gray-400'}`}>
                              {item.dueDay}일까지 {isOverdue && '⚠️ 기한 초과!'}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 사진 업로드 탭 */}
        {activeTab === 'upload' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold">사진으로 거래 추가</h2>

            {/* 업로드 영역 */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="bg-white rounded-xl p-12 shadow-sm border-2 border-dashed border-gray-300 hover:border-blue-500 cursor-pointer transition-colors text-center"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              <Upload size={48} className="mx-auto text-gray-400 mb-4" />
              <p className="text-lg font-semibold text-gray-700">클릭하여 이미지 업로드</p>
              <p className="text-sm text-gray-500 mt-2">
                은행 앱 캡처, 영수증, 거래내역 사진 등
              </p>
            </div>

            {/* OCR 처리 중 */}
            {isProcessingOCR && (
              <div className="bg-blue-50 rounded-xl p-6 text-center">
                <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-blue-700">이미지를 분석하고 있습니다...</p>
              </div>
            )}

            {/* OCR 결과 */}
            {ocrResult && !isProcessingOCR && (
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <FileText size={20} />
                  인식 결과
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm whitespace-pre-wrap max-h-40 overflow-auto">
                  {ocrResult}
                </div>

                {/* 자동 추출된 데이터로 폼 채우기 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">날짜</label>
                    <input
                      type="date"
                      value={newTransaction.date}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, date: e.target.value }))}
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">구분</label>
                    <select
                      value={newTransaction.type}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, type: e.target.value, category: '' }))}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="expense">지출</option>
                      <option value="income">수입</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">금액</label>
                    <input
                      type="number"
                      value={newTransaction.amount}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, amount: e.target.value }))}
                      placeholder="금액 입력"
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">분류</label>
                    <select
                      value={newTransaction.category}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">자동 분류</option>
                      {(newTransaction.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm text-gray-600 mb-1">내용</label>
                    <input
                      type="text"
                      value={newTransaction.description}
                      onChange={(e) => setNewTransaction(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="거래처 또는 내용"
                      className="w-full border rounded-lg px-3 py-2"
                    />
                  </div>
                </div>
                <button
                  onClick={addTransaction}
                  className="mt-4 w-full bg-blue-600 text-white px-4 py-3 rounded-lg flex items-center justify-center gap-2 hover:bg-blue-700"
                >
                  <Plus size={18} /> 거래 추가
                </button>
              </div>
            )}

            {/* 안내 */}
            <div className="bg-blue-50 rounded-xl p-6">
              <h3 className="font-semibold text-blue-800 mb-2">💡 사용 팁</h3>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• 은행 앱에서 거래내역 캡처 사진을 올려주세요</li>
                <li>• 영수증 사진도 인식됩니다</li>
                <li>• 인식이 정확하지 않으면 직접 수정할 수 있어요</li>
                <li>• 거래처 이름이 포함되면 자동으로 분류됩니다</li>
              </ul>
            </div>
          </div>
        )}
      </main>

      {/* 푸터 */}
      <footer className="bg-gray-100 p-4 mt-12">
        <div className="max-w-6xl mx-auto text-center text-sm text-gray-500">
          온소아청소년과의원 재정관리 시스템 | 데이터는 브라우저에 저장됩니다
        </div>
      </footer>
    </div>
  );
}
