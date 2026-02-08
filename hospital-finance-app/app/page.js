'use client';

import { useState, useEffect, useRef } from 'react';

// 분류 카테고리
const INCOME_CATEGORIES = ['카드매출', '심평원', '영유아검진', '예방접종', '현금수입', '이자수입', '기타수입'];
const EXPENSE_CATEGORIES = ['인건비', '임대료', '의약품', '검사비', '4대보험', '세금', '소모품', '대출이자', '렌탈', '기부금', '식비', '광고비', '관리비/청소', '시설투자', '기타운영비'];
const CHECKLIST_CATEGORIES = ['세무/회계', '급여/인건비', '거래처', '임대료/관리비', '대출/금융', '기타'];

// 키워드 기반 자동 분류
const CLASSIFICATION_KEYWORDS = {
  카드매출: ['KB국민', '신한', '삼성', '현대', '롯데', 'BC', '하나', 'NH농협', '카드', 'VAN', '이지스', 'NICE'],
  심평원: ['국민건강', '건강보험', '의료급여', '심평원', '건보'],
  영유아검진: ['영유아', '영검', '검진'],
  예방접종: ['예방접종', '감염과', '보건소', '질병관리'],
  인건비: ['급여', '프리랜서', '김진', '김다정', '김다혜', '김재영', '박지은', '이지현', '하미선', '노슬기'],
  임대료: ['월세', '임대'],
  의약품: ['지엔팜', '보령바이오파마', '동아에스티', '블루팜코리아', '홍익무역', '더편한샵', '블루엠텍', '크레스콤', '레노메디', '해아람', '다한다'],
  검사비: ['녹십자의료재단', '검사', '시약', '의료재단'],
  '4대보험': ['국민연금', '건강보험', '고용보험', '산재보험', '4대보험'],
  세금: ['국세', '지방세', '세무', '부가세', '원천세', '종합소득세'],
  대출이자: ['이자', '대출', '상환', '경남은행', '우리은행', '기업은행', '롯데캐피탈'],
  기부금: ['기부', '모금', '충북공동모금회'],
  식비: ['식대', '배달', '음식점', '식당'],
  광고비: ['광고', '마케팅', '현수막'],
  '관리비/청소': ['관리비', '청소'],
};

// 숫자 포맷팅
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(amount);
};

// 자동 분류
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

