import { Client } from '@notionhq/client';

const notion = new Client({ auth: process.env.NOTION_API_KEY });

// 거래내역 가져오기
export async function getTransactions() {
  try {
    const response = await notion.databases.query({
      database_id: process.env.NOTION_TRANSACTIONS_DB,
      sorts: [{ property: '날짜', direction: 'descending' }],
    });

    return response.results.map(page => ({
      id: page.id,
      date: page.properties['날짜']?.date?.start || '',
      type: page.properties['구분']?.select?.name || 'expense',
      amount: page.properties['금액']?.number || 0,
      category: page.properties['분류']?.select?.name || '',
      description: page.properties['내용']?.title?.[0]?.plain_text || '',
    }));
  } catch (error) {
    console.error('Error fetching transactions:', error);
    return [];
  }
}

// 거래내역 추가
export async function addTransaction(data) {
  try {
    const response = await notion.pages.create({
      parent: { database_id: process.env.NOTION_TRANSACTIONS_DB },
      properties: {
        '내용': { title: [{ text: { content: data.description || '' } }] },
        '날짜': { date: { start: data.date } },
        '구분': { select: { name: data.type === 'income' ? '수입' : '지출' } },
        '금액': { number: parseInt(data.amount) },
        '분류': { select: { name: data.category } },
      },
    });
    return { success: true, id: response.id };
  } catch (error) {
    console.error('Error adding transaction:', error);
    return { success: false, error: error.message };
  }
}

// 거래내역 삭제
export async function deleteTransaction(id) {
  try {
    await notion.pages.update({
      page_id: id,
      archived: true,
    });
    return { success: true };
  } catch (error) {
    console.error('Error deleting transaction:', error);
    return { success: false, error: error.message };
  }
}

// 체크리스트 가져오기
export async function getChecklist() {
  try {
    const response = await notion.databases.query({
      database_id: process.env.NOTION_CHECKLIST_DB,
      sorts: [{ property: '카테고리', direction: 'ascending' }],
    });

    return response.results.map(page => ({
      id: page.id,
      category: page.properties['카테고리']?.select?.name || '',
      item: page.properties['항목']?.title?.[0]?.plain_text || '',
      dueDay: page.properties['마감일']?.number || 1,
      months: page.properties['적용월']?.multi_select?.map(m => parseInt(m.name)) || [],
      checked: page.properties['완료']?.checkbox || false,
      checkMonth: page.properties['완료월']?.rich_text?.[0]?.plain_text || '',
    }));
  } catch (error) {
    console.error('Error fetching checklist:', error);
    return [];
  }
}

// 체크리스트 항목 추가
export async function addChecklistItem(data) {
  try {
    const response = await notion.pages.create({
      parent: { database_id: process.env.NOTION_CHECKLIST_DB },
      properties: {
        '항목': { title: [{ text: { content: data.item } }] },
        '카테고리': { select: { name: data.category } },
        '마감일': { number: parseInt(data.dueDay) },
        '적용월': { multi_select: data.months.map(m => ({ name: String(m) })) },
        '완료': { checkbox: false },
      },
    });
    return { success: true, id: response.id };
  } catch (error) {
    console.error('Error adding checklist item:', error);
    return { success: false, error: error.message };
  }
}

// 체크리스트 항목 업데이트
export async function updateChecklistItem(id, data) {
  try {
    const properties = {};
    if (data.checked !== undefined) {
      properties['완료'] = { checkbox: data.checked };
      properties['완료월'] = { rich_text: [{ text: { content: data.checkMonth || '' } }] };
    }
    if (data.item) properties['항목'] = { title: [{ text: { content: data.item } }] };
    if (data.category) properties['카테고리'] = { select: { name: data.category } };
    if (data.dueDay) properties['마감일'] = { number: parseInt(data.dueDay) };
    if (data.months) properties['적용월'] = { multi_select: data.months.map(m => ({ name: String(m) })) };

    await notion.pages.update({ page_id: id, properties });
    return { success: true };
  } catch (error) {
    console.error('Error updating checklist item:', error);
    return { success: false, error: error.message };
  }
}

// 체크리스트 항목 삭제
export async function deleteChecklistItem(id) {
  try {
    await notion.pages.update({ page_id: id, archived: true });
    return { success: true };
  } catch (error) {
    console.error('Error deleting checklist item:', error);
    return { success: false, error: error.message };
  }
}

// 설정(고정비) 가져오기
export async function getSettings() {
  try {
    const response = await notion.databases.query({
      database_id: process.env.NOTION_SETTINGS_DB,
    });

    return response.results.map(page => ({
      id: page.id,
      category: page.properties['분류']?.title?.[0]?.plain_text || '',
      amount: page.properties['월예산']?.number || 0,
    }));
  } catch (error) {
    console.error('Error fetching settings:', error);
    return [];
  }
}

// 설정(고정비) 추가
export async function addSetting(data) {
  try {
    const response = await notion.pages.create({
      parent: { database_id: process.env.NOTION_SETTINGS_DB },
      properties: {
        '분류': { title: [{ text: { content: data.category } }] },
        '월예산': { number: parseInt(data.amount) },
      },
    });
    return { success: true, id: response.id };
  } catch (error) {
    console.error('Error adding setting:', error);
    return { success: false, error: error.message };
  }
}

// 설정(고정비) 수정
export async function updateSetting(id, data) {
  try {
    const properties = {};
    if (data.category) properties['분류'] = { title: [{ text: { content: data.category } }] };
    if (data.amount !== undefined) properties['월예산'] = { number: parseInt(data.amount) };

    await notion.pages.update({ page_id: id, properties });
    return { success: true };
  } catch (error) {
    console.error('Error updating setting:', error);
    return { success: false, error: error.message };
  }
}

// 설정(고정비) 삭제
export async function deleteSetting(id) {
  try {
    await notion.pages.update({ page_id: id, archived: true });
    return { success: true };
  } catch (error) {
    console.error('Error deleting setting:', error);
    return { success: false, error: error.message };
  }
}