// 업로드 탭 컴포넌트 (Claude AI OCR)
function UploadTab({ fileInputRef, handleImageUpload, isProcessingOCR, ocrResult, ocrError, setOcrResult, addOcrTransactions, formatCurrency }) {
  const [selectedIndexes, setSelectedIndexes] = useState([]);

  const toggleSelect = (index) => {
    setSelectedIndexes(prev =>
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const selectAll = () => {
    if (ocrResult?.transactions) {
      setSelectedIndexes(ocrResult.transactions.map((_, i) => i));
    }
  };

  const deselectAll = () => {
    setSelectedIndexes([]);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">📷 사진으로 거래 추가</h2>
        <span className="text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">GPT-4o-mini OCR</span>
      </div>

      <div onClick={() => fileInputRef.current?.click()} className="bg-white rounded-xl p-12 shadow-sm border-2 border-dashed border-gray-300 hover:border-blue-500 cursor-pointer text-center transition-colors">
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
        <div className="text-6xl mb-4">📤</div>
        <p className="text-lg font-semibold text-gray-700">클릭하여 이미지 업로드</p>
        <p className="text-sm text-gray-500 mt-2">은행 앱 캡처, 영수증, 거래내역 사진</p>
      </div>

      {isProcessingOCR && (
        <div className="bg-blue-50 rounded-xl p-8 text-center">
          <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-blue-700 font-medium">GPT-4o-mini가 이미지를 분석하고 있습니다...</p>
          <p className="text-blue-500 text-sm mt-2">잠시만 기다려주세요</p>
        </div>
      )}

      {ocrError && !isProcessingOCR && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <p className="text-red-700">❌ {ocrError}</p>
          <button onClick={() => setOcrResult(null)} className="mt-2 text-sm text-red-600 underline">다시 시도</button>
        </div>
      )}

      {ocrResult?.transactions && !isProcessingOCR && (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="bg-green-50 p-4 border-b flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-green-800">✅ {ocrResult.transactions.length}건의 거래를 인식했습니다</h3>
              {ocrResult.bank && <p className="text-sm text-green-600">{ocrResult.bank}</p>}
            </div>
            <div className="flex gap-2">
              <button onClick={selectAll} className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded hover:bg-green-200">전체 선택</button>
              <button onClick={deselectAll} className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded hover:bg-gray-200">선택 해제</button>
            </div>
          </div>

          <div className="divide-y max-h-96 overflow-auto">
            {ocrResult.transactions.map((t, index) => (
              <div
                key={index}
                onClick={() => toggleSelect(index)}
                className={`p-4 cursor-pointer transition-colors ${selectedIndexes.includes(index) ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${selectedIndexes.includes(index) ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300'}`}>
                    {selectedIndexes.includes(index) && '✓'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium truncate">{t.description}</p>
                        <p className="text-sm text-gray-500">{t.date} {t.time && `${t.time}`}</p>
                        {t.memo && <p className="text-xs text-gray-400">메모: {t.memo}</p>}
                      </div>
                      <div className="text-right ml-4">
                        <p className={`font-bold ${t.type === '입금' ? 'text-green-600' : 'text-red-600'}`}>
                          {t.type === '입금' ? '+' : '-'}{formatCurrency(t.amount)}
                        </p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${t.type === '입금' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {t.category}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 bg-gray-50 border-t flex justify-between items-center">
            <p className="text-sm text-gray-600">{selectedIndexes.length}건 선택됨</p>
            <div className="flex gap-2">
              <button onClick={() => setOcrResult(null)} className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300">취소</button>
              <button
                onClick={() => addOcrTransactions(selectedIndexes)}
                disabled={selectedIndexes.length === 0}
                className={`px-4 py-2 rounded-lg ${selectedIndexes.length > 0 ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
              >
                선택한 {selectedIndexes.length}건 추가
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-blue-50 rounded-xl p-6">
        <h3 className="font-semibold text-blue-800 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• 은행 앱에서 거래내역 캡처 사진을 올려주세요</li>
          <li>• GPT-4o-mini가 자동으로 날짜, 금액, 거래처를 인식합니다</li>
          <li>• 여러 거래가 있으면 한꺼번에 선택해서 추가할 수 있어요</li>
          <li>• 분류도 자동으로 됩니다 (더편한샵 → 의료용품 등)</li>
        </ul>
      </div>
    </div>
  );
}

export default function Home() {
  // 인증 상태
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // 앱 상태
  const [activeTab, setActiveTab] = useState('dashboard');
  const [transactions, setTransactions] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [settings, setSettings] = useState([]);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());

  // 폼 상태
  const [isAddingTransaction, setIsAddingTransaction] = useState(false);
  const [newTransaction, setNewTransaction] = useState({ date: '', type: 'expense', amount: '', description: '', category: '' });
  const [isAddingChecklist, setIsAddingChecklist] = useState(false);
  const [newChecklist, setNewChecklist] = useState({ category: '세무/회계', item: '', dueDay: 1, months: [] });
  const [isAddingSetting, setIsAddingSetting] = useState(false);
  const [newSetting, setNewSetting] = useState({ category: '', amount: '' });
  const [editingSetting, setEditingSetting] = useState(null);
  const [editingChecklist, setEditingChecklist] = useState(null);

  // OCR 상태
  const [ocrResult, setOcrResult] = useState(null); // { transactions: [], bank: '' }
  const [isProcessingOCR, setIsProcessingOCR] = useState(false);
  const [ocrError, setOcrError] = useState('');
  const fileInputRef = useRef(null);

  // 로그인 확인
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      verifyToken(token);
    } else {
      setIsLoading(false);
    }
  }, []);

  const verifyToken = async (token) => {
    try {
      const res = await fetch('/api/auth', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.authenticated) {
        setIsLoggedIn(true);
        loadData();
      } else {
        localStorage.removeItem('auth_token');
      }
    } catch (error) {
      localStorage.removeItem('auth_token');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (data.success) {
        localStorage.setItem('auth_token', data.token);
        setIsLoggedIn(true);
        loadData();
      } else {
        setLoginError(data.error);
      }
    } catch (error) {
      setLoginError('로그인 중 오류가 발생했습니다.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setIsLoggedIn(false);
    setTransactions([]);
    setChecklist([]);
    setSettings([]);
  };

  // 데이터 로드
  const loadData = async () => {
    try {
      const [transRes, checkRes, settingsRes] = await Promise.all([
        fetch('/api/transactions'),
        fetch('/api/checklist'),
        fetch('/api/settings'),
      ]);
      const [trans, check, sett] = await Promise.all([
        transRes.json(),
        checkRes.json(),
        settingsRes.json(),
      ]);
      setTransactions(trans);
      setChecklist(check);
      setSettings(sett);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  // 이번 달 거래 필터링
  const currentMonthTransactions = transactions.filter(t => {
    const date = new Date(t.date);
    return date.getMonth() + 1 === currentMonth && date.getFullYear() === currentYear;
  });

  // 수입/지출 합계
  const totalIncome = currentMonthTransactions.filter(t => t.type === '수입' || t.type === 'income').reduce((sum, t) => sum + t.amount, 0);
  const totalExpense = currentMonthTransactions.filter(t => t.type === '지출' || t.type === 'expense').reduce((sum, t) => sum + t.amount, 0);
  const balance = totalIncome - totalExpense;

  // 월별 고정비 합계
  const totalFixedCosts = settings.reduce((sum, s) => sum + s.amount, 0);
  const remainingExpected = totalFixedCosts - totalExpense;

  // 분류별 지출 합계
  const expenseByCategory = currentMonthTransactions
    .filter(t => t.type === '지출' || t.type === 'expense')
    .reduce((acc, t) => {
      acc[t.category] = (acc[t.category] || 0) + t.amount;
      return acc;
    }, {});

  // 이번 달 체크리스트
  const currentMonthChecklist = checklist.filter(item => item.months.includes(currentMonth));

  // 체크리스트 진행률
  const checklistProgress = currentMonthChecklist.length > 0 ?
    Math.round((currentMonthChecklist.filter(c => c.checked && c.checkMonth === `${currentYear}-${currentMonth}`).length / currentMonthChecklist.length) * 100) : 0;

  // 거래 추가
  const addTransaction = async () => {
    if (!newTransaction.date || !newTransaction.amount) return;

    const category = newTransaction.category || autoClassify(newTransaction.description, newTransaction.type);

    try {
      const res = await fetch('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newTransaction, category }),
      });
      const data = await res.json();
      if (data.success) {
        loadData();
        setNewTransaction({ date: '', type: 'expense', amount: '', description: '', category: '' });
        setIsAddingTransaction(false);
        setOcrResult('');
      }
    } catch (error) {
      console.error('Error adding transaction:', error);
    }
  };

  // 거래 삭제
  const deleteTransaction = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
      await fetch('/api/transactions', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      });
      loadData();
    } catch (error) {
      console.error('Error deleting transaction:', error);
    }
  };

  // 체크리스트 토글
  const toggleChecklistItem = async (item) => {
    const newChecked = !(item.checked && item.checkMonth === `${currentYear}-${currentMonth}`);
    try {
      await fetch('/api/checklist', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.id,
          checked: newChecked,
          checkMonth: newChecked ? `${currentYear}-${currentMonth}` : '',
        }),
      });
      loadData();
    } catch (error) {
      console.error('Error updating checklist:', error);
    }
  };

  // 체크리스트 추가
  const addChecklistItem = async () => {
    if (!newChecklist.item || newChecklist.months.length === 0) return;
    try {
      const res = await fetch('/api/checklist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newChecklist),
      });
      const data = await res.json();
      if (data.success) {
        loadData();
        setNewChecklist({ category: '세무/회계', item: '', dueDay: 1, months: [] });
        setIsAddingChecklist(false);
      }
    } catch (error) {
      console.error('Error adding checklist item:', error);
    }
  };

  // 체크리스트 삭제
  const deleteChecklistItem = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
      await fetch('/api/checklist', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      });
      loadData();
    } catch (error) {
      console.error('Error deleting checklist item:', error);
    }
  };

  // 설정(고정비) 추가
  const addSettingItem = async () => {
    if (!newSetting.category || !newSetting.amount) return;
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSetting),
      });
      const data = await res.json();
      if (data.success) {
        loadData();
        setNewSetting({ category: '', amount: '' });
        setIsAddingSetting(false);
      }
    } catch (error) {
      console.error('Error adding setting:', error);
    }
  };

  // 설정(고정비) 수정
  const updateSettingItem = async () => {
    if (!editingSetting) return;
    try {
      await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingSetting),
      });
      loadData();
      setEditingSetting(null);
    } catch (error) {
      console.error('Error updating setting:', error);
    }
  };

  // 설정(고정비) 삭제
  const deleteSettingItem = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
      await fetch('/api/settings', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      });
      loadData();
    } catch (error) {
      console.error('Error deleting setting:', error);
    }
  };

  // OCR 처리 (Claude API 사용)
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessingOCR(true);
    setOcrResult(null);
    setOcrError('');

    try {
      const formData = new FormData();
      formData.append('image', file);

      const res = await fetch('/api/ocr', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (data.error) {
        setOcrError(data.error);
      } else if (data.transactions) {
        setOcrResult(data);
      } else {
        setOcrError('거래 내역을 인식하지 못했습니다.');
      }
    } catch (error) {
      console.error('OCR Error:', error);
      setOcrError('이미지 분석 중 오류가 발생했습니다.');
    } finally {
      setIsProcessingOCR(false);
    }
  };

  // OCR 결과에서 선택한 거래들을 Notion에 추가
  const addOcrTransactions = async (selectedIndexes) => {
    if (!ocrResult?.transactions) return;

    const selectedTransactions = ocrResult.transactions.filter((_, i) => selectedIndexes.includes(i));

    for (const t of selectedTransactions) {
      try {
        await fetch('/api/transactions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            date: t.date,
            type: t.type === '입금' ? 'income' : 'expense',
            amount: t.amount,
            description: t.description + (t.memo ? ` (${t.memo})` : ''),
            category: t.category,
          }),
        });
      } catch (error) {
        console.error('거래 추가 오류:', error);
      }
    }

    loadData();
    setOcrResult(null);
    alert(`${selectedTransactions.length}건의 거래가 추가되었습니다.`);
  };

  // 로딩 중
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  // 로그인 화면
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="text-6xl mb-4">🏥</div>
            <h1 className="text-2xl font-bold text-gray-800">온소아청소년과의원</h1>
            <p className="text-gray-500 mt-2">재정관리 시스템</p>
          </div>
          <form onSubmit={handleLogin}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">비밀번호</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {loginError && <p className="text-red-500 text-sm mb-4">{loginError}</p>}
            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              로그인
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 메인 앱
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl md:text-2xl font-bold">🏥 온소아청소년과의원 재정관리</h1>
            <p className="text-blue-100 text-sm mt-1">{currentYear}년 {currentMonth}월</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-blue-500 hover:bg-blue-400 px-4 py-2 rounded-lg text-sm"
          >
            로그아웃
          </button>
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <nav className="bg-white shadow overflow-x-auto">
        <div className="max-w-6xl mx-auto flex">
          {[
            { id: 'dashboard', label: '📊 대시보드' },
            { id: 'transactions', label: '💰 거래내역' },
            { id: 'checklist', label: '📋 체크리스트' },
            { id: 'upload', label: '📷 업로드' },
            { id: 'settings', label: '⚙️ 설정' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap px-4 md:px-6 py-4 border-b-2 transition-colors text-sm ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-600 hover:text-blue-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-4 md:p-6">
        {/* 월 선택 */}
        <div className="flex gap-2 mb-6">
          <select value={currentYear} onChange={(e) => setCurrentYear(parseInt(e.target.value))} className="border rounded px-3 py-2">
            {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
          <select value={currentMonth} onChange={(e) => setCurrentMonth(parseInt(e.target.value))} className="border rounded px-3 py-2">
            {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => <option key={m} value={m}>{m}월</option>)}
          </select>
          <button onClick={loadData} className="bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded">🔄 새로고침</button>
        </div>

        {/* 대시보드 */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border-l-4 border-green-500">
                <p className="text-gray-500 text-xs md:text-sm">이번 달 수입</p>
                <p className="text-lg md:text-2xl font-bold text-green-600">{formatCurrency(totalIncome)}</p>
              </div>
              <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border-l-4 border-red-500">
                <p className="text-gray-500 text-xs md:text-sm">이번 달 지출</p>
                <p className="text-lg md:text-2xl font-bold text-red-600">{formatCurrency(totalExpense)}</p>
              </div>
              <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border-l-4 border-blue-500">
                <p className="text-gray-500 text-xs md:text-sm">순이익</p>
                <p className={`text-lg md:text-2xl font-bold ${balance >= 0 ? 'text-blue-600' : 'text-red-600'}`}>{formatCurrency(balance)}</p>
              </div>
              <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border-l-4 border-orange-500">
                <p className="text-gray-500 text-xs md:text-sm">예상 추가 지출</p>
                <p className="text-lg md:text-2xl font-bold text-orange-600">{formatCurrency(Math.max(0, remainingExpected))}</p>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="font-semibold mb-4">📋 이번 달 업무 진행률</h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div className="bg-blue-600 h-4 rounded-full transition-all" style={{ width: `${checklistProgress}%` }} />
                </div>
                <span className="font-bold text-lg">{checklistProgress}%</span>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="font-semibold mb-4">📉 분류별 지출 현황</h3>
              <div className="space-y-3">
                {settings.map(({ category, amount }) => {
                  const actual = expenseByCategory[category] || 0;
                  const percentage = Math.min(100, Math.round((actual / amount) * 100));
                  return (
                    <div key={category}>
                      <div className="flex justify-between text-sm mb-1">
                        <span>{category}</span>
                        <span className={actual > amount ? 'text-red-600 font-semibold' : ''}>
                          {formatCurrency(actual)} / {formatCurrency(amount)}
                        </span>
                      </div>
                      <div className="bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${percentage > 100 ? 'bg-red-500' : percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'}`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
              <h3 className="font-semibold mb-2 text-amber-800">⚠️ 이번 달 예측</h3>
              <p className="text-amber-700">
                예상 총 지출: <strong>{formatCurrency(totalFixedCosts)}</strong><br />
                현재까지 지출: <strong>{formatCurrency(totalExpense)}</strong><br />
                앞으로 필요 예상 금액: <strong>{formatCurrency(Math.max(0, remainingExpected))}</strong>
              </p>
            </div>
          </div>
        )}

        {/* 거래내역 */}
        {activeTab === 'transactions' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">거래 내역</h2>
              <button onClick={() => setIsAddingTransaction(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg">➕ 추가</button>
            </div>

            {isAddingTransaction && (
              <div className="bg-white rounded-xl p-6 shadow-sm border-2 border-blue-200">
                <h3 className="font-semibold mb-4">새 거래 추가</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">날짜</label>
                    <input type="date" value={newTransaction.date} onChange={(e) => setNewTransaction(prev => ({ ...prev, date: e.target.value }))} className="w-full border rounded-lg px-3 py-2" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">구분</label>
                    <select value={newTransaction.type} onChange={(e) => setNewTransaction(prev => ({ ...prev, type: e.target.value }))} className="w-full border rounded-lg px-3 py-2">
                      <option value="expense">지출</option>
                      <option value="income">수입</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">금액</label>
                    <input type="number" value={newTransaction.amount} onChange={(e) => setNewTransaction(prev => ({ ...prev, amount: e.target.value }))} className="w-full border rounded-lg px-3 py-2" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">분류</label>
                    <select value={newTransaction.category} onChange={(e) => setNewTransaction(prev => ({ ...prev, category: e.target.value }))} className="w-full border rounded-lg px-3 py-2">
                      <option value="">자동 분류</option>
                      {(newTransaction.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(cat => <option key={cat} value={cat}>{cat}</option>)}
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm text-gray-600 mb-1">내용</label>
                    <input type="text" value={newTransaction.description} onChange={(e) => setNewTransaction(prev => ({ ...prev, description: e.target.value }))} className="w-full border rounded-lg px-3 py-2" />
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button onClick={addTransaction} className="bg-blue-600 text-white px-4 py-2 rounded-lg">💾 저장</button>
                  <button onClick={() => setIsAddingTransaction(false)} className="bg-gray-200 px-4 py-2 rounded-lg">❌ 취소</button>
                </div>
              </div>
            )}

            <div className="bg-white rounded-xl shadow-sm overflow-x-auto">
              <table className="w-full min-w-[600px]">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold">날짜</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">구분</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">분류</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">내용</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">금액</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold">삭제</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {currentMonthTransactions.length === 0 ? (
                    <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">거래 내역이 없습니다</td></tr>
                  ) : (
                    currentMonthTransactions.map(t => (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm">{t.date}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-1 rounded-full ${(t.type === '수입' || t.type === 'income') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {t.type === 'income' ? '수입' : t.type === 'expense' ? '지출' : t.type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">{t.category}</td>
                        <td className="px-4 py-3 text-sm">{t.description || '-'}</td>
                        <td className={`px-4 py-3 text-sm text-right font-semibold ${(t.type === '수입' || t.type === 'income') ? 'text-green-600' : 'text-red-600'}`}>
                          {(t.type === '수입' || t.type === 'income') ? '+' : '-'}{formatCurrency(t.amount)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button onClick={() => deleteTransaction(t.id)} className="text-red-500 hover:text-red-700">🗑️</button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 체크리스트 */}
        {activeTab === 'checklist' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">{currentMonth}월 체크리스트</h2>
              <button onClick={() => setIsAddingChecklist(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg">➕ 항목 추가</button>
            </div>

            {isAddingChecklist && (
              <div className="bg-white rounded-xl p-6 shadow-sm border-2 border-blue-200">
                <h3 className="font-semibold mb-4">새 체크리스트 항목</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">카테고리</label>
                    <select value={newChecklist.category} onChange={(e) => setNewChecklist(prev => ({ ...prev, category: e.target.value }))} className="w-full border rounded-lg px-3 py-2">
                      {CHECKLIST_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">마감일 (일)</label>
                    <input type="number" min="1" max="31" value={newChecklist.dueDay} onChange={(e) => setNewChecklist(prev => ({ ...prev, dueDay: parseInt(e.target.value) }))} className="w-full border rounded-lg px-3 py-2" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm text-gray-600 mb-1">항목명</label>
                    <input type="text" value={newChecklist.item} onChange={(e) => setNewChecklist(prev => ({ ...prev, item: e.target.value }))} className="w-full border rounded-lg px-3 py-2" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm text-gray-600 mb-1">적용 월 (클릭하여 선택)</label>
                    <div className="flex flex-wrap gap-2">
                      {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => setNewChecklist(prev => ({
                            ...prev,
                            months: prev.months.includes(m) ? prev.months.filter(x => x !== m) : [...prev.months, m]
                          }))}
                          className={`px-3 py-1 rounded-full text-sm ${newChecklist.months.includes(m) ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
                        >
                          {m}월
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button onClick={addChecklistItem} className="bg-blue-600 text-white px-4 py-2 rounded-lg">💾 저장</button>
                  <button onClick={() => setIsAddingChecklist(false)} className="bg-gray-200 px-4 py-2 rounded-lg">❌ 취소</button>
                </div>
              </div>
            )}

            {CHECKLIST_CATEGORIES.map(category => {
              const items = currentMonthChecklist.filter(c => c.category === category);
              if (items.length === 0) return null;

              return (
                <div key={category} className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <div className="bg-blue-50 px-4 py-3 font-semibold text-blue-800">{category}</div>
                  <div className="divide-y">
                    {items.map(item => {
                      const isChecked = item.checked && item.checkMonth === `${currentYear}-${currentMonth}`;
                      const isOverdue = !isChecked && new Date() > new Date(currentYear, currentMonth - 1, item.dueDay);

                      return (
                        <div key={item.id} className={`px-4 py-3 flex items-center gap-3 ${isOverdue ? 'bg-red-50' : ''}`}>
                          <button
                            onClick={() => toggleChecklistItem(item)}
                            className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${isChecked ? 'bg-green-500 border-green-500 text-white' : 'border-gray-300'}`}
                          >
                            {isChecked && '✓'}
                          </button>
                          <div className="flex-1">
                            <p className={isChecked ? 'line-through text-gray-400' : ''}>{item.item}</p>
                            <p className={`text-xs ${isOverdue ? 'text-red-600 font-semibold' : 'text-gray-400'}`}>
                              {item.dueDay}일까지 {isOverdue && '⚠️ 기한 초과!'}
                            </p>
                          </div>
                          <button onClick={() => deleteChecklistItem(item.id)} className="text-red-500 hover:text-red-700">🗑️</button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 업로드 */}
        {activeTab === 'upload' && (
          <UploadTab
            fileInputRef={fileInputRef}
            handleImageUpload={handleImageUpload}
            isProcessingOCR={isProcessingOCR}
            ocrResult={ocrResult}
            ocrError={ocrError}
            setOcrResult={setOcrResult}
            addOcrTransactions={addOcrTransactions}
            formatCurrency={formatCurrency}
          />
        )}

        {/* 설정 */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">💰 월별 예산 설정</h2>
                <button onClick={() => setIsAddingSetting(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg">➕ 추가</button>
              </div>

              {isAddingSetting && (
                <div className="bg-blue-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="text"
                      placeholder="분류명 (예: 인건비)"
                      value={newSetting.category}
                      onChange={(e) => setNewSetting(prev => ({ ...prev, category: e.target.value }))}
                      className="border rounded-lg px-3 py-2"
                    />
                    <input
                      type="number"
                      placeholder="월 예산 (원)"
                      value={newSetting.amount}
                      onChange={(e) => setNewSetting(prev => ({ ...prev, amount: e.target.value }))}
                      className="border rounded-lg px-3 py-2"
                    />
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button onClick={addSettingItem} className="bg-blue-600 text-white px-4 py-2 rounded-lg">💾 저장</button>
                    <button onClick={() => setIsAddingSetting(false)} className="bg-gray-200 px-4 py-2 rounded-lg">❌ 취소</button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {settings.map(setting => (
                  <div key={setting.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                    {editingSetting?.id === setting.id ? (
                      <>
                        <input
                          type="text"
                          value={editingSetting.category}
                          onChange={(e) => setEditingSetting(prev => ({ ...prev, category: e.target.value }))}
                          className="flex-1 border rounded px-2 py-1"
                        />
                        <input
                          type="number"
                          value={editingSetting.amount}
                          onChange={(e) => setEditingSetting(prev => ({ ...prev, amount: parseInt(e.target.value) }))}
                          className="w-40 border rounded px-2 py-1"
                        />
                        <button onClick={updateSettingItem} className="text-green-600">💾</button>
                        <button onClick={() => setEditingSetting(null)} className="text-gray-600">❌</button>
                      </>
                    ) : (
                      <>
                        <span className="flex-1 font-medium">{setting.category}</span>
                        <span className="text-blue-600 font-semibold">{formatCurrency(setting.amount)}</span>
                        <button onClick={() => setEditingSetting(setting)} className="text-blue-600">✏️</button>
                        <button onClick={() => deleteSettingItem(setting.id)} className="text-red-500">🗑️</button>
                      </>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t">
                <div className="flex justify-between font-bold text-lg">
                  <span>총 예상 고정비</span>
                  <span className="text-blue-600">{formatCurrency(totalFixedCosts)}</span>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 rounded-xl p-6">
              <h3 className="font-semibold text-blue-800 mb-2">💡 설정 안내</h3>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• 여기서 설정한 예산이 대시보드의 "분류별 지출 현황"에 반영됩니다</li>
                <li>• 체크리스트 항목은 "체크리스트" 탭에서 추가/삭제할 수 있습니다</li>
                <li>• 모든 변경사항은 Notion에 자동 저장됩니다</li>
              </ul>
            </div>
          </div>
        )}
      </main>

      <footer className="bg-gray-100 p-4 mt-12">
        <div className="max-w-6xl mx-auto text-center text-sm text-gray-500">
          온소아청소년과의원 재정관리 시스템
        </div>
      </footer>
    </div>
  );
}
